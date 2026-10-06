#!/bin/bash
# Reruns for the 2026-10-05 follow-up audit: aim-map and multi-spot runs with execution-time dependency hashes
# (finding 2), and the twin records with the controllers reading the ion gauge (finding 1). Three parallel chains.
cd "/c/Users/Jiaow/Documents/github/MBE twin"
export PYTHONPATH=src
PY=/c/Users/Jiaow/miniconda3/envs/rheed/python.exe
RC=scripts/realizable_controller.py

run() {  # name, args...
    local name=$1; shift
    $PY $RC "$@" --out results/$name > results/$name.log 2>&1 && echo "done $name $(date +%H:%M)" || echo "FAILED $name"
}

chain_aim() {
    bash cases/aim_sweep_2026-10-05.sh
    for a in 92.5 97.5; do for d in 0.2 0.8; do
        run aim_BL_a${a}_d${d} --t-min 720 --t-max 720 --heater-design-limit 1460 --pointing-residual $d \
            --aim-maps results/aim_operating_fine/aim_maps_B-L.npz --aim-mm $a
    done; done
}

chain_ms() {
    bash cases/multispot_sweep_2026-10-05.sh
    run ms_h1460_d0.2_cold --t-min 690 --t-max 710 --heater-control multispot --heater-design-limit 1460 \
        --pointing-residual 0.2 --aim-maps results/aim_operating/aim_maps_B-L.npz --aim-mm 95
}

chain_aim > results/rerun_prov_aim.txt 2>&1 &
chain_ms > results/rerun_prov_ms.txt 2>&1 &
bash cases/twin/twin_runs.sh > results/rerun_prov_twin.txt 2>&1 &
wait
echo "all reruns done $(date +%H:%M)"
