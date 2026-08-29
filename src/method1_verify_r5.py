"""
Targeted: verify V_T for ALL R==5 entries via exact linear-hull DP (Method 1).
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
        c=0
        for x in range(16):
            ax=bin(a&x).count('1')%2; bs=bin(b&SBOX[x]).count('1')%2
            c+=1 if ax==bs else -1
        LAT[a][b]=c
def m2n(m): return [(m>>(4*(7-i)))&0xF for i in range(8)]
def n2m(ns):
    m=0
    for i in range(8): m|=(ns[i]&0xF)<<(4*(7-i))
    return m
def apply_LT(nibs):
    n0,n1,n2,n3,n4,n5,n6,n7=nibs
    return [n0^n1^n3, n6, n0^n2^n3, n4, n4^n5^n7, n2, n4^n6^n7, n0]
def LT_mask(m): return n2m(apply_LT(m2n(m)))
# invert L^T over GF(2)^32
N=32
mat=[[0]*N for _ in range(N)]
for col in range(N):
    y=LT_mask(1<<col)
    for row in range(N): mat[row][col]=(y>>row)&1
aug=[mat[i][:]+[1 if i==j else 0 for j in range(N)] for i in range(N)]
for i in range(N):
    piv=None
    for r in range(i,N):
        if aug[r][i]==1: piv=r;break
    aug[i],aug[piv]=aug[piv],aug[i]
    for r in range(N):
        if r!=i and aug[r][i]==1:
            for c in range(2*N): aug[r][c]^=aug[i][c]
INV=[[aug[i][N+c] for c in range(N)] for i in range(N)]
def LinvT_mask(m):
    out=0
    for row in range(32):
        bit=0
        for col in range(32):
            if INV[row][col]: bit^=(m>>col)&1
        if bit: out|=1<<row
    return out
def exact_correlation(u,v,R,RMAX=5000000):
    dp={u:1.0}
    for r in range(R):
        nd=defaultdict(float)
        for a,val in dp.items():
            if val==0.0: continue
            na=m2n(a); choices=[]
            for j in range(8):
                aj=na[j]; opts=[]
                if aj==0: opts=[(0,1.0)]
                else:
                    for bj in range(16):
                        if LAT[aj][bj]!=0: opts.append((bj,LAT[aj][bj]/16.0))
                choices.append(opts)
            for combo in product(*choices):
                bn=[c[0] for c in combo]; f=1.0
                for c in combo: f*=c[1]
                nd[LinvT_mask(n2m(bn))]+=val*f
        dp=nd
        if len(dp)>RMAX: return None
    return dp.get(v,0.0)

with open('result_method2_merged.txt') as f: content=f.read()
pat=r'@\((\d+),\s*(0x[0-9a-fA-F]+),\s*(0x[0-9a-fA-F]+),\s*([0-9eE.+-]+),\s*([0-9eE.+-]+)\)'
ms=re.findall(pat,content)
print("=== R=5 exact V_T verification ===")
ok=0; bad=0
for m in ms:
    R=int(m[0]); u=int(m[1],16); v=int(m[2],16); VT=float(m[3])
    if R!=5: continue
    ct=exact_correlation(u,v,5)
    if ct is None:
        print(f"  R=5 u=0x{u:08X} v=0x{v:08X}: state explosion"); continue
    err=abs(ct-VT)/max(abs(VT),1e-12); st="OK" if err<1e-6 else "MISMATCH"
    ok+= st=="OK"; bad+= st!="OK"
    print(f"  u=0x{u:08X} v=0x{v:08X}: claimed={VT:.6e} exact={ct:.6e} err={err:.2e} [{st}]")
print(f"R=5: ok={ok} mismatch={bad}")
