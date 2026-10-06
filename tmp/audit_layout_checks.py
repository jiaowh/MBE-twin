import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('lc', root / 'scripts/layout_comparison.py')
lc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lc)
m = json.loads((root / 'data/runs/studies/layout_comparison.json').read_text())
for name in ('layout_comparison', 'layout_feasibility'):
    rec = json.loads((root / f'data/runs/studies/{name}.json').read_text())
    bad = [p for p, h in rec['source_sha256'].items()
           if hashlib.sha256((root / p).read_bytes().replace(b'\r\n', b'\n')).hexdigest() != h]
    print('hashes', name, len(rec['source_sha256']), 'mismatches', bad)

atoms_per_sccm = 2 * lc.pressure_from_flow(1, 1, 273.15) / (1.380649e-23 * 273.15)
print('N atoms per second per sccm', atoms_per_sccm)
for row in m['outputs']['rows']:
    if row['T0_C'] == 740 and row['heater_limit'] == '1473 K element' and row['pressure_case'] == '2 sccm / 2 m3/s':
        print(row['layout'], 'nominal', row['nominal'], 'min flow', row['nominal']['q_atoms_s']/atoms_per_sccm,
              'heater temperatures', row['heater']['state_t_heater_max_K'])

rho = np.linspace(0, .094, 39)
params = lc.load_parameters()
n = np.stack([np.ones_like(rho), 1 + .2*(rho/.094)**2])[:,None,:]
ga = np.ones((1,1,len(rho)))
t = np.full((1,len(rho)), 1013.15)
original = lc.steady_state
captured = {}
def capture(j_ga, j_n, *args):
    captured['ga_centre'] = j_ga[...,0].copy()
    return original(j_ga, j_n, *args)
lc.steady_state = capture
lc.evaluate(n, ga, t, params, 'Ref14_growth', rho, 1000/60, 7.296e17, (0,0,0,0))
print('Ga centres under purported hold', captured['ga_centre'].ravel().tolist())
print('quadratic area mean actual', lc.area_mean((rho/.094)**2, rho), 'exact', .5)
lc.steady_state = original

# Reproduce the recorded B/C nominal values using cached maps and freshly computed heater maps.
env = m['inputs']['envelope']
pressures = list(m['inputs']['pressure_cases_Pa'])
pi = pressures.index('2 sccm / 2 m3/s')
tm, hr = lc.heater_states('designed density', .099, 1013.15, 1473.15, rho)
for name in ('B', 'C'):
    lay = env['layouts'][name]
    nn = lay['n']
    z = np.load(root / f"results/layout_comparison/N_{nn['L_over_r']:g}_{nn['polar_deg']:g}_{nn['aim_offset_mm']:g}.npz")
    nfull = z['maps'][:,None,:] * z['att'][pi][None,None,:] * z['lip_1 mm overlap'][None,:,:]
    labels = [(fill,d) for fill in (40,70,120) for d in lc.GA_D]
    gmaps = []
    for fill,d in labels:
        gz = np.load(root / f'results/layout_comparison/Ga_46_{fill}.npz')
        gg = lc.ga_shape(lc.ga_record(46,fill,d),rho)[None,:] * gz[f'att_{d}'][pi][None,:] * gz['lip_1 mm overlap']
        gmaps.append(gg / gg[:,:1])
    gm = np.array(gmaps)
    res = lc.evaluate(nfull,gm,tm,params,'Ref14_growth',rho,1000/60,m['inputs']['atoms_per_m2_s_per_nm_min'],(0,3,0,1))
    print('reproduced',name,'nominal thickness',res['thickness'][0,3,0,1], 'q',res['q'][0,3,0,1])
