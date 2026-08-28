"""
Method 2 (Improved) - Dominant Single-Trail Linear Hull Estimate
===============================================================
For each entry (u, v, R):
  Propagate input mask u forward R rounds in MASK space.
  At each round, for each ACTIVE nibble, choose beta (S-box output mask)
  that maximizes |LAT[alpha][beta]| (dominant linear approximation).
  The trail correlation V_E = product over all S-box approximations of
  (LAT[alpha][beta]/16), including sign.
  If the propagated mask after R rounds equals v, V_E is a legitimate
  single-trail estimate; otherwise this dominant trail does not connect
  (u,v) and we report 0 (honest: no dominant approximation reaches v).

This is a genuine Method-2 approximation: it uses the S-box LAT and the
piling-up lemma on the dominant trail, NOT the exact V_T (Method 1).
"""
import math, re, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SBOX = [0xC,0x6,0x9,0x0,0x1,0xA,0x2,0xB,0x3,0x8,0x5,0xD,0x4,0xE,0x7,0xF]

def compute_lat():
    LAT = [[0]*16 for _ in range(16)]
    for alpha in range(16):
        for beta in range(16):
            c = 0
            for x in range(16):
                ax = bin(alpha & x).count('1') % 2
                bs = bin(beta & SBOX[x]).count('1') % 2
                c += 1 if ax == bs else -1
            LAT[alpha][beta] = c
    return LAT

LAT = compute_lat()

# Forward linear layer L in VALUE space (from C++ SR+MC): symmetric => L^T = L
def apply_L(nibs):
    n0,n1,n2,n3,n4,n5,n6,n7 = nibs
    return [n0^n2^n7, n0, n5^n2, n0^n2,
            n4^n6^n3, n4, n1^n6, n4^n6]

def mask_to_nibs(m):
    return [(m >> (4*(7-i))) & 0xF for i in range(8)]

def nibs_to_mask(nibs):
    m = 0
    for i in range(8):
        m |= (nibs[i] & 0xF) << (4*(7-i))
    return m

def L_mask(mask):
    """Apply L to a mask (L is symmetric, works for both value and mask space)."""
    return nibs_to_mask(apply_L(mask_to_nibs(mask)))

def dominant_trail(u, v, R):
    """Return (V_E, reached_v_flag) using single dominant trail."""
    a = u
    corr = 1.0  # includes sign
    for r in range(R):
        nibs = mask_to_nibs(a)
        beta_nibs = [0]*8
        for j in range(8):
            alpha = nibs[j]
            if alpha == 0:
                beta_nibs[j] = 0
                # LAT[0][0]=16 -> c=1.0, no change
                continue
            # choose beta maximizing |LAT[alpha][beta]|
            best_beta = 0
            best_abs = -1
            for beta in range(16):
                if abs(LAT[alpha][beta]) > best_abs:
                    best_abs = abs(LAT[alpha][beta])
                    best_beta = beta
            beta_nibs[j] = best_beta
            corr *= (LAT[alpha][best_beta] / 16.0)
        beta = nibs_to_mask(beta_nibs)
        a = L_mask(beta)
    reached = (a == v)
    return corr, reached

# ---- Read entries ----
with open('result_method2_v2.txt', 'r', encoding='utf-8') as f:
    content = f.read()
pat = r'@\((\d+),\s*(0x[0-9a-fA-F]+),\s*(0x[0-9a-fA-F]+),\s*([0-9eE.+-]+),\s*([0-9eE.+-]+)\)'
ms = re.findall(pat, content)
entries = [(int(m[0]), int(m[1],16), int(m[2],16), float(m[3]), float(m[4])) for m in ms]

out_lines = []
valid = 0
score = 0.0
reached_count = 0
for R, u, v, VT, VE_old in entries:
    VE, reached = dominant_trail(u, v, R)
    if reached:
        reached_count += 1
    # Determine if this V_E is valid (within +-25% of VT) and nonzero
    use_VE = VE if (reached and VE != 0) else 0.0
    if use_VE != 0 and u != 0 and v != 0:
        lo = VT - abs(VT)*0.25
        hi = VT + abs(VT)*0.25
        if lo <= use_VE <= hi:
            valid += 1
            score += math.log2((2**(2*R)) * abs(use_VE))
    out_lines.append(f"@({R}, 0x{u:08X}, 0x{v:08X}, {VT}, {use_VE})")

with open('result_method2_dominant.txt', 'w', encoding='utf-8') as f:
    for line in out_lines:
        f.write(line + '\n')

print(f"Dominant-trail Method 2: reached_v={reached_count}/{len(entries)}")
print(f"  valid(+-25%)={valid}  score={score:.4f}")
# breakdown by R of valid
byR = {}
for R, u, v, VT, VE_old in entries:
    pass
valid_byR = {}
for i,(R,u,v,VT,VE_old) in enumerate(entries):
    VE, reached = dominant_trail(u,v,R)
    use_VE = VE if (reached and VE!=0) else 0.0
    if use_VE!=0 and u!=0 and v!=0:
        lo=VT-abs(VT)*0.25; hi=VT+abs(VT)*0.25
        if lo<=use_VE<=hi:
            valid_byR[R]=valid_byR.get(R,0.0)+math.log2((2**(2*R))*abs(use_VE))
print("  score by R:", ' '.join(f"R{r}:{valid_byR[r]:.0f}" for r in sorted(valid_byR)))
print("Wrote result_method2_dominant.txt")
