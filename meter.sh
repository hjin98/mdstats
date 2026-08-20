CONFIG=$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/campaign.toml
WORKSPACE=$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign

du -sh "$WORKSPACE/.mdstats" | tee g4b-disk-before.txt

set -o pipefail

/usr/bin/time -v -o g4b-time.txt \
  timeout --signal=TERM 20m \
  env PYTHONUNBUFFERED=1 \
  python -u tools/mdstats-mlff-campaign.py \
    --config "$CONFIG" prepare \
  2>&1 | tee g4b-mvsel2.txt

status=${PIPESTATUS[0]}

du -sh "$WORKSPACE/.mdstats" | tee g4b-disk-after.txt
echo "exit=$status"
