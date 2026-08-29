"""
Method 1 (Exact) Verification - Vectorized Cipher Computation
==============================================================
Computes V_T exactly for all entries using numpy vectorization.
Processes plaintexts in batches to manage memory.
"""
import os
import numpy as np
import math
import re
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Auto-locate results/ so this script runs from any cwd (repo root or results/)
_HERE = os.path.dirname(os.path.abspath(__file__))
_RS = os.path.join(os.path.dirname(_HERE), 'results')
if os.path.isdir(_RS) and os.path.exists(os.path.join(_RS, 'result.txt')):
    os.chdir(_RS)

# ========== Cipher Definition ========== 
SBOX = [0xC,0x6,0x9,0x0,0x1,0xA,0x2,0xB,0x3,0x8,0x5,0xD,0x4,0xE,0x7,0xF]
SBOX_NP = np.array(SBOX, dtype=np.uint8)

def encrypt_batch(states, R):
    """Encrypt a batch of 32-bit states through R rounds.
    states: numpy array of uint32 values
    Returns: encrypted states (uint32)
    """
    for r in range(R):
        # Step 1: S-box substitution
        # Extract 8 nibbles from each 32-bit state
        nibbles = np.zeros((len(states), 8), dtype=np.uint8)
        for i in range(8):
            nibbles[:, i] = (states >> (4 * (7 - i))) & 0xF
        
        # Apply S-box to each nibble
        for i in range(8):
            nibbles[:, i] = SBOX_NP[nibbles[:, i]]
        
        # Reconstruct 32-bit state from nibbles
        states = np.zeros(len(states), dtype=np.uint32)
        for i in range(8):
            states |= nibbles[:, i].astype(np.uint32) << (4 * (7 - i))
        
        # Step 2: ShiftRows (SR)
        # SR rearranges nibbles: [0,5,2,7,4,1,6,3] -> permute
        # Extract nibbles again
        nibbles = np.zeros((len(states), 8), dtype=np.uint8)
        for i in range(8):
            nibbles[:, i] = (states >> (4 * (7 - i))) & 0xF
        
        # SR permutation: position i gets nibble from SR_table[i]
        # SR: [0->0, 1->5, 2->2, 3->7, 4->4, 5->1, 6->6, 7->3]
        # i.e., new[0]=old[0], new[1]=old[5], new[2]=old[2], new[3]=old[7],
        #       new[4]=old[4], new[5]=old[1], new[6]=old[6], new[7]=old[3]
        sr_nibbles = np.zeros_like(nibbles)
        sr_nibbles[:, 0] = nibbles[:, 0]
        sr_nibbles[:, 1] = nibbles[:, 5]
        sr_nibbles[:, 2] = nibbles[:, 2]
        sr_nibbles[:, 3] = nibbles[:, 7]
        sr_nibbles[:, 4] = nibbles[:, 4]
        sr_nibbles[:, 5] = nibbles[:, 1]
        sr_nibbles[:, 6] = nibbles[:, 6]
        sr_nibbles[:, 7] = nibbles[:, 3]
        
        # Reconstruct
        states = np.zeros(len(states), dtype=np.uint32)
        for i in range(8):
            states |= sr_nibbles[:, i].astype(np.uint32) << (4 * (7 - i))
        
        # Step 3: MixColumns (MC)
        # MC operates on each column (pair of nibbles) independently
        # For our 4-bit cipher: MC = XOR operations
        # From C++ code:
        # state[0]=t0^t2^t3; state[1]=t0; state[2]=t1^t2; state[3]=t0^t2;
        # state[4]=t4^t6^t7; state[5]=t4; state[6]=t5^t6; state[7]=t4^t6;
        # where t0..t7 are SR output nibbles
        
        nibbles = np.zeros((len(states), 8), dtype=np.uint8)
        for i in range(8):
            nibbles[:, i] = (states >> (4 * (7 - i))) & 0xF
        
        mc_nibbles = np.zeros_like(nibbles)
        mc_nibbles[:, 0] = nibbles[:, 0] ^ nibbles[:, 2] ^ nibbles[:, 3]
        mc_nibbles[:, 1] = nibbles[:, 0]
        mc_nibbles[:, 2] = nibbles[:, 5] ^ nibbles[:, 2]
        mc_nibbles[:, 3] = nibbles[:, 0] ^ nibbles[:, 2]
        mc_nibbles[:, 4] = nibbles[:, 4] ^ nibbles[:, 6] ^ nibbles[:, 3]
        mc_nibbles[:, 5] = nibbles[:, 4]
        mc_nibbles[:, 6] = nibbles[:, 1] ^ nibbles[:, 6]
        mc_nibbles[:, 7] = nibbles[:, 4] ^ nibbles[:, 6]
        
        # Reconstruct
        states = np.zeros(len(states), dtype=np.uint32)
        for i in range(8):
            states |= mc_nibbles[:, i].astype(np.uint32) << (4 * (7 - i))
    
    return states

def dot_product(mask, states):
    """Compute dot product (parity of XOR) for a batch of states.
    dot(mask, state) = XOR of bits where mask and state both have 1.
    Returns: numpy array of 0/1 values (parity)."""
    # For each state, compute parity of (mask & state)
    and_result = mask & states
    # Count bits and compute parity
    # Use lookup table for bit count parity of 32-bit numbers
    parity = np.zeros(len(states), dtype=np.int8)
    temp = and_result.copy()
    for shift in [16, 8, 4, 2, 1]:
        temp ^= temp >> shift
    parity = temp & 1
    return parity

def compute_correlation_exact(u, v, R, batch_size=2**20):
    """Compute exact correlation V_T for (u, v, R) using exhaustive search.
    Processes plaintexts in batches of batch_size."""
    N = 2**32  # Total plaintexts
    total_sum = 0.0
    
    num_batches = N // batch_size
    if N % batch_size != 0:
        num_batches += 1
    
    for batch_idx in range(num_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, N)
        
        # Generate plaintext batch
        plaintexts = np.arange(start, end, dtype=np.uint32)
        
        # Encrypt
        ciphertexts = encrypt_batch(plaintexts, R)
        
        # Compute dot products
        u_dot = dot_product(u, plaintexts)
        v_dot = dot_product(v, ciphertexts)
        
        # Accumulate: (-1)^(u_dot XOR v_dot) = 1 if u_dot==v_dot, -1 if different
        signs = np.where(u_dot == v_dot, 1, -1)
        total_sum += np.sum(signs)
    
    V_T = total_sum / N
    return V_T

# ========== Main ========== 
def main():
    # Read entries from result.txt
    with open('result.txt', 'r', encoding='utf-8') as f:
        content = f.read()
    
    pattern = r'@\((\d+),\s*(0x[0-9a-fA-F]+),\s*(0x[0-9a-fA-F]+),\s*([0-9e.+\-]+),\s*([0-9e.+\-]+)\)'
    matches = re.findall(pattern, content)
    
    entries = []
    for m in matches:
        R = int(m[0])
        u = int(m[1], 16)
        v = int(m[2], 16)
        V_T_claimed = float(m[3])
        V_E = float(m[4])
        entries.append((R, u, v, V_T_claimed, V_E))
    
    # Get unique R values and sort
    R_values = sorted(set(e[0] for e in entries))
    print(f"R values to verify: {R_values}")
    print(f"Total entries: {len(entries)}")
    
    # Verify a few entries first (small R for speed)
    # Start with R=1 (should be very fast)
    verified = {}
    errors = []
    
    batch_size = 2**20  # 1M plaintexts per batch
    
    for R in R_values:
        R_entries = [e for e in entries if e[0] == R]
        print(f"\n--- Verifying R={R} ({len(R_entries)} entries) ---")
        
        # Compute all (u, v) correlations for this R simultaneously
        # Precompute encryption for all plaintexts
        start_time = time.time()
        
        # We need to encrypt all 2^32 plaintexts through R rounds
        # Then for each (u, v), compute the correlation
        
        # Process in batches
        correlations = {}
        
        for batch_idx in range(2**32 // batch_size):
            start = batch_idx * batch_size
            end = start + batch_size
            
            # Generate plaintexts
            plaintexts = np.arange(start, end, dtype=np.uint32)
            
            # Encrypt
            ciphertexts = encrypt_batch(plaintexts, R)
            
            # Compute correlation for each (u, v)
            for e_idx, (R_e, u, v, V_T_claimed, V_E) in enumerate(R_entries):
                if (u, v) in correlations:
                    accum = correlations[(u, v)]
                else:
                    accum = 0.0
                
                u_dot = dot_product(u, plaintexts)
                v_dot = dot_product(v, ciphertexts)
                signs = np.where(u_dot == v_dot, 1, -1)
                accum += np.sum(signs)
                correlations[(u, v)] = accum
        
        # Finalize correlations
        for e_idx, (R_e, u, v, V_T_claimed, V_E) in enumerate(R_entries):
            V_T_computed = correlations[(u, v)] / 2**32
            verified[(u, v, R)] = V_T_computed
            
            error = abs(V_T_computed - V_T_claimed) / max(abs(V_T_claimed), 1e-10)
            status = "OK" if error < 0.01 else "ERROR"
            if status == "ERROR":
                errors.append((R, u, v, V_T_claimed, V_T_computed, error))
            
            print(f"  @(R={R}, u=0x{u:08X}, v=0x{v:08X}): claimed={V_T_claimed:.6e}, computed={V_T_computed:.6e}, err={error:.4e} [{status}]")
        
        elapsed = time.time() - start_time
        print(f"  R={R} verification took {elapsed:.1f}s")
        
        # Save progress
        with open('method1_verify_results.txt', 'w', encoding='utf-8') as f:
            for key, val in verified.items():
                u, v, R_k = key
                f.write(f"@({R_k}, 0x{u:08X}, 0x{v:08X}, V_T_computed={val:.10e})\n")
        
        # For R>=10, this becomes very slow. Check if we should continue.
        if R >= 10 and elapsed > 120:
            remaining_R = [r for r in R_values if r > R]
            estimated_time = sum(elapsed * (r/R) for r in remaining_R)
            print(f"\n  WARNING: R={R} took {elapsed:.1f}s. Estimated time for remaining R values: {estimated_time/60:.1f} minutes")
            print(f"  Continuing verification...")
        
        # For very large R, we might need to reduce batch size or skip
        if R >= 15 and elapsed > 300:
            print(f"\n  R={R} too slow ({elapsed:.1f}s). Skipping remaining high-R entries.")
            break
    
    # Summary
    print(f"\n===== VERIFICATION SUMMARY =====")
    print(f"Verified entries: {len(verified)}")
    print(f"Errors found: {len(errors)}")
    
    if errors:
        print("\nError details:")
        for R, u, v, claimed, computed, err in errors:
            print(f"  R={R}, u=0x{u:08X}, v=0x{v:08X}: claimed={claimed:.6e}, computed={computed:.6e}, error={err:.4e}")
    
    # Write full verification results
    with open('method1_verify_results.txt', 'w', encoding='utf-8') as f:
        f.write(f"Verification Summary\n")
        f.write(f"Verified: {len(verified)}, Errors: {len(errors)}\n\n")
        for key, val in verified.items():
            u, v, R_k = key
            # Find claimed V_T
            claimed = None
            for e in entries:
                if e[0] == R_k and e[1] == u and e[2] == v:
                    claimed = e[3]
                    break
            f.write(f"@({R_k}, 0x{u:08X}, 0x{v:08X}, claimed={claimed}, computed={val:.10e})\n")

if __name__ == '__main__':
    main()
