#!/usr/bin/env python3
"""
computecor_mitm_v3.py — 方式2: 线性壳 + 中间相遇(Meet-in-the-Middle)估算
=====================================================================
将R轮拆成前半段(正向from u)和后半段(反向from v)，在中间状态匹配。

关键修正(v3):
  1. apply_L: 使用正确的正向线性层L(不是(L^T)^{-1})
  2. S-box权重: 使用 LAT/16 (不是 LAT/8)
  3. MITM公式: 直接求和 Σ(fwd*bwd)，不需要 0.5 因子
  4. R=1精确: 直接用 ∏(LAT/16)，不需要 2^(K-1) 因子

理论基础:
  相关矩阵方法: M[v,u] = Σ_trails ∏(LAT[α_i][β_i]/16) 
  即每条线性路线的贡献 = ∏(LAT/16) for active S-boxes
  总相关性 = 所有路线贡献之和 (线性壳)
"""

import sys
import re
import math
from collections import defaultdict

SBOX = (0xC, 0x6, 0x9, 0x0, 0x1, 0xA, 0x2, 0xB,
        0x3, 0x8, 0x5, 0xD, 0x4, 0xE, 0x7, 0xF)

LAT = [[0]*16 for _ in range(16)]

def dot4(a, b):
    z = a & b
    z ^= z >> 1
    z ^= z >> 2
    return z & 1

def init_lat():
    for a in range(16):
        for b in range(16):
            cnt = 0
            for x in range(16):
                cnt += 1 if dot4(a, x) == dot4(b, SBOX[x]) else -1
            LAT[a][b] = cnt

def nibbles_of(x):
    return [(x >> (28 - 4*i)) & 0xF for i in range(8)]

def mask_to_int(nibs):
    x = 0
    for i, n in enumerate(nibs):
        x |= (n << (28 - 4*i))
    return x

def apply_LT(nibs):
    """L^T: 线性层反向传播 (output mask -> input mask)"""
    m0,m1,m2,m3,m4,m5,m6,m7 = nibs
    return [m0^m1^m3, m6, m0^m2^m3, m4,
            m4^m5^m7, m2, m4^m6^m7, m0]

def apply_L(nibs):
    """L: 线性层正向传播 (input mask -> output mask)
    从C++代码推导: SR后MC
    SR: new[0]=old[0], new[1]=old[5], new[2]=old[2], new[3]=old[7],
        new[4]=old[4], new[5]=old[1], new[6]=old[6], new[7]=old[3]
    MC: 
      state[0] = t0^t2^t3 = old[0]^old[2]^old[7]
      state[1] = t0 = old[0]
      state[2] = t1^t2 = old[5]^old[2]
      state[3] = t0^t2 = old[0]^old[2]
      state[4] = t4^t6^t7 = old[4]^old[6]^old[3]
      state[5] = t4 = old[4]
      state[6] = t5^t6 = old[1]^old[6]
      state[7] = t4^t6 = old[4]^old[6]
    """
    n0,n1,n2,n3,n4,n5,n6,n7 = nibs
    return [n0^n2^n7, n0, n5^n2, n0^n2,
            n4^n6^n3, n4, n1^n6, n4^n6]

# S-box forward/backward lookup tables
# 权重 = LAT/16 (单S-box相关性)
sbox_fwd = {}  # forward: alpha -> [(beta, weight)]
sbox_bwd = {}  # backward: beta -> [(alpha, weight)]

def init_sbox_tables():
    global sbox_fwd, sbox_bwd
    sbox_fwd = {}
    sbox_bwd = {}
    for a in range(16):
        if a == 0:
            sbox_fwd[a] = [(0, 1.0)]  # inactive nibble: trivial correlation 1.0
        else:
            entries = []
            for b in range(1, 16):
                if LAT[a][b] != 0:
                    entries.append((b, LAT[a][b] / 16.0))  # LAT/16 = correlation per S-box
            sbox_fwd[a] = entries
    for b in range(16):
        if b == 0:
            sbox_bwd[b] = [(0, 1.0)]
        else:
            entries = []
            for a in range(1, 16):
                if LAT[a][b] != 0:
                    entries.append((a, LAT[a][b] / 16.0))  # LAT/16 = correlation per S-box
            sbox_bwd[b] = entries


def propagate_forward(corr_map, max_size=200000):
    """正向传播一轮: S-box正向 -> L正向"""
    # Step 1: S-box forward (alpha -> beta) 逐个nibble处理
    for i in range(8):
        shift = 28 - 4*i
        nib_mask = 0xF << shift
        new_map = defaultdict(float)
        for mask, corr in corr_map.items():
            alpha = (mask >> shift) & 0xF
            for beta, w in sbox_fwd[alpha]:
                new_mask = (mask & ~nib_mask) | (beta << shift)
                new_map[new_mask] += corr * w
        corr_map = dict(new_map)
        if len(corr_map) > max_size:
            sorted_items = sorted(corr_map.items(), key=lambda x: abs(x[1]), reverse=True)
            corr_map = dict(sorted_items[:max_size])
    
    # Step 2: L forward (linear layer正向)
    new_map = defaultdict(float)
    for mask, corr in corr_map.items():
        nibs = nibbles_of(mask)
        new_nibs = apply_L(nibs)
        new_mask = mask_to_int(new_nibs)
        new_map[new_mask] += corr
    corr_map = dict(new_map)
    
    # Prune small values relative to maximum
    if corr_map:
        max_c = max(abs(c) for c in corr_map.values())
        thresh = max_c * 1e-12
        if thresh > 0:
            corr_map = {m: c for m, c in corr_map.items() if abs(c) > thresh}
    
    return corr_map


def propagate_backward(corr_map, max_size=200000):
    """反向传播一轮: L^T反向 -> S-box反向"""
    # Step 1: L^T (linear layer backward)
    new_map = defaultdict(float)
    for mask, corr in corr_map.items():
        nibs = nibbles_of(mask)
        new_nibs = apply_LT(nibs)
        new_mask = mask_to_int(new_nibs)
        new_map[new_mask] += corr
    corr_map = dict(new_map)
    
    # Step 2: S-box backward (beta -> alpha) 逐个nibble处理
    for i in range(8):
        shift = 28 - 4*i
        nib_mask = 0xF << shift
        new_map = defaultdict(float)
        for mask, corr in corr_map.items():
            beta = (mask >> shift) & 0xF
            for alpha, w in sbox_bwd[beta]:
                new_mask = (mask & ~nib_mask) | (alpha << shift)
                new_map[new_mask] += corr * w
        corr_map = dict(new_map)
        if len(corr_map) > max_size:
            sorted_items = sorted(corr_map.items(), key=lambda x: abs(x[1]), reverse=True)
            corr_map = dict(sorted_items[:max_size])
    
    # Prune small values relative to maximum
    if corr_map:
        max_c = max(abs(c) for c in corr_map.values())
        thresh = max_c * 1e-12
        if thresh > 0:
            corr_map = {m: c for m, c in corr_map.items() if abs(c) > thresh}
    
    return corr_map


def estimate_mitm(u, v, R, max_size=200000):
    """MITM: forward R/2 rounds from u, backward R/2 rounds from v, match in middle
    V_E = Σ(fwd_weight * bwd_weight) for matching masks (no 0.5 factor needed)
    """
    R_fwd = R // 2
    R_bwd = R - R_fwd
    
    # Forward from u
    fwd_map = {u: 1.0}
    for r in range(R_fwd):
        fwd_map = propagate_forward(fwd_map, max_size)
    
    # Backward from v
    bwd_map = {v: 1.0}
    for r in range(R_bwd):
        bwd_map = propagate_backward(bwd_map, max_size)
    
    # Match: V_E = Σ(fwd_weight * bwd_weight) for matching masks
    V_E = 0.0
    # Iterate over smaller map for efficiency
    if len(fwd_map) > len(bwd_map):
        fwd_map, bwd_map = bwd_map, fwd_map
    
    for mask, w_fwd in fwd_map.items():
        if mask in bwd_map:
            V_E += w_fwd * bwd_map[mask]
    
    return V_E


def estimate_r1_exact(u, v):
    """R=1: exact LAT calculation via correlation matrix
    cor_E(v, u) = M_Slayer[L^T(v), u] = ∏ LAT[u_i][L^T(v)_i] / 16
    No piling-up factor needed (already accounted for in Kronecker product)
    """
    u_nib = nibbles_of(u)
    v_nib = nibbles_of(v)
    sbox_out = apply_LT(list(v_nib))  # L^T(v) gives S-box output mask
    corr = 1.0
    for i in range(8):
        alpha = u_nib[i]
        beta = sbox_out[i]
        if alpha == 0 and beta == 0:
            continue  # inactive nibble: contribution = 1.0
        if alpha == 0 or beta == 0:
            return 0.0  # mismatch: one active, one inactive
        if LAT[alpha][beta] == 0:
            return 0.0  # no linear approximation
        corr *= LAT[alpha][beta] / 16.0
    return corr


if __name__ == "__main__":
    init_lat()
    init_sbox_tables()
    
    print("# === Method 2 v3: Linear Hull + MITM (corrected) ===", file=sys.stderr)
    print("# Forward R/2 rounds from u, backward R/2 from v, match in middle", file=sys.stderr)
    print("# =====================================================\n", file=sys.stderr)
    
    count = 0
    valid_count = 0
    
    for line in sys.stdin:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        hex_nums = re.findall(r'0x[0-9a-fA-F]+', line)
        dec_nums = re.findall(r'(?<![0-9a-fA-Fx])(\d+)(?![0-9a-fA-Fx])', line)
        if len(hex_nums) >= 2 and dec_nums:
            R = int(dec_nums[0])
            u = int(hex_nums[0], 16)
            v = int(hex_nums[1], 16)
        else:
            continue
        
        count += 1
        
        if R == 1:
            V_E = estimate_r1_exact(u, v)
        else:
            V_E = estimate_mitm(u, v, R)
        
        if V_E != 0.0:
            valid_count += 1
        
        print(f"@({R}, 0x{u:08X}, 0x{v:08X}, {V_E:.10e})")
        
        if count % 5 == 0:
            print(f"# Progress: {count} entries, {valid_count} valid", file=sys.stderr)
    
    print(f"# =====================================================", file=sys.stderr)
    print(f"# Done: {count} entries, valid estimates: {valid_count}", file=sys.stderr)
