#!/bin/bash
# Rerun of the studies affected by the joint 95 % gate (audit 2026-10-05, finding 2), two chains in parallel.
cd "/c/Users/Jiaow/Documents/github/MBE twin"
export PYTHONPATH=src
PY=/c/Users/Jiaow/miniconda3/envs/rheed/python.exe

run() {  # name, args...
    local name=$1; shift
    $PY "$@" --out results/$name > results/$name.log 2> results/$name.log.err \
        && cp results/$name/manifest.json data/runs/studies/$name.json \
        && echo "done $name $(date +%H:%M)" || echo "FAILED $name $(date +%H:%M)"
}

chain_a() {
    run operating_optimum scripts/operating_optimum.py
    run operating_optimum_sc_plume scripts/operating_optimum.py --scattered gas+plume
    run operating_cold_limit scripts/operating_cold_limit.py
    run operating_cold_limit_bias5 scripts/operating_cold_limit.py --pyrometer-bias 5 --t-max 790
    run operating_cold_limit_bias10 scripts/operating_cold_limit.py --pyrometer-bias 10 --t-max 790
    run operating_cold_limit_gas scripts/operating_cold_limit.py --scattered gas
}

chain_b() {
    run operating_cold_limit_gas-gamma0.1 scripts/operating_cold_limit.py --scattered gas-gamma0.1
    for b in 2 3 4 5 10; do
        run operating_cold_limit_sc_plume_bias$b scripts/operating_cold_limit.py --scattered gas+plume --pyrometer-bias $b --t-max 790
    done
}

chain_a > results/rerun_gate_a.txt 2>&1 &
chain_b > results/rerun_gate_b.txt 2>&1 &
wait
echo "all done $(date +%H:%M)"
