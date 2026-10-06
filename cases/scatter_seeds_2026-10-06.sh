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
# Controller runs: multi-spot heater, 0.2 deg re-aim, 1460 K heater design, rate monitor + BFM, 710-720 C; each run
# evaluates only the layout whose tables it replaces. Everything this script makes goes to a fresh directory
# results/scatter_seeds_<time>/; the records in data/runs/studies are replaced only after every step succeeded.
# Bootstrap (audit 2026-10-06): NBOOT resampled averages per layout (average_scattered_seeds.py --resample) give the
# table-noise uncertainty of the averaged-table results and of the B-L - B-p difference. About 70 min with 2 jobs (68 min on 2026-10-06).
set -uo pipefail
cd "/c/Users/Jiaow/Documents/github/MBE twin"
export PYTHONPATH=src
PY=/c/Users/Jiaow/miniconda3/envs/rheed/python.exe
RC=scripts/realizable_controller.py
AV=scripts/average_scattered_seeds.py
ST=data/runs/studies
C="--t-min 710 --t-max 720 --heater-control multispot --heater-design-limit 1460 --pointing-residual 0.2"
L=results/scattered_plume_tables_B-L_95mm
G=results/scattered_tables_B-L_95mm
B=results/scattered_plume_tables_B-p_97.5mm
NBOOT=${NBOOT:-40}
R=results/scatter_seeds_$(date +%Y%m%d_%H%M%S)
mkdir "$R" || exit 1
echo "run directory $R"

step() {  # a sequential command; stop the script if it fails
    "$@" || { echo "FAILED: $*"; exit 1; }
}

# seed-averaged tables
step $PY $AV --parts ${G}{,_rep,_s3,_s4} --out $R/avg_gas_BL
step $PY $AV --parts $L ${L}{_rep,_s3,_s4,_s5,_s6,_s7,_s8,_s9,_s10} --out $R/avg_plume_BL
step $PY $AV --parts ${B}_s{1,2,3,4,5,6,7,8,9,10} --out $R/avg_plume_Bp
# bootstrap-resampled averages (independent RNG streams per table set)
for k in $(seq 1 $NBOOT); do
    step $PY $AV --parts ${G}{,_rep,_s3,_s4} --resample $((1000 + k)) --out $R/boot_gas_BL_$k > /dev/null
    step $PY $AV --parts $L ${L}{_rep,_s3,_s4,_s5,_s6,_s7,_s8,_s9,_s10} --resample $((2000 + k)) --out $R/boot_plume_BL_$k > /dev/null
    step $PY $AV --parts ${B}_s{1,2,3,4,5,6,7,8,9,10} --resample $((3000 + k)) --out $R/boot_plume_Bp_$k > /dev/null
done

NL="--layouts B-L --n-tables results/aim_tables/n_tables_B-L_95mm.npz"
NB="--layouts B-p --n-tables results/aim_tables/n_tables_B-p_97.5mm.npz"
GL=$R/avg_gas_BL/manifest.json
PL=$R/avg_plume_BL/manifest.json
PB=$R/avg_plume_Bp/manifest.json
GB="$ST/scattered_tables.json"   # B-p gas factors: the archived envelope-aim tables (used only beyond plume coverage)
P=()
P+=("ctl_BL95_s1 $NL --n-scatter $GL $L/manifest.json")
P+=("ctl_BL95_s2 $NL --n-scatter $GL ${L}_rep/manifest.json")
for k in 3 4 5 6 7 8 9 10; do P+=("ctl_BL95_s$k $NL --n-scatter $GL ${L}_s$k/manifest.json"); done
P+=("ctl_BL95_avg $NL --n-scatter $GL $PL")
P+=("ctl_BL95_flat $NL --n-scatter $GL $PL --scatter-flat")
for a in 90 92.5 97.5 100; do
    P+=("ctl_BLscan_$a --layouts B-L --n-tables results/aim_tables/n_tables_B-L_${a}mm.npz --n-scatter $GL $PL --scatter-from-aim 95")
done
for k in 1 2 3 4 5 6 7 8 9 10; do P+=("ctl_Bp_s$k $NB --n-scatter $GB ${B}_s$k/manifest.json"); done
P+=("ctl_Bp_avg $NB --n-scatter $GB $PB")
P+=("ctl_Bp_flat $NB --n-scatter $GB $PB --scatter-flat")
for k in $(seq 1 $NBOOT); do
    P+=("ctl_BL95_boot$k $NL --n-scatter $R/boot_gas_BL_$k/manifest.json $R/boot_plume_BL_$k/manifest.json")
    P+=("ctl_Bp_boot$k $NB --n-scatter $GB $R/boot_plume_Bp_$k/manifest.json")
done

# MAXJOBS at a time (default 2), each started only while MIN_FREE_GB of physical memory is free: one controller
# run peaks near 0.9 GB, and six in parallel exhausted memory and crashed this laptop on 2026-10-06.
# Every job's exit status is checked.
MAXJOBS=${MAXJOBS:-2}
MIN_FREE_GB=${MIN_FREE_GB:-3}
free_gb() { powershell -NoProfile -Command "[int]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB)" | tr -d ''; }
failed=0
declare -A running=()
reap() {  # wait for one job and record its status
    local pid
    if wait -n -p pid "${!running[@]}"; then echo "done ${running[$pid]} $(date +%H:%M)"
    else echo "FAILED ${running[$pid]}"; failed=$((failed + 1)); fi
    unset "running[$pid]"
}
for spec in "${P[@]}"; do
    set -- $spec
    name=$1; shift
    while [ ${#running[@]} -ge $MAXJOBS ]; do reap; done
    while [ ${#running[@]} -gt 0 ] && [ "$(free_gb)" -lt $MIN_FREE_GB ]; do reap; done
    until [ "$(free_gb)" -ge $MIN_FREE_GB ]; do echo "waiting for memory ($(free_gb) GB free)"; sleep 60; done
    $PY $RC $C "$@" --out $R/$name > $R/$name.log 2>&1 &
    running[$!]=$name
done
while [ ${#running[@]} -gt 0 ]; do reap; done
if [ $failed -gt 0 ]; then echo "$failed controller runs failed; nothing archived (see $R/*.log)"; exit 1; fi

boots() { for k in $(seq 1 $NBOOT); do echo boot:$R/ctl_$1_boot$k; done; }
step $PY scripts/summarize_scatter_noise.py --runs $(for k in 1 2 3 4 5 6 7 8 9 10; do echo single:$R/ctl_BL95_s$k; done) \
    avg:$R/ctl_BL95_avg flat:$R/ctl_BL95_flat aim:$R/ctl_BLscan_{90,92.5,97.5,100} $(boots BL95) --out $R/scatter_noise_BL95
step $PY scripts/summarize_scatter_noise.py --runs single:$R/ctl_Bp_s{1,2,3,4,5,6,7,8,9,10} avg:$R/ctl_Bp_avg flat:$R/ctl_Bp_flat \
    $(boots Bp) --compare $R/scatter_noise_BL95 --out $R/scatter_noise_Bp

# publish only now that every step succeeded
step cp $R/avg_gas_BL/manifest.json $ST/scattered_tables_B-L_95mm.json
step cp $R/avg_plume_BL/manifest.json $ST/scattered_plume_tables_B-L_95mm.json
step cp $R/avg_plume_Bp/manifest.json $ST/scattered_plume_tables_B-p_97.5mm.json
step cp $R/scatter_noise_BL95/manifest.json $ST/scatter_noise_BL95.json
step cp $R/scatter_noise_Bp/manifest.json $ST/scatter_noise_Bp.json
step cp $R/ctl_BL95_avg/manifest.json $ST/realizable_controller_ms_BL95scatter.json
step cp $R/ctl_Bp_avg/manifest.json $ST/realizable_controller_ms_Bp97scatter.json
echo "all done $(date +%H:%M)"
