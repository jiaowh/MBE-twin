#!/bin/bash
# Scattered-atom factor tables at the frozen aims, seed-averaged, and their effect on the uniformity worst case (2026-10-06).
# Prerequisites (each several hours of Monte Carlo, run detached by results/run_queue_aim95*.ps1 and run_queue_Bp_seeds*.ps1):
#   B-L +95 mm gas:   scattered_tables.py --layouts B-L --aim-mm 95 --ga-particles 16000 --seed S --out results/scattered_tables_B-L_95mm{,_rep,_s3,_s4}
#                     (S = 20261003, 20261103, 20261203, 20261303)
#   B-L +95 mm plume: scattered_plume_tables.py --layouts B-L --aim-mm 95 --seed S --out results/scattered_plume_tables_B-L_95mm{,_rep,_s3,_s4}
#                     (S = 20261007, 20261107, 20261207, 20261307; S = 2 and 4 m^3/s), and --speeds 4 for _s5 ... _s10
#                     (S = 20261507 ... 20262007)
#   B-p +97.5 mm plume: scattered_plume_tables.py --layouts B-p --aim-mm 97.5 --speeds 2 --seed S
#                     --out results/scattered_plume_tables_B-p_97.5mm_s{1..10} (S = 20262106 ... 20263006)
#   aim tables:       aim_tables.py --layout B-L --aim-mm A (A = 90 92.5 95 97.5 100); aim_tables.py --layout B-p --aim-mm 97.5
# Controller runs: multi-spot heater, 0.2 deg re-aim, 1460 K heater design, rate monitor + BFM, 710-720 C.
cd "/c/Users/Jiaow/Documents/github/MBE twin"
export PYTHONPATH=src
PY=/c/Users/Jiaow/miniconda3/envs/rheed/python.exe
RC=scripts/realizable_controller.py
ST=data/runs/studies
C="--t-min 710 --t-max 720 --heater-control multispot --heater-design-limit 1460 --pointing-residual 0.2"
L=results/scattered_plume_tables_B-L_95mm
B=results/scattered_plume_tables_B-p_97.5mm

run() {  # name, args...
    local name=$1; shift
    $PY $RC $C "$@" --out results/$name > results/$name.log 2>&1 && echo "done $name $(date +%H:%M)" || echo "FAILED $name"
}

# seed-averaged tables (archived)
$PY scripts/average_scattered_seeds.py --parts results/scattered_tables_B-L_95mm{,_rep,_s3,_s4} --out results/scattered_tables_B-L_95mm_avg4
$PY scripts/average_scattered_seeds.py --parts $L ${L}{_rep,_s3,_s4,_s5,_s6,_s7,_s8,_s9,_s10} --out ${L}_avg10
$PY scripts/average_scattered_seeds.py --parts ${B}_s{1,2,3,4,5,6,7,8,9,10} --out ${B}_avg10
cp results/scattered_tables_B-L_95mm_avg4/manifest.json $ST/scattered_tables_B-L_95mm.json
cp ${L}_avg10/manifest.json $ST/scattered_plume_tables_B-L_95mm.json
cp ${B}_avg10/manifest.json $ST/scattered_plume_tables_B-p_97.5mm.json

NL="--n-tables results/aim_tables/n_tables_B-L_95mm.npz"
NB="--n-tables results/aim_tables/n_tables_B-p_97.5mm.npz"
GL="$ST/scattered_tables_B-L_95mm.json"
GB="$ST/scattered_tables.json"   # B-p gas factors: the archived envelope-aim tables (used only beyond plume coverage)
P=()
P+=("ctl_BL95_s1 $NL --n-scatter $GL $L/manifest.json")
P+=("ctl_BL95_s2 $NL --n-scatter $GL ${L}_rep/manifest.json")
for k in 3 4 5 6 7 8 9 10; do P+=("ctl_BL95_s$k $NL --n-scatter $GL ${L}_s$k/manifest.json"); done
P+=("ctl_BL95_avg $NL --n-scatter $GL $ST/scattered_plume_tables_B-L_95mm.json")
P+=("ctl_BL95_flat $NL --n-scatter $GL $ST/scattered_plume_tables_B-L_95mm.json --scatter-flat")
for a in 90 92.5 97.5 100; do
    P+=("ctl_BLscan_$a --n-tables results/aim_tables/n_tables_B-L_${a}mm.npz --n-scatter $GL $ST/scattered_plume_tables_B-L_95mm.json --scatter-from-aim 95")
done
for k in 1 2 3 4 5 6 7 8 9 10; do P+=("ctl_Bp_s$k $NB --n-scatter $GB ${B}_s$k/manifest.json"); done
P+=("ctl_Bp_avg $NB --n-scatter $GB $ST/scattered_plume_tables_B-p_97.5mm.json")
P+=("ctl_Bp_flat $NB --n-scatter $GB $ST/scattered_plume_tables_B-p_97.5mm.json --scatter-flat")

# six at a time (about 5 min per wave on this laptop)
i=0
for spec in "${P[@]}"; do
    run $spec &
    i=$((i + 1)); [ $((i % 6)) -eq 0 ] && wait
done
wait

$PY scripts/summarize_scatter_noise.py --runs $(for k in 1 2 3 4 5 6 7 8 9 10; do echo single:results/ctl_BL95_s$k; done) \
    avg:results/ctl_BL95_avg flat:results/ctl_BL95_flat aim:results/ctl_BLscan_{90,92.5,97.5,100} --out results/scatter_noise_BL95
$PY scripts/summarize_scatter_noise.py --runs single:results/ctl_Bp_s{1,2,3,4,5,6,7,8,9,10} avg:results/ctl_Bp_avg flat:results/ctl_Bp_flat \
    --out results/scatter_noise_Bp
cp results/scatter_noise_BL95/manifest.json $ST/scatter_noise_BL95.json
cp results/scatter_noise_Bp/manifest.json $ST/scatter_noise_Bp.json
cp results/ctl_BL95_avg/manifest.json $ST/realizable_controller_ms_BL95scatter.json
echo "all done $(date +%H:%M)"
