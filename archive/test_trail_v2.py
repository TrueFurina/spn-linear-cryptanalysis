import time, sys
from collections import defaultdict

SBOX = (0xC, 0x6, 0x9, 0x0, 0x1, 0xA, 0x2, 0xB,
        0x3, 0x8, 0x5, 0xD, 0x4, 0xE, 0x7, 0xF)

def dot4(a, b):
    z = a & b; z ^= z>>1; z ^= z>>2; return z & 1

LAT = [[0]*16 for _ in range(16)]
for a in range(16):
    for b in range(16):
        cnt = 0
        for x in range(16):
            cnt += 1 if dot4(a,x) == dot4(b,SBOX[x]) else -1
        LAT[a][b] = cnt

def mask_of(nibs):
    r = 0
    for i in range(8): r |= (nibs[i]&0xF) << (28-4*i)
    return r

def nibbles_of(x):
    return [(x >> (28-4*i)) & 0xF for i in range(8)]

def LTi(w):
    w0,w1,w2,w3,w4,w5,w6,w7 = w
    return [w7, w0^w2^w5, w5, w2^w5^w7, w3, w1^w4^w6, w1, w1^w3^w6]

FWD = {a: [(b, LAT[a][b]/16.0) for b in range(1,16) if LAT[a][b]] for a in range(16)}
FWD_S = {a: sorted(FWD[a], key=lambda x: abs(x[1]), reverse=True) for a in range(16)}

def fwd_one_topk(mask, k):
    u = nibbles_of(mask)
    act = [(i,u[i]) for i in range(8) if u[i]]
    if not act: return [(0,1.0)]
    if len(act) == 1:
        pos, alpha = act[0]
        return [(mask_of(LTi([beta if i==pos else 0 for i in range(8)])), c) 
                for beta,c in FWD[alpha]]
    ch = [FWD_S[a][:k] for _,a in act]
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

# Test with various topk
test_cases = [
    (0x01000000, 0x10000000, 5, -2.06493e-5),
    (0x02000000, 0x20000000, 5, -7.2122e-6),
    (0x04000000, 0x40000000, 5, 5.0068e-6),
    (0x08000000, 0x80000000, 5, -6.0201e-6),
    (0x01000000, 0x10000000, 6, 1.43573e-5),
]

for k in [2, 3]:
    print(f"\n=== topk={k} ===", flush=True)
    budget = 1000
    for u, v, R, vt in test_cases:
        t0 = time.time()
        state = {u: 1.0}
        for ri in range(R):
            ns = defaultdict(float)
            for m,c in state.items():
                for nm,nc in fwd_one_topk(m, k):
                    ns[nm] += c*nc
            n_out = len(ns)
            if n_out > budget:
                items = sorted(ns.items(), key=lambda x: abs(x[1]), reverse=True)
                state = dict(items[:budget])
            else:
                state = dict(ns)
        ve = state.get(v, 0.0)
        ratio = ve/vt if abs(vt) > 1e-15 else float('inf')
        ok = 0.75 <= abs(ratio) <= 1.25
        elapsed = time.time()-t0
        print(f"  R={R} V_E={ve:.8e} V_T={vt:.8e} ratio={ratio:.4f} {'OK' if ok else 'MISS'} ({elapsed:.2f}s)", flush=True)
