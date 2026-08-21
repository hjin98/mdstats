#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>
#include <stdlib.h>

#ifdef _OPENMP
#include <omp.h>
#endif

#define MVSEL2_PW_BLOCKSIZE 128

/*
 * Match NumPy's DOUBLE_pairwise_sum ordering for a contiguous gathered FP64
 * row. The gather is performed lazily through authenticated MVIDX1 uint32
 * witness indices rather than materializing terms[row] first.
 *
 * Witness bounds are an already-authenticated MVIDX1 invariant and the private
 * Python owner guarantees terms length == family witness_count before entering
 * this hot loop. Rechecking every edge would add a branch to billions of edge
 * visits without strengthening the scientific persistence boundary.
 *
 * Do not compile this function with fast-math/reassociation.
 */
static inline double
mvsel2_pairwise_sum_gather(
    const uint32_t *witnesses,
    const double *terms,
    uint64_t n
)
{
    uint64_t i;
    if (n == 0) {
        return 0.0;
    }
    if (n < 8) {
        double res = -0.0;
        for (i = 0; i < n; ++i) {
            res += terms[witnesses[i]];
        }
        return res;
    }
    if (n <= MVSEL2_PW_BLOCKSIZE) {
        double r[8];
        double res;
        r[0] = terms[witnesses[0]];
        r[1] = terms[witnesses[1]];
        r[2] = terms[witnesses[2]];
        r[3] = terms[witnesses[3]];
        r[4] = terms[witnesses[4]];
        r[5] = terms[witnesses[5]];
        r[6] = terms[witnesses[6]];
        r[7] = terms[witnesses[7]];

        for (i = 8; i < n - (n % 8); i += 8) {
            r[0] += terms[witnesses[i + 0]];
            r[1] += terms[witnesses[i + 1]];
            r[2] += terms[witnesses[i + 2]];
            r[3] += terms[witnesses[i + 3]];
            r[4] += terms[witnesses[i + 4]];
            r[5] += terms[witnesses[i + 5]];
            r[6] += terms[witnesses[i + 6]];
            r[7] += terms[witnesses[i + 7]];
        }

        res = ((r[0] + r[1]) + (r[2] + r[3])) +
              ((r[4] + r[5]) + (r[6] + r[7]));
        for (; i < n; ++i) {
            res += terms[witnesses[i]];
        }
        return res;
    }
    else {
        uint64_t n2 = n / 2;
        n2 -= n2 % 8;
        return mvsel2_pairwise_sum_gather(witnesses, terms, n2) +
               mvsel2_pairwise_sum_gather(
                   witnesses + n2,
                   terms,
                   n - n2
               );
    }
}

static int
mvsel2_get_1d_buffer(
    PyObject *object,
    Py_buffer *view,
    int writable,
    Py_ssize_t itemsize,
    const char *name
)
{
    int flags = PyBUF_ND | PyBUF_FORMAT | PyBUF_C_CONTIGUOUS;
    if (writable) {
        flags |= PyBUF_WRITABLE;
    }
    if (PyObject_GetBuffer(object, view, flags) < 0) {
        return -1;
    }
    if (view->ndim != 1 || view->itemsize != itemsize ||
        view->len < 0 || view->len % itemsize != 0) {
        PyErr_Format(
            PyExc_ValueError,
            "%s must be a one-dimensional C-contiguous buffer with itemsize %zd",
            name,
            itemsize
        );
        PyBuffer_Release(view);
        return -1;
    }
    return 0;
}

static PyObject *
mvsel2_score_family_batch(PyObject *self, PyObject *args)
{
    PyObject *offsets_object;
    PyObject *witnesses_object;
    PyObject *terms_object;
    PyObject *candidates_object;
    PyObject *output_object;
    int workers;
    Py_buffer offsets_view = {0};
    Py_buffer witnesses_view = {0};
    Py_buffer terms_view = {0};
    Py_buffer candidates_view = {0};
    Py_buffer output_view = {0};
    uint64_t edges = 0;
    PyObject *result = NULL;

    if (!PyArg_ParseTuple(
            args,
            "OOOOOi:score_family_batch",
            &offsets_object,
            &witnesses_object,
            &terms_object,
            &candidates_object,
            &output_object,
            &workers)) {
        return NULL;
    }
    if (workers < 1) {
        PyErr_SetString(PyExc_ValueError, "workers must be positive");
        return NULL;
    }
#ifndef _OPENMP
    if (workers > 1) {
        PyErr_SetString(
            PyExc_RuntimeError,
            "MVSEL2 native extension was built without OpenMP support"
        );
        return NULL;
    }
#endif

    if (mvsel2_get_1d_buffer(
            offsets_object, &offsets_view, 0, (Py_ssize_t)sizeof(uint64_t),
            "offsets") < 0) {
        goto done;
    }
    if (mvsel2_get_1d_buffer(
            witnesses_object, &witnesses_view, 0, (Py_ssize_t)sizeof(uint32_t),
            "witnesses") < 0) {
        goto done;
    }
    if (mvsel2_get_1d_buffer(
            terms_object, &terms_view, 0, (Py_ssize_t)sizeof(double),
            "terms") < 0) {
        goto done;
    }
    if (mvsel2_get_1d_buffer(
            candidates_object, &candidates_view, 0, (Py_ssize_t)sizeof(uint32_t),
            "candidates") < 0) {
        goto done;
    }
    if (mvsel2_get_1d_buffer(
            output_object, &output_view, 1, (Py_ssize_t)sizeof(double),
            "output") < 0) {
        goto done;
    }

    {
        const uint64_t *offsets = (const uint64_t *)offsets_view.buf;
        const uint32_t *candidates = (const uint32_t *)candidates_view.buf;
        const uint64_t offset_count = (uint64_t)(offsets_view.len / (Py_ssize_t)sizeof(uint64_t));
        const uint64_t witness_count = (uint64_t)(witnesses_view.len / (Py_ssize_t)sizeof(uint32_t));
        const uint64_t candidate_count = offset_count > 0 ? offset_count - 1 : 0;
        const uint64_t requested = (uint64_t)(candidates_view.len / (Py_ssize_t)sizeof(uint32_t));
        const uint64_t output_count = (uint64_t)(output_view.len / (Py_ssize_t)sizeof(double));
        uint64_t position;

        if (offset_count < 2) {
            PyErr_SetString(PyExc_ValueError, "offsets must contain at least two entries");
            goto done;
        }
        if (terms_view.len == 0) {
            PyErr_SetString(PyExc_ValueError, "terms must not be empty");
            goto done;
        }
        if (requested > output_count) {
            PyErr_SetString(PyExc_ValueError, "output is shorter than candidates");
            goto done;
        }
        if (requested > (uint64_t)PY_SSIZE_T_MAX) {
            PyErr_SetString(PyExc_OverflowError, "candidate batch is too large");
            goto done;
        }

        for (position = 0; position < requested; ++position) {
            const uint64_t candidate = (uint64_t)candidates[position];
            uint64_t start;
            uint64_t stop;
            if (candidate >= candidate_count) {
                PyErr_SetString(PyExc_IndexError, "candidate index is out of range");
                goto done;
            }
            start = offsets[candidate];
            stop = offsets[candidate + 1];
            if (start > stop || stop > witness_count) {
                PyErr_SetString(PyExc_ValueError, "candidate CSR offsets are invalid");
                goto done;
            }
            edges += stop - start;
        }

        {
            const uint32_t *witnesses = (const uint32_t *)witnesses_view.buf;
            const double *terms = (const double *)terms_view.buf;
            double *output = (double *)output_view.buf;
            Py_ssize_t count = (Py_ssize_t)requested;
            Py_ssize_t p;

            Py_BEGIN_ALLOW_THREADS
#ifdef _OPENMP
#pragma omp parallel for schedule(static) num_threads(workers)
#endif
            for (p = 0; p < count; ++p) {
                const uint64_t candidate = (uint64_t)candidates[p];
                const uint64_t start = offsets[candidate];
                const uint64_t stop = offsets[candidate + 1];
                output[p] = mvsel2_pairwise_sum_gather(
                    witnesses + start,
                    terms,
                    stop - start
                );
            }
            Py_END_ALLOW_THREADS
        }
    }

    result = PyLong_FromUnsignedLongLong((unsigned long long)edges);

done:
    if (output_view.obj != NULL) {
        PyBuffer_Release(&output_view);
    }
    if (candidates_view.obj != NULL) {
        PyBuffer_Release(&candidates_view);
    }
    if (terms_view.obj != NULL) {
        PyBuffer_Release(&terms_view);
    }
    if (witnesses_view.obj != NULL) {
        PyBuffer_Release(&witnesses_view);
    }
    if (offsets_view.obj != NULL) {
        PyBuffer_Release(&offsets_view);
    }
    return result;
}

static PyObject *
mvsel2_openmp_enabled(PyObject *self, PyObject *args)
{
#ifdef _OPENMP
    Py_RETURN_TRUE;
#else
    Py_RETURN_FALSE;
#endif
}

static PyObject *
mvsel2_max_threads(PyObject *self, PyObject *args)
{
#ifdef _OPENMP
    return PyLong_FromLong((long)omp_get_max_threads());
#else
    return PyLong_FromLong(1L);
#endif
}

static PyMethodDef mvsel2_methods[] = {
    {
        "score_family_batch",
        mvsel2_score_family_batch,
        METH_VARARGS,
        "Score authenticated candidate CSR rows against one FP64 witness-term vector."
    },
    {
        "openmp_enabled",
        mvsel2_openmp_enabled,
        METH_NOARGS,
        "Return whether the extension was compiled with OpenMP."
    },
    {
        "max_threads",
        mvsel2_max_threads,
        METH_NOARGS,
        "Return the native backend's current maximum thread count."
    },
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef mvsel2_module = {
    PyModuleDef_HEAD_INIT,
    "_mvsel2_native",
    "Private exact MVSEL2 family-row scoring backend.",
    -1,
    mvsel2_methods
};

PyMODINIT_FUNC
PyInit__mvsel2_native(void)
{
    return PyModule_Create(&mvsel2_module);
}
