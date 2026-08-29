"""
Method 1 (Exact) via Linear-Hull DP over LAT
============================================
Exact correlation C(u,v) over R rounds = sum over ALL linear trails of
product of S-box correlations (linear-hull theorem). This is MATHEMATICALLY
equivalent to exhaustive 2^32-plaintext Method 1, but uses the LAT structure
so it is feasible for small R.

Round function: Y = L(S(X)), S bitwise S-box, L = MC o SR (linear).
Mask propagation (FORWARD in mask space):
  input mask a_i -> S-box output mask beta_i (chosen, LAT[a_i][beta_i]!=0)
  -> next input mask a_{i+1} = L^{-T}(beta_i).
Transition is a matrix multiply: C_R(u,v) = (M^R)[v][u],
  M[a'][a] = LAT[a][ L^T(a') ]/16  (beta = L^T(a')).

We build L^T (value space) from the C++ SR+MC recurrence, invert it over
GF(2)^32 to get L^{-T}, then run sparse DP for R up to R_MAX.
"""
import os, math, re, sys, io
from itertools import product
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)

# Auto-locate results/ so this script runs from any cwd (repo root or results/)
_HERE = os.path.dirname(os.path.abspath(__file__))
_RS = os.path.join(os.path.dirname(_HERE), 'results')
if os.path.isdir(_RS) and os.path.exists(os.path.join(_RS, 'result_method2_merged.txt')):
    os.chdir(_RS)

SBOX = [0xC,0x6,0x9,0x0,0x1,0xA,0x2,0xB,0x3,0x8,0x5,0xD,0x4,0xE,0x7,0xF]
LAT = [[0]*16 for _ in range(16)]
for a in range(16):
    for b in range(16):
        c = 0
        for x in range(16):
            ax = bin(a & x).count('1') % 2
            bs = bin(b & SBOX[x]).count('1') % 2
            c += 1 if ax == bs else -1
        LAT[a][b] = c

def m2n(m):
    return [(m >> (4*(7-i))) & 0xF for i in range(8)]
def n2m(ns):
    m = 0
    for i in range(8):
        m |= (ns[i] & 0xF) << (4*(7-i))
    return m

# L^T in value space (transpose of the SR+MC linear map)
def apply_LT(nibs):
    n0,n1,n2,n3,n4,n5,n6,n7 = nibs
    return [n0^n1^n3, n6, n0^n2^n3, n4, n4^n5^n7, n2, n4^n6^n7, n0]
def LT_mask(m):
    return n2m(apply_LT(m2n(m)))

# Build 32x32 GF(2) matrix for apply_LT and invert -> L^{-T}
def build_inverse():
    # matrix M: M[row][col] = bit (row) of apply_LT(unit col)
    N = 32
    mat = [[0]*N for _ in range(N)]
    for col in range(N):
        x = 1 << col
        y = LT_mask(x)
        for row in range(N):
            mat[row][col] = (y >> row) & 1
    # augment with identity, Gaussian elimination over GF(2)
    aug = [row[:] + [1 if i == j else 0 for j in range(N)] for i, row in enumerate(mat)]
    for i in range(N):
        # find pivot
        piv = None
        for r in range(i, N):
            if aug[r][i] == 1:
                piv = r; break
        if piv is None:
            raise ValueError("L^T singular - cannot invert")
        aug[i], aug[piv] = aug[piv], aug[i]
        for r in range(N):
            if r != i and aug[r][i] == 1:
                for c in range(2*N):
                    aug[r][c] ^= aug[i][c]
    inv = [[aug[i][N+c] for c in range(N)] for i in range(N)]
    return inv

INV = build_inverse()
def LinvT_mask(m):
    out = 0
    for row in range(32):
        bit = 0
        for col in range(32):
            if INV[row][col]:
                bit ^= (m >> col) & 1
        if bit:
            out |= (1 << row)
    return out

def exact_correlation(u, v, R, R_MAX_STATES=2000000):
    dp = {u: 1.0}
    for r in range(R):
        new_dp = defaultdict(float)
        for a, val in dp.items():
            if val == 0.0:
                continue
            nibs_a = m2n(a)
            choices = []
            for j in range(8):
                aj = nibs_a[j]
                opts = []
                if aj == 0:
                    opts = [(0, 1.0)]
                else:
                    for bj in range(16):
                        if LAT[aj][bj] != 0:
                            opts.append((bj, LAT[aj][bj] / 16.0))
                choices.append(opts)
            for combo in product(*choices):
                beta_nibs = [c[0] for c in combo]
                factor = 1.0
                for c in combo:
                    factor *= c[1]
                beta = n2m(beta_nibs)
                a_next = LinvT_mask(beta)
                new_dp[a_next] += val * factor
        dp = new_dp
        if len(dp) > R_MAX_STATES:
            return None  # too big, abort
    return dp.get(v, 0.0)

# Verify R=1 exact
assert abs(exact_correlation(0x10000000, 0x01000000, 1) - (-0.25)) < 1e-9, "R=1 self-test failed"
print("R=1 self-test OK (=-0.25)")

# Load entries and verify low-R ones
with open('result_method2_merged.txt') as f:
    content = f.read()
pat = r'@\((\d+),\s*(0x[0-9a-fA-F]+),\s*(0x[0-9a-fA-F]+),\s*([0-9eE.+-]+),\s*([0-9eE.+-]+)\)'
ms = re.findall(pat, content)
entries = [(int(m[0]), int(m[1],16), int(m[2],16), float(m[3]), float(m[4])) for m in ms]

R_MAX_VERIFY = 4
verified = 0
mismatches = []
for R, u, v, VT, VE in entries:
    if R > R_MAX_VERIFY:
        continue
    ct = exact_correlation(u, v, R)
    if ct is None:
        print(f"  R={R} u=0x{u:08X} v=0x{v:08X}: state explosion, skipped")
        continue
    err = abs(ct - VT) / max(abs(VT), 1e-12)
    status = "OK" if err < 1e-6 else "MISMATCH"
    if status == "OK":
        verified += 1
    else:
        mismatches.append((R, u, v, VT, ct, err))
    print(f"  R={R} u=0x{u:08X} v=0x{v:08X}: claimed={VT:.6e} exact={ct:.6e} err={err:.2e} [{status}]")

print(f"\nVerified (R<= {R_MAX_VERIFY}): {verified} OK, {len(mismatches)} mismatch")
if mismatches:
    print("MISMATCHES:")
    for R, u, v, VT, ct, err in mismatches:
        print(f"  R={R} u=0x{u:08X} v=0x{v:08X}: claimed={VT:.6e} exact={ct:.6e}")
