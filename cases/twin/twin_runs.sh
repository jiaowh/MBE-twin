#!/bin/bash
# Twin records of 2026-10-05: frozen and realizable recipes on the truth states, heater design margin.
cd "/c/Users/Jiaow/Documents/github/MBE twin"
export PYTHONPATH=src
PY=/c/Users/Jiaow/miniconda3/envs/rheed/python.exe
rm -f data/runs/studies/twin_*.json
F=cases/twin/gan_1um_720C.json
R=cases/twin/gan_1um_720C_realizable.json
for c in "" _fill40 _fill120 _tilt-flange-0.8deg-dir0 _tilt-flange-0.8deg-dir180; do
    $PY scripts/twin_run.py --recipe $F --chamber cases/twin/chamber_B-L_720C$c.json | sed -n 1,3p
    $PY scripts/twin_run.py --recipe $R --chamber cases/twin/chamber_B-L_720C$c.json | sed -n 1,3p
done
for b in 2 -2; do
    $PY scripts/twin_run.py --recipe $F --pyrometer-bias $b | sed -n 1,3p
    $PY scripts/twin_run.py --recipe $F --chamber cases/twin/chamber_B-L_720C_heater1425K.json --pyrometer-bias $b | sed -n 1,3p
done
$PY scripts/twin_run.py --recipe $F --chamber cases/twin/chamber_B-L_720C_heater1425K.json | sed -n 1,3p
$PY scripts/twin_run.py --recipe $R --chamber cases/twin/chamber_B-L_720C_fill120.json --bfm-error 0.02 | sed -n 1,3p
$PY scripts/twin_run.py --recipe $R --chamber cases/twin/chamber_B-L_720C_fill120.json --rate-error 0.01 | sed -n 1,3p
echo "twin runs done"
