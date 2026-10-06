#!/bin/bash
# Aim offset at the operating point (uniformity first): realizable controller with the aim maps of
# scripts/nitrogen_aim_operating.py, before (0.8 deg) and after (0.2 deg) a commissioning re-aim.
cd "/c/Users/Jiaow/Documents/github/MBE twin"
export PYTHONPATH=src
PY=/c/Users/Jiaow/miniconda3/envs/rheed/python.exe
for d in 0.2 0.8; do
    for a in 90 95 100 105; do
        name=aim_BL_a${a}_d${d}
        $PY scripts/realizable_controller.py --t-min 710 --t-max 730 --heater-design-limit 1460 --pointing-residual $d \
            --aim-maps results/aim_operating/aim_maps_B-L.npz --aim-mm $a --out results/$name > results/$name.log 2>&1 \
            && echo "done $name" || echo "FAILED $name"
    done
    for a in 92.5 97.5 102.5; do
        name=aim_Bp_a${a}_d${d}
        $PY scripts/realizable_controller.py --t-min 710 --t-max 730 --heater-design-limit 1450 --pointing-residual $d \
            --aim-maps results/aim_operating/aim_maps_B-p.npz --aim-mm $a --out results/$name > results/$name.log 2>&1 \
            && echo "done $name" || echo "FAILED $name"
    done
done
echo "aim sweep done"
