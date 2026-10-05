#!/bin/bash
# Residual N pointing after a commissioning re-aim: realizable controller at 700-740 C for three heater designs.
cd "/c/Users/Jiaow/Documents/github/MBE twin"
export PYTHONPATH=src
PY=/c/Users/Jiaow/miniconda3/envs/rheed/python.exe
$PY scripts/realizable_controller.py --t-min 720 --t-max 720 --heater-design-limit 1460 --pointing-residual 0.8 \
    --out results/reaim_check08 > results/reaim_check08.log 2>&1 && echo "check 0.8 done"
for d in 0.4 0.2 0.1; do
    for h in 1473.15 1460 1450; do
        name=reaim_d${d}_h${h%.*}
        $PY scripts/realizable_controller.py --t-min 700 --t-max 740 --heater-design-limit $h --pointing-residual $d \
            --out results/$name > results/$name.log 2>&1 && echo "done $name" || echo "FAILED $name"
    done
done
echo "sweep done"
