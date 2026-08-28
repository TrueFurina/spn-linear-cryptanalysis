#!/usr/bin/env python3
"""
快速分析：c_2 vs V_T平台，不计算R=3/4（太慢）
"""
import sys, math, re
from collections import defaultdict
from computecor_hull_v4 import init_lat, init_trans, fwd_one_full, exact_corr_R2

init_lat()
init_trans()

# Read V_T data
vt_data = defaultdict(list)
with open("D:/University/密码学/密码数学挑战赛/result.txt", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line[0] != '@': continue
        parts = line.split(',')
        R = int(parts[0].split('(')[1])
        u = int(parts[1].strip(), 16)
        v = int(parts[2].strip(), 16)
        vt = float(parts[3].strip())
        vt_data[(u,v)].append((R, vt))

print("=" * 100)
print("c_2 → V_T plateau analysis (R=3/4 exact skipped — combinatorial explosion)")
print("=" * 100)

all_abs_vt = []

for (u, v), entries in sorted(vt_data.items()):
    c2 = exact_corr_R2(u, v)
    abs_vts = [abs(e[1]) for e in entries if e[0] >= 5]
    if not abs_vts:
        continue
    
    avg_vt = sum(abs_vts) / len(abs_vts)
    geo_vt = 10 ** (sum(math.log10(x) for x in abs_vts) / len(abs_vts))
    min_vt = min(abs_vts)
    max_vt = max(abs_vts)
    
    # Sign consistency
    signs_ok = 0
    signs_total = 0
    for R, vt in entries:
        if R >= 5:
            expected = -1 if R % 2 == 1 else 1
            if vt * expected > 0:
                signs_ok += 1
            signs_total += 1
    
    all_abs_vt.extend(abs_vts)
    
    print(f"u=0x{u:08X} v=0x{v:08X}  c2={c2:+.6e}  "
          f"avg|VT|={avg_vt:.2e}  geo|VT|={geo_vt:.2e}  "
          f"range=[{min_vt:.1e},{max_vt:.1e}]  "
          f"sign: {signs_ok}/{signs_total}")

print(f"\nOverall |V_T| distribution ({len(all_abs_vt)} entries):")
all_abs_vt.sort()
for pct in [10, 25, 50, 75, 90]:
    idx = len(all_abs_vt) * pct // 100
    print(f"  P{pct}: {all_abs_vt[idx]:.2e}")
print(f"  mean: {sum(all_abs_vt)/len(all_abs_vt):.2e}")
print(f"  min:  {min(all_abs_vt):.2e}")
print(f"  max:  {max(all_abs_vt):.2e}")

# Per-round analysis
print(f"\nPer-round |V_T| geomean:")
for R in range(5, 21):
    vals = []
    for (u,v), entries in vt_data.items():
        for r, vt in entries:
            if r == R:
                vals.append(abs(vt))
    if vals:
        geo = 10 ** (sum(math.log10(x) for x in vals) / len(vals))
        print(f"  R={R:2d}: n={len(vals):2d}  geomean={geo:.2e}")
