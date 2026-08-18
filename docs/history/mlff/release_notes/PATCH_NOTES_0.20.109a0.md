# mdstats 0.20.109a0 - PREC2 staged-precision runtime

This release implements the PREC2 runtime substrate for protocol-bound staged precision training.

## Implemented

- Live epoch-boundary FP32 -> FP64 promotion for model floating parameters/buffers.
- Recursive promotion of Adam/AMSGrad floating optimizer state, including moments and maximum second moments.
- EMA shadow-state promotion and exact restart preservation.
- Stage-relative learning-rate scaling with scheduler bookkeeping continuity.
- Latest-only exact-continuation companion state for MACE 0.3.16 staged restarts.
- Fail-safe restart selection when a raw checkpoint exists without its companion.
- Durable precision transition receipts.
- Floating minibatch tensors follow the active model dtype while graph/index tensors remain integral.

## Qualification boundary

Real MACE 0.3.16 e3nn force training crosses the FP32/FP64 boundary successfully. Existing CuEq campaign/source-contract tests pass, but the supplied environment does not contain `cuequivariance`/`cuequivariance_torch`; real CuEq production activation remains a PREC3 requirement.

## Compatibility

PREC1 protocol identities remain authoritative. Existing one-stage campaigns are unchanged. Canonical staged profiles remain fail-closed at production preflight until PREC3 completes end-to-end activation.
