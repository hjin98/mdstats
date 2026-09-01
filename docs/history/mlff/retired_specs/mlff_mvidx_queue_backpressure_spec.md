# MVIDX bounded-queue backpressure hardening (0.20.240a0)

## Status

Maintenance hardening on MLFF architecture revision 103 / dependency schema 83. Scientific authority is unchanged and `FINAL-GPU1` remains the next scientific gate.

## Production incident

A production TARGET-DATA2C-MVIDX1 domain contained 165 required exact-neighborhood families. With 28 inverse workers, PARCORE1 intentionally bounded the ready queue to 56 tasks. The pre-0.20.240 MVIDX producer eagerly submitted every family before entering its completion-drain loop, so submission 57+ could raise `DeterministicWorkQueueError: PARCORE1 ready queue is full (56 tasks)` even though workers were making valid progress.

## Required execution contract

MVIDX SHALL treat PARCORE1 queue capacity as producer backpressure rather than as a reason to increase the queue bound.

1. Family inversions are submitted only while `queue.can_submit()` is true.
2. When ready capacity is exhausted, the coordinator waits for worker completion, drains canonical completions, commits their results, and refills the queue.
3. The hard-obligation inverse is submitted through the same bounded refill loop after family submission reaches its canonical end.
4. Ready, in-flight, and completed queue limits remain bounded and RAM admission remains fail-closed.
5. Completion order may vary, but result assembly remains canonical by family order and task identity.
6. Out-of-core MVIDX storage introduced in 0.20.238a0 is unchanged.
7. Queue size, worker count, and refill timing are execution state and SHALL NOT enter MVIDX scientific identity.

## Qualification oracle

A production-style TARGET-DATA2B fixture with 17 required families is forced through a PARCORE1 queue with only one ready slot. The optimized MVIDX build must complete without queue-full failure and must reproduce the exact control MVIDX content digest. Under the historical eager-submission implementation, this fixture necessarily fails once the bounded ready slot and in-flight capacity are saturated.
