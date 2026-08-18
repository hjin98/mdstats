# mdstats 0.20.118a0 patch notes

## DATA8 canonical refine floor portability fix

The canonical `refine` profile still uses the user-visible 80% FP32 -> 20% FP64 schedule,
FP64 learning-rate scale 0.5, a hard three-epoch FP64 floor, and the configured 15,000
gradient-update reference floor. The previous resolver treated 15,000 updates as an
unconditional per-job hard floor. That is impossible for default n512 target-only naive
fine tuning: with batch size 2, a 30-epoch job contains only about 7,680 optimizer steps
before fold-size effects. DATA8 therefore failed even though the nominal six-epoch FP64
tail was valid.

0.20.118a0 preserves strict custom contracts but makes the exact canonical reference
profile portable across workload sizes. If 15,000 FP64 updates cannot fit anywhere in the
staged epoch budget and the nominal 20% tail already meets the hard three-epoch floor,
the resolver keeps the nominal split and binds the actually achievable update floor into
the resolved schedule. Replay-sized jobs that can satisfy 15,000 updates retain the
existing behavior.

The release also fixes `require_update_floor=False`: update-count enforcement is now
actually disabled even when `updates_per_epoch` is supplied.
