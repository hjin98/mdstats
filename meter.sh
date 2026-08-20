CONFIG=$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/campaign.toml
WORKSPACE=$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign

du -sh "$WORKSPACE/.mdstats" | tee g4-disk-before.txt

set -o pipefail

/usr/bin/time -v -o g4-time.txt \
  python tools/mdstats-mlff-campaign.py \
    --config "$CONFIG" prepare \
  2>&1 | tee g4-mvsel2.log

status=${PIPESTATUS[0]}

du -sh "$WORKSPACE/.mdstats" | tee g4-disk-after.txt
echo "exit=$status"
