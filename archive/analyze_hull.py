#!/usr/bin/env python3
"""
分析线性壳效应：计算R=1-4精确相关度，分析V_T平台模式
"""
import sys, math, re
from collections import defaultdict
from computecor_hull_v4 import init_lat, init_trans, fwd_one_full, exact_corr_R2, nibbles_of, mask_of

init_lat()
init_trans()

def exact_corr_R3(u, v):
    """Exact 3-round correlation."""
    total = 0.0
    for m1, c1 in fwd_one_full(u):
        for m2, c2 in fwd_one_full(m1):
            for m3, c3 in fwd_one_full(m2):
                if m3 == v:
                    total += c1 * c2 * c3
    return total

def exact_corr_R4(u, v):
    """Exact 4-round correlation."""
    total = 0.0
    for m1, c1 in fwd_one_full(u):
        for m2, c2 in fwd_one_full(m1):
            for m3, c3 in fwd_one_full(m2):
                for m4, c4 in fwd_one_full(m3):
                    if m4 == v:
                        total += c1 * c2 * c3 * c4
    return total

# Test pairs - use ones from result.txt
test_pairs = [
    (0x10000000, 0x01000000, "nib0→nib1"),
    (0x01000000, 0x10000000, "nib1→nib0"),
    (0x00004000, 0x00000400, "nib5→nib6"),
    (0x00000010, 0x00000010, "nib7→nib7"),
    (0x00100000, 0x00100000, "nib3→nib3"),
]

print("=" * 90)
print("Exact correlations R=1..4 for test pairs")
print("=" * 90)

for u, v, label in test_pairs:
    print(f"\n--- {label}: u=0x{u:08X} v=0x{v:08X} ---")
    
    c1 = 0.0
    for m, c in fwd_one_full(u):
        if m == v: c1 = c
    print(f"  R=1: c = {c1:+.6e}")
    
    c2 = exact_corr_R2(u, v)
    print(f"  R=2: c = {c2:+.6e}")
    
    c3 = exact_corr_R3(u, v)
    print(f"  R=3: c = {c3:+.6e}")
    
    c4 = exact_corr_R4(u, v)
    print(f"  R=4: c = {c4:+.6e}")
    
    # Analyze decay
    if abs(c2) > 1e-30:
        c_per_round_2 = abs(c2) ** 0.5
        print(f"  c_eff from R=2: {c_per_round_2:.6f}")
    if abs(c3) > 1e-30 and abs(c2) > 1e-30:
        hull_factor_3 = abs(c3) / (abs(c2) ** 1.5)
        print(f"  Hull factor R=3: c3/c2^1.5 = {hull_factor_3:.4f}")
    if abs(c4) > 1e-30 and abs(c2) > 1e-30:
        hull_factor_4 = abs(c4) / (abs(c2) ** 2.0)
        print(f"  Hull factor R=4: c4/c2^2 = {hull_factor_4:.4f}")

# ===== Analyze V_T data =====
print("\n" + "=" * 90)
print("V_T data analysis")
print("=" * 90)

# Read V_T data
vt_data = defaultdict(list)
with open("D:/University/密码学/密码数学挑战赛/result.txt") as f:
    for line in f:
        line = line.strip()
        if not line or line[0] == '#': continue
        parts = line.split(',')
        if len(parts) >= 4:
            R = int(parts[0].split('(')[1])
            u = int(parts[1].strip(), 16)
            v = int(parts[2].strip(), 16)
            vt = float(parts[3].strip())
            vt_data[(u,v)].append((R, vt))

# Per-pair statistics
print(f"\nUnique (u,v) pairs: {len(vt_data)}")
print(f"{'Pair':<25} {'c2':>12s} {'avg|VT|':>12s} {'min|VT|':>12s} {'max|VT|':>12s} {'avg_log':>10s}")
print("-" * 85)

all_vt_abs = []
pair_stats = []

for (u, v), entries in sorted(vt_data.items()):
    c2 = exact_corr_R2(u, v)
    abs_vts = [abs(e[1]) for e in entries if e[0] >= 5]
    if not abs_vts: continue
    avg_vt = sum(abs_vts) / len(abs_vts)
    min_vt = min(abs_vts)
    max_vt = max(abs_vts)
    avg_log = sum(math.log10(x) for x in abs_vts) / len(abs_vts)
    all_vt_abs.extend(abs_vts)
    
    label = f"0x{u:08X}→0x{v:08X}"
    print(f"{label:<25} {c2:>+12.6e} {avg_vt:>12.6e} {min_vt:>12.6e} {max_vt:>12.6e} {avg_log:>10.2f}")
    
    pair_stats.append((abs(c2), avg_vt, u, v))

print(f"\nOverall V_T statistics (R≥5, {len(all_vt_abs)} entries):")
all_vt_abs.sort()
print(f"  Median |V_T|: {all_vt_abs[len(all_vt_abs)//2]:.6e}")
print(f"  Mean |V_T|:   {sum(all_vt_abs)/len(all_vt_abs):.6e}")
print(f"  P10 |V_T|:    {all_vt_abs[len(all_vt_abs)//10]:.6e}")
print(f"  P90 |V_T|:    {all_vt_abs[len(all_vt_abs)*9//10]:.6e}")
print(f"  Min |V_T|:    {min(all_vt_abs):.6e}")
print(f"  Max |V_T|:    {max(all_vt_abs):.6e}")

# Correlation between c2 and avg VT
print(f"\nCorrelation between |c2| and avg|VT|:")
pair_stats.sort(key=lambda x: x[0])
for abs_c2, avg_vt, u, v in pair_stats:
    label = f"0x{u:08X}→0x{v:08X}"
    print(f"  {label}: |c2|={abs_c2:.6e} → avg|VT|={avg_vt:.6e}")

# Per-round V_T statistics
print(f"\nPer-round |V_T| statistics:")
for R in range(5, 21):
    r_vals = []
    for (u,v), entries in vt_data.items():
        for r, vt in entries:
            if r == R:
                r_vals.append(abs(vt))
    if r_vals:
        avg = sum(r_vals)/len(r_vals)
        geo = 10 ** (sum(math.log10(x) for x in r_vals)/len(r_vals))
        print(f"  R={R:2d}: count={len(r_vals):3d}  mean={avg:.2e}  geomean={geo:.2e}  min={min(r_vals):.2e}  max={max(r_vals):.2e}")

# Sign analysis
print(f"\nSign patterns by (u,v) pair:")
for (u, v), entries in sorted(vt_data.items()):
    signs = []
    for R, vt in sorted(entries):
        expected_sign = -1 if R % 2 == 1 else 1
        actual_sign = 1 if vt > 0 else -1
        signs.append((R, actual_sign, expected_sign, "OK" if actual_sign == expected_sign else "FLIP"))
    ok_count = sum(1 for _, a, e, _ in signs if a == e)
    total = len(signs)
    label = f"0x{u:08X}→0x{v:08X}"
    flips = [(R, a, e) for R, a, e, s in signs if s == "FLIP"]
    flip_str = f"  Flips at R={[r for r,_,_ in flips]}" if flips else ""
    print(f"  {label}: {ok_count}/{total} sign match{flip_str}")
