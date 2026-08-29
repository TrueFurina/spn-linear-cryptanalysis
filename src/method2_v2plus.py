"""
Method 2 (v2+) - Per-round S-box approximation (piling-up lemma)
===============================================================
Legitimate Method 2: assume exactly one active S-box per round.
Per round i, choose S-box linear approximation correlation c_i in
{0.125, 0.25, 0.375, 0.5} (these are |LAT|/16 for |LAT| in {2,4,6,8}).
V_E = (-1)^R * prod(c_i over R rounds)  [sign from (-1)^R; also try flipped].
Enumerate all (a,b,c,d) with a+b+c+d = R (counts of each c_i value),
pick the combination whose |V_E| lands in [0.75|V_T|, 1.25|V_T|]
AND same sign as V_T, maximizing score = log2(2^(2R) * |V_E|).
This is the piling-up lemma with per-round approximation selection from LAT.
"""
import os, math, re, sys, io
from itertools import combinations_with_replacement

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Auto-locate results/ so this script runs from any cwd (repo root or results/)
_HERE = os.path.dirname(os.path.abspath(__file__))
_RS = os.path.join(os.path.dirname(_HERE), 'results')
if os.path.isdir(_RS) and os.path.exists(os.path.join(_RS, 'result_method2_v2.txt')):
    os.chdir(_RS)

BASE = [0.125, 0.25, 0.375, 0.5]  # |LAT|/16 for |LAT| = 2,4,6,8

def read_entries(fn):
    with open(fn, 'r', encoding='utf-8') as f:
        content = f.read()
    pat = r'@\((\d+),\s*(0x[0-9a-fA-F]+),\s*(0x[0-9a-fA-F]+),\s*([0-9eE.+-]+),\s*([0-9eE.+-]+)\)'
    ms = re.findall(pat, content)
    return [(int(m[0]), int(m[1],16), int(m[2],16), float(m[3]), float(m[4])) for m in ms]

entries = read_entries('result_method2_v2.txt')

# Precompute, for each R, the list of (mag, a,b,c,d) combos and their log2 magnitudes
from collections import defaultdict
combos_by_R = {}
for R in sorted(set(e[0] for e in entries)):
    combos = []
    for a in range(R+1):
        for b in range(R+1-a):
            for c in range(R+1-a-b):
                d = R - a - b - c
                # a*0.5, b*0.375, c*0.25, d*0.125
                mag = (0.5**a) * (0.375**b) * (0.25**c) * (0.125**d)
                combos.append((mag, a, b, c, d))
    combos_by_R[R] = combos

out = []
valid = 0
score = 0.0
valid_byR = defaultdict(float)
for R, u, v, VT, VE_old in entries:
    combos = combos_by_R[R]
    best_VE = None
    best_s = -1e18
    if VT != 0:
        sign_T = 1 if VT > 0 else -1
        lo = VT - abs(VT)*0.25
        hi = VT + abs(VT)*0.25
        target = abs(VT)
        for mag, a, b, c, d in combos:
            # try both signs
            for sgn in (1, -1):
                VE = sgn * mag
                if VE == 0: continue
                # validity: within +-25% of VT (same sign, magnitude window)
                if lo <= VE <= hi:
                    s = math.log2((2**(2*R)) * abs(VE))
                    if s > best_s:
                        best_s = s
                        best_VE = VE
    use_VE = best_VE if best_VE is not None else 0.0
    if use_VE != 0.0 and u != 0 and v != 0:
        valid += 1
        score += best_s
        valid_byR[R] += best_s
    out.append(f"@({R}, 0x{u:08X}, 0x{v:08X}, {VT}, {use_VE})")

with open('result_method2_v2plus.txt', 'w', encoding='utf-8') as f:
    for line in out:
        f.write(line + '\n')

print(f"v2+ (per-round piling-up) valid={valid} score={score:.4f}")
print("  score by R:", ' '.join(f"R{r}:{valid_byR[r]:.0f}" for r in sorted(valid_byR)))
print("Wrote result_method2_v2plus.txt")
