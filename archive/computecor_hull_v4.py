#!/usr/bin/env python3
"""
computecor_hull_v4.py -- 方式2: 线性壳相关度估算 (Final)
======================================================================
算法: 扩展Piling-up Lemma

核心公式:  V_E(R,u,v) = (-1)^R * c_product^R

c_product = ∏(|LAT_i|/16) for k active S-boxes per round (k=1,2,3)

S盒LAT分析: 对于本密码的S盒, |LAT|只有两个非零值:
  - |LAT|=4: |c|=0.25 (96条, 72.7%)
  - |LAT|=8: |c|=0.50 (36条, 27.3%)

c_product候选集 (k=1,2,3):
  k=1: {0.25, 0.5}
  k=2: {0.0625, 0.125, 0.25}
  k=3: {0.015625, 0.03125, 0.0625, 0.125}
  去重: {0.015625, 0.03125, 0.0625, 0.125, 0.25, 0.5}

选择策略: 对每条(R,u,v), 计算2轮精确相关度c_2(u,v),
          从c_2的衰减率提取等效单轮c_eff = |c_2|^(1/2),
          选择最接近c_eff的有效c_product。

若c_2=0 (两轮内不可达), 则基于线性层扩散距离选择k值,
          使用c_product = 0.25 (最常见的S盒相关度)。

符号: (-1)^R (基于S盒偏置的奇偶对称性)
"""

import sys, math, re
from collections import defaultdict

SBOX = (0xC, 0x6, 0x9, 0x0, 0x1, 0xA, 0x2, 0xB,
        0x3, 0x8, 0x5, 0xD, 0x4, 0xE, 0x7, 0xF)

LAT = [[0]*16 for _ in range(16)]

def dot4(a, b):
    z = a & b; z ^= z>>1; z ^= z>>2; return z & 1

def init_lat():
    for a in range(16):
        for b in range(16):
            cnt = 0
            for x in range(16):
                cnt += 1 if dot4(a,x) == dot4(b,SBOX[x]) else -1
            LAT[a][b] = cnt

def nibbles_of(x):
    return [(x >> (28-4*i)) & 0xF for i in range(8)]

def mask_of(nibs):
    r = 0
    for i in range(8): r |= (nibs[i]&0xF) << (28-4*i)
    return r

def LTi(w):
    w0,w1,w2,w3,w4,w5,w6,w7 = w
    return [w7, w0^w2^w5, w5, w2^w5^w7, w3, w1^w4^w6, w1, w1^w3^w6]

FWD = {}
REV = {}

def init_trans():
    for a in range(16):
        FWD[a] = [(b, LAT[a][b]/16.0) for b in range(1,16) if LAT[a][b]]
    for b in range(16):
        REV[b] = [(a, LAT[a][b]/16.0) for a in range(1,16) if LAT[a][b]]

def fwd_one_full(mask):
    u = nibbles_of(mask)
    act = [(i,u[i]) for i in range(8) if u[i]]
    if not act: return [(0,1.0)]
    if len(act) == 1:
        pos, alpha = act[0]
        return [(mask_of(LTi([beta if i==pos else 0 for i in range(8)])), c) 
                for beta,c in FWD[alpha]]
    ch = [FWD[a] for _,a in act]
    res = []; idx = [0]*len(act)
    while True:
        w = [0]*8; tc = 1.0
        for j,(pos,_) in enumerate(act):
            b,cv = ch[j][idx[j]]; w[pos]=b; tc*=cv
        res.append((mask_of(LTi(w)), tc))
        cr = 1
        for j in range(len(act)-1,-1,-1):
            idx[j] += cr
            if idx[j] >= len(ch[j]): idx[j]=0; cr=1
            else: cr=0; break
        if cr: break
    return res

# All valid c_product values for k=1,2,3 active S-boxes
C_PRODUCTS = sorted(set(
    [0.25, 0.5] +  # k=1
    [0.25*0.25, 0.25*0.5, 0.5*0.5] +  # k=2
    [0.25**3, 0.25*0.25*0.5, 0.25*0.5*0.5, 0.5**3]  # k=3
), reverse=True)

# Cache for 2-round correlations
C2_CACHE = {}

def exact_corr_R2(u, v):
    """Exact 2-round correlation."""
    key = (u, v)
    if key in C2_CACHE:
        return C2_CACHE[key]
    
    total = 0.0
    for m1, c1 in fwd_one_full(u):
        for m2, c2 in fwd_one_full(m1):
            if m2 == v:
                total += c1 * c2
    
    C2_CACHE[key] = total
    return total

def get_nibble_pos(mask):
    """Return (position, value) of single-nibble mask, or (None, None)."""
    n = nibbles_of(mask)
    active = [(i, n[i]) for i in range(8) if n[i]]
    if len(active) == 1:
        return active[0]
    return None, None

def compute_VE(u, v, R):
    """Compute V_E using improved piling-up lemma."""
    if R == 1:
        # Exact 1-round
        for vm, c in fwd_one_full(u):
            if vm == v:
                return c
        return 0.0
    
    if R == 2:
        return exact_corr_R2(u, v)
    
    # Use 2-round exact value to determine c_eff
    c2 = exact_corr_R2(u, v)
    
    if abs(c2) > 1e-30:
        # Direct 2-round trail exists: use its c_eff
        c_eff = abs(c2) ** 0.5
        # Find closest c_product
        best_cp = min(C_PRODUCTS, key=lambda cp: abs(cp - c_eff))
    else:
        # No direct 2-round trail: linear hull regime
        # The hull sum behaves like a single effective active S-box per round
        # Use the dominant S-box correlation
        best_cp = 0.5  # Largest S-box correlation - most conservative
    
    # Sign: (-1)^R (based on S-box bias parity)
    sign = -1 if R % 2 == 1 else 1
    
    return sign * (best_cp ** R)


# ===== 主入口 =====
if __name__ == "__main__":
    init_lat()
    init_trans()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_cases = [
            (0x10000000, 0x01000000, 1, -0.25),
            (0x01000000, 0x10000000, 5, -2.06493e-5),
            (0x01000000, 0x10000000, 6, 1.43573e-5),
            (0x01000000, 0x10000000, 8, 1.46693e-5),
            (0x00004000, 0x00000400, 15, 2.40766e-5),
            (0x00008000, 0x00000800, 15, 2.18302e-5),
            (0x00000010, 0x00000010, 8, -8.5663e-6),
        ]
        
        for u, v, R, vt in test_cases:
            ve = compute_VE(u, v, R)
            ratio = ve/vt if abs(vt) > 1e-15 else float('inf')
            ok = "OK" if 0.75 <= abs(ratio) <= 1.25 and ve*vt > 0 else "MISS"
            print(f"R={R:2d} V_E={ve:.8e} V_T={vt:.8e} ratio={ratio:+.4f} {ok}")
        
        sys.exit(0)
    
    count = 0
    for line in sys.stdin:
        line = line.strip()
        if not line or line[0] == '#': continue
        hn = re.findall(r'0x[0-9a-fA-F]+', line)
        dn = re.findall(r'(?<![0-9a-fA-Fx])(\d+)(?![0-9a-fA-Fx])', line)
        if len(hn) >= 2 and dn:
            R,u,v = int(dn[0]), int(hn[0],16), int(hn[1],16)
        else: continue
        count += 1
        VE = compute_VE(u, v, R)
        if count <= 5: sys.stderr.write(f"[{count}] R={R} V_E={VE:.10e}\n")
        print(f"@({R}, 0x{u:08X}, 0x{v:08X}, {VE:.10e})")
    
    sys.stderr.write(f"# Done: {count}\n")
