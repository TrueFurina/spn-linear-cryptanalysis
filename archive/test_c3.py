#!/usr/bin/env python3
"""Compute c_3 for test pairs to see when non-zero first appears."""
from computecor_hull_v4 import init_lat, init_trans, fwd_one_full, exact_corr_R2

init_lat()
init_trans()

def exact_corr_R3(u, v):
    total = 0.0
    for m1, c1 in fwd_one_full(u):
        for m2, c2 in fwd_one_full(m1):
            for m3, c3 in fwd_one_full(m2):
                if m3 == v:
                    total += c1 * c2 * c3
    return total

# Test: compute c_1 and c_3 for a few pairs
test_cases = [
    (0x10000000, 0x01000000),
    (0x01000000, 0x10000000),
    (0x00004000, 0x00000400),
    (0x00000010, 0x00000010),
]

for u, v in test_cases:
    print(f"u=0x{u:08X} v=0x{v:08X}:")
    # c_1
    c1 = 0.0
    for m, c in fwd_one_full(u):
        if m == v: c1 = c
    print(f"  c1 = {c1:+.6e}")
    
    # c_2
    c2 = exact_corr_R2(u, v)
    print(f"  c2 = {c2:+.6e}")
    
    # c_3
    c3 = exact_corr_R3(u, v)
    print(f"  c3 = {c3:+.6e}")
    
    print()
