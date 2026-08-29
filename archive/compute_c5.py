#!/usr/bin/env python3
"""
Compute c_5 for one test pair: (0x10000000, 0x01000000)
Use forward enumeration with aggressive pruning.
"""
from computecor_hull_v4 import init_lat, init_trans, fwd_one_full, exact_corr_R2
from collections import defaultdict
import time

init_lat()
init_trans()

# For (0x10000000, 0x01000000), c1 = -0.25
# This means there's a direct R=1 trail.
# Let's compute c_5 by forward enumeration.

u = 0x10000000
v = 0x01000000

print(f"Enumerating trails u=0x{u:08X} → v=0x{v:08X}")

# Forward enumeration with state dedup
# state = (mask, correlation)
r1_states = defaultdict(float)
for m1, c1 in fwd_one_full(u):
    r1_states[m1] += c1

print(f"Round 1: {len(r1_states)} unique masks")

r2_states = defaultdict(float)
for m1, c1 in r1_states.items():
    for m2, c2 in fwd_one_full(m1):
        r2_states[m2] += c1 * c2
        
print(f"Round 2: {len(r2_states)} unique masks")

r3_states = defaultdict(float)
for m2, c2 in r2_states.items():
    for m3, c3 in fwd_one_full(m2):
        r3_states[m3] += c2 * c3
        
print(f"Round 3: {len(r3_states)} unique masks")

r4_states = defaultdict(float)
for m3, c3 in r3_states.items():
    for m4, c4 in fwd_one_full(m3):
        r4_states[m4] += c3 * c4
        
print(f"Round 4: {len(r4_states)} unique masks")
print(f"c_4(u,v) = {r4_states.get(v, 0.0):+.6e}")

# Check if any v is reached
if v in r4_states:
    print(f"*** c_4 non-zero! value = {r4_states[v]:+.6e}")

r5_states = defaultdict(float)
count = 0
for m4, c4 in r4_states.items():
    count += 1
    if count % 1000 == 0:
        print(f"  R4→R5: processed {count}/{len(r4_states)} masks...")
    for m5, c5 in fwd_one_full(m4):
        r5_states[m5] += c4 * c5

print(f"Round 5: {len(r5_states)} unique masks")
print(f"c_5(u,v) = {r5_states.get(v, 0.0):+.6e}")

if v in r5_states:
    print(f"*** c_5 = {r5_states[v]:+.6e}")

# Also compute V_T for comparison
# From result.txt: @(5, 0x10000000, 0x01000000, -0.0000206493, 48427.83) WAIT
# Actually from the data, (0x10000000, 0x01000000) starts at R=7
# Let me also test (0x01000000, 0x10000000) which has R=5 data
print("\n\nNow testing u=0x01000000 v=0x10000000:")
u2 = 0x01000000
v2 = 0x10000000

r1b = defaultdict(float)
for m, c in fwd_one_full(u2):
    r1b[m] += c
print(f"R1: {len(r1b)} masks, c1={r1b.get(v2,0):+.6e}")

r2b = defaultdict(float)
for m, c in r1b.items():
    for m2, c2 in fwd_one_full(m):
        r2b[m2] += c * c2
print(f"R2: {len(r2b)} masks, c2={r2b.get(v2,0):+.6e}")

r3b = defaultdict(float)
for m, c in r2b.items():
    for m3, c3 in fwd_one_full(m):
        r3b[m3] += c * c3
print(f"R3: {len(r3b)} masks, c3={r3b.get(v2,0):+.6e}")

r4b = defaultdict(float)
for m, c in r3b.items():
    for m4, c4 in fwd_one_full(m):
        r4b[m4] += c * c4
print(f"R4: {len(r4b)} masks, c4={r4b.get(v2,0):+.6e}")

r5b = defaultdict(float)
cnt = 0
for m, c in r4b.items():
    cnt += 1
    if cnt % 500 == 0:
        print(f"  R4→R5: {cnt}/{len(r4b)}...")
    for m5, c5 in fwd_one_full(m):
        r5b[m5] += c * c5
print(f"R5: {len(r5b)} masks, c5={r5b.get(v2,0):+.6e}")
