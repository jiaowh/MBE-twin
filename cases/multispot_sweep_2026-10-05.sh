#!/bin/bash
# Multi-spot pyrometry with three zone groups at 720 C, best aims (B-p 97.5 mm, B-L 95 mm), after a 0.2 deg re-aim.
cd "/c/Users/Jiaow/Documents/github/MBE twin"
export PYTHONPATH=src
PY=/c/Users/Jiaow/miniconda3/envs/rheed/python.exe
AIM="--aim-maps results/aim_operating/aim_maps_B-L.npz --aim-mm 95"
for h in 1460 1450 1425; do
    name=ms_h${h}_d0.2
    $PY scripts/realizable_controller.py --t-min 720 --t-max 720 --heater-control multispot --heater-design-limit $h \
        --pointing-residual 0.2 $AIM --dump-t 720 --out results/$name > results/$name.log 2>&1 && echo "done $name" || echo "FAILED $name"
done
name=ms_h1450_d0.8
$PY scripts/realizable_controller.py --t-min 720 --t-max 720 --heater-control multispot --heater-design-limit 1450 \
    --pointing-residual 0.8 $AIM --dump-t 720 --out results/$name > results/$name.log 2>&1 && echo "done $name" || echo "FAILED $name"
echo "multispot sweep done"
