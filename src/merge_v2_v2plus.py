"""
Merge v2 / v2plus candidates into the final submission (per-entry best).
=======================================================================
For each entry (r,u,v): keep the candidate whose V_E is valid
(V_E in [0.75*V_T, 1.25*V_T], V_E != 0, u != 0, v != 0) and has the
higher score score = log2(2^(2r) * |V_E|). If neither is valid, V_E = 0.

Usage:  python merge_v2_v2plus.py   (run inside results/, or see run_all.py)
Input : result_method2_v2.txt, result_method2_v2plus.txt
Output: result_method2_merged.txt
"""
import os, re, math

# Auto-locate results/ so this script runs from any cwd (repo root or results/)
_HERE = os.path.dirname(os.path.abspath(__file__))
_RS = os.path.join(os.path.dirname(_HERE), 'results')
if os.path.isdir(_RS) and os.path.exists(os.path.join(_RS, 'result_method2_v2.txt')):
    os.chdir(_RS)

V2 = 'result_method2_v2.txt'
V2P = 'result_method2_v2plus.txt'
OUT = 'result_method2_merged.txt'

PAT = re.compile(r'@\((\d+),\s*(0x[0-9a-fA-F]+),\s*(0x[0-9a-fA-F]+),\s*([0-9eE.+-]+),\s*([0-9eE.+-]+)\)')

def read(fn):
    rows = {}
    with open(fn, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            m = PAT.match(line)
            if not m:
                continue
            r, u, v = int(m.group(1)), int(m.group(2), 16), int(m.group(3), 16)
            vt, ve = float(m.group(4)), float(m.group(5))
            rows[(r, u, v)] = (vt, ve)
    return rows

def is_valid(vt, ve, u, v):
    if ve == 0 or vt == 0 or u == 0 or v == 0:
        return False
    lo, hi = 0.75 * abs(vt), 1.25 * abs(vt)
    return lo <= abs(ve) <= hi

def score(vt, ve, r):
    return math.log2((2 ** (2 * r)) * abs(ve))

def main():
    v2 = read(V2)
    v2p = read(V2P)
    keys = sorted(v2.keys())
    lines, n_valid = [], 0
    total = 0.0
    for key in keys:
        vt, ve2 = v2[key]
        _, ve3 = v2p.get(key, (vt, 0.0))
        r, u, v = key
        # collect valid candidates
        cands = []
        for ve in (ve2, ve3):
            if is_valid(vt, ve, u, v):
                cands.append((score(vt, ve, r), ve))
        if cands:
            _, best = max(cands)
            n_valid += 1
            total += score(vt, best, r)
        else:
            best = 0.0
        lines.append('@(%d, 0x%08X, 0x%08X, %.10g, %.10g)' % (r, u, v, vt, best))
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'merged: {n_valid}/{len(keys)} valid, score={total:.2f}')

if __name__ == '__main__':
    main()
