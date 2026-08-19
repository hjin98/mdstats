"""Read uncompressed NPY members from NPZ/ZIP containers as memmaps."""
from __future__ import annotations

from pathlib import Path
import struct
from typing import Iterable
import zipfile

import numpy as np

_LOCAL_FILE_HEADER = struct.Struct("<IHHHHHIIIHH")
_LOCAL_FILE_SIGNATURE = 0x04034B50


def npy_memmap_from_stored_zip_member(
    archive_path: str | Path,
    archive: zipfile.ZipFile,
    member: str,
) -> np.ndarray:
    path = Path(archive_path)
    info = archive.getinfo(member)
    if info.compress_type != zipfile.ZIP_STORED:
        with archive.open(member, "r") as handle:
            result = np.load(handle, allow_pickle=False)
        result.setflags(write=False)
        return result
    with path.open("rb") as handle:
        handle.seek(info.header_offset)
        header = handle.read(_LOCAL_FILE_HEADER.size)
        if len(header) != _LOCAL_FILE_HEADER.size:
            raise ValueError(f"ZIP member header is truncated for {member!r}.")
        fields = _LOCAL_FILE_HEADER.unpack(header)
        if fields[0] != _LOCAL_FILE_SIGNATURE:
            raise ValueError(f"ZIP member header signature is invalid for {member!r}.")
        name_length, extra_length = int(fields[-2]), int(fields[-1])
        npy_start = (
            info.header_offset
            + _LOCAL_FILE_HEADER.size
            + name_length
            + extra_length
        )
        handle.seek(npy_start)
        version = np.lib.format.read_magic(handle)
        if version == (1, 0):
            shape, fortran_order, dtype = np.lib.format.read_array_header_1_0(handle)
        elif version in {(2, 0), (3, 0)}:
            shape, fortran_order, dtype = np.lib.format.read_array_header_2_0(handle)
        else:
            raise ValueError(f"Unsupported NPY version {version!r} for {member!r}.")
        data_offset = handle.tell()
    result = np.memmap(
        path,
        mode="r",
        dtype=dtype,
        offset=data_offset,
        shape=shape,
        order="F" if fortran_order else "C",
    )
    result.setflags(write=False)
    return result


def load_npz_members_mmap(
    path: str | Path,
    members: Iterable[str],
) -> dict[str, np.ndarray]:
    archive_path = Path(path)
    requested = tuple(dict.fromkeys(str(name) for name in members))
    with zipfile.ZipFile(archive_path, "r") as archive:
        by_key = {
            info.filename[:-4]: info.filename
            for info in archive.infolist()
            if info.filename.endswith(".npy")
        }
        missing = tuple(name for name in requested if name not in by_key)
        if missing:
            raise KeyError(missing)
        return {
            name: npy_memmap_from_stored_zip_member(
                archive_path, archive, by_key[name]
            )
            for name in requested
        }
