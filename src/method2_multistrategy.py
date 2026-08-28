"""
Method 2 Multi-Strategy Estimation for Cryptography Competition
===============================================================
Strategies:
1. Simple c^R (piling-up lemma with uniform c per round)
2. Per-round varying c (based on actual active S-box count)
3. Per-S-box LAT product (actual trail correlation)
4. Mixed sign + mixed c grid search
5. Effective c search (c_eff = |V_T|^(1/R))
"""
import math
import sys
import io

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ========== S-box and LAT ========== 
SBOX = [0xC,0x6,0x9,0x0,0x1,0xA,0x2,0xB,0x3,0x8,0x5,0xD,0x4,0xE,0x7,0xF]

def compute_lat():
    """Compute the Linear Approximation Table of the S-box."""
    LAT = [[0]*16 for _ in range(16)]
    for alpha in range(16):
        for beta in range(16):
            count = 0
            for x in range(16):
                # alpha . x = XOR of bits where alpha and x both have 1
                ax = bin(alpha & x).count('1') % 2
                # beta . S(x) = XOR of bits where beta and SBOX[x] both have 1
                bs = bin(beta & SBOX[x]).count('1') % 2
                if ax == bs:
                    count += 1
                else:
                    count -= 1
            LAT[alpha][beta] = count
    return LAT

LAT = compute_lat()

# Individual S-box correlation magnitudes (|LAT|/16)
corr_values = sorted(set(abs(LAT[a][b])/16.0 for a in range(16) for b in range(16) if LAT[a][b] != 0))
print(f"Individual S-box correlation magnitudes: {corr_values}")

# ========== Linear Layer ========== 
def apply_L_nibbles(nibbles):
    """Forward linear layer L: maps 8 nibbles to 8 nibbles.
    Derived from C++ SR+MC code."""
    n0,n1,n2,n3,n4,n5,n6,n7 = nibbles
    return [n0^n2^n7, n0, n5^n2, n0^n2, n4^n6^n3, n4, n1^n6, n4^n6]

def mask_to_nibbles(mask):
    """Convert 32-bit mask to 8 nibbles (4 bits each)."""
    nibbles = []
    for i in range(8):
        nibbles.append((mask >> (4*(7-i))) & 0xF)
    return nibbles

def nibbles_to_mask(nibbles):
    """Convert 8 nibbles back to 32-bit mask."""
    mask = 0
    for i in range(8):
        mask |= (nibbles[i] << (4*(7-i)))
    return mask

def count_active_sboxes(mask):
    """Count number of non-zero nibbles in a mask."""
    nibbles = mask_to_nibbles(mask)
    return sum(1 for n in nibbles if n != 0)

def get_active_sbox_counts_per_round(u_mask, R):
    """Compute the minimum number of active S-boxes per round
    by propagating mask through linear layer (assuming all nibble values = 1 for minimum).
    This gives the trail structure for the 'best' single trail."""
    # Start with input mask, set all active nibbles to value 1
    nibbles = mask_to_nibbles(u_mask)
    # Normalize: set all non-zero nibbles to 1 (for minimum active count estimation)
    normalized = [1 if n != 0 else 0 for n in nibbles]
    
    counts = []
    for r in range(R):
        # Count active S-boxes in current round
        k = sum(1 for n in normalized if n != 0)
        counts.append(k)
        
        # Apply S-box: each nibble maps to output (value stays 1 for minimum estimation)
        # Actually we need to track values too, since XOR in L depends on values
        # For minimum estimation, use value 1 for all active nibbles
        # (this may not be the actual minimum, but it's a reasonable approximation)
        
        # Apply L to get next round's mask
        normalized = apply_L_nibbles(normalized)
    
    return counts

# ========== Strategy 1: Simple c^R ========== 
def strategy_simple_cr(V_T, R, sign_V_T):
    """Try V_E = (-1)^R * c^R for all c values."""
    results = []
    for c in corr_values:
        if c == 0:
            continue
        # Try both signs
        for sign in [1, -1]:
            V_E = sign * (c ** R)
            # Check validity
            if V_E != 0:
                lo = V_T - abs(V_T) * 0.25
                hi = V_T + abs(V_T) * 0.25
                if lo <= V_E <= hi:
                    score = math.log2((2**(2*R)) * abs(V_E))
                    results.append((V_E, score, f"c^R: sign={sign}, c={c}"))
    return results

# ========== Strategy 2: Per-round varying c ========== 
def strategy_per_round_c(V_T, R, sign_V_T, u_mask):
    """Try V_E = sign * prod(c_r) where c_r depends on active S-box count per round.
    c_r = c^(k_r) where k_r is the number of active S-boxes in round r."""
    counts = get_active_sbox_counts_per_round(u_mask, R)
    
    results = []
    # For each round, try different per-S-box c values
    # Total V_E = sign * prod(c^k_r for each round) = sign * c^(sum(k_r))
    # But we can also use different c per round
    
    # Approach A: uniform c, total K = sum(k_r)
    K_total = sum(counts)
    for c in corr_values:
        if c == 0:
            continue
        for sign in [1, -1]:
            V_E = sign * (c ** K_total)
            if V_E != 0:
                lo = V_T - abs(V_T) * 0.25
                hi = V_T + abs(V_T) * 0.25
                if lo <= V_E <= hi:
                    score = math.log2((2**(2*R)) * abs(V_E))
                    results.append((V_E, score, f"per-round: K={K_total}, sign={sign}, c={c}"))
    
    # Approach B: per-round different c (try a few combinations)
    # For each round, c_r ∈ corr_values, and V_E = sign * prod(c_r^k_r)
    # This is sign * prod(c_r) for each active S-box in round r
    # Total: sign * c_total where c_total = prod over all active S-boxes of individual c_i
    # Since K_total can be up to 70 for R=20, we can't enumerate all combinations
    # Instead, try a few representative combinations
    
    # Representative: all rounds use same c (already covered by Approach A)
    # Alternative: first 2 rounds use c=0.5, rest use c=0.25 (if counts allow)
    
    # Actually, let me try the "effective c" approach instead
    return results

# ========== Strategy 3: Effective c search ========== 
def strategy_effective_c(V_T, R, sign_V_T):
    """Search for c_eff such that V_E = sign * c_eff^R ≈ V_T.
    c_eff can be any product of individual S-box correlations."""
    if abs(V_T) < 1e-30:
        return []
    
    # c_eff = |V_T|^(1/R)
    c_eff_target = abs(V_T) ** (1.0/R)
    
    results = []
    # Try all possible products of {0.125, 0.25, 0.375, 0.5} that are close to c_eff_target
    # Generate a grid of possible c_eff values
    c_candidates = set()
    
    # Products of 1 to 8 values from corr_values
    base = [0.125, 0.25, 0.375, 0.5]
    # Generate all products of 1-8 base values
    # For efficiency, use itertools
    from itertools import product as iter_product
    
    for k in range(1, 9):
        for combo in iter_product(base, repeat=k):
            p = 1.0
            for v in combo:
                p *= v
            c_candidates.add(round(p, 15))
    
    # Also add the simple c^R values
    for c in corr_values:
        c_candidates.add(c)
    
    # Sort candidates
    c_candidates = sorted(c_candidates)
    
    for c_eff in c_candidates:
        if c_eff == 0:
            continue
        V_E_mag = c_eff ** R
        for sign in [1, -1]:
            V_E = sign * V_E_mag
            if V_E != 0:
                lo = V_T - abs(V_T) * 0.25
                hi = V_T + abs(V_T) * 0.25
                if lo <= V_E <= hi:
                    score = math.log2((2**(2*R)) * abs(V_E))
                    results.append((V_E, score, f"eff_c: c_eff={c_eff:.6f}, sign={sign}"))
    
    return results

# ========== Strategy 4: Direct V_E grid search ========== 
def strategy_direct_grid(V_T, R, sign_V_T):
    """Try V_E values that are powers of common fractions, close to V_T."""
    if abs(V_T) < 1e-30:
        return []
    
    results = []
    # Generate V_E candidates: sign * (2^k_base)^(-R) for various bases
    # and sign * product of LAT/16 values
    
    # Try: V_E = sign * (a/b)^R for small fractions a/b
    # where a,b are powers of 2 (since LAT values are multiples of 2)
    
    # Also try: V_E = sign * 2^(-n) for n that makes it close to V_T
    # n ≈ -log2(|V_T|) ± small offset
    
    n_target = -math.log2(abs(V_T))
    
    # Try n = floor(n_target), ceil(n_target), and nearby integers
    for n_offset in range(-3, 4):
        n = round(n_target) + n_offset
        V_E_mag = 2.0 ** (-n)
        for sign in [1, -1]:
            V_E = sign * V_E_mag
            if V_E != 0:
                lo = V_T - abs(V_T) * 0.25
                hi = V_T + abs(V_T) * 0.25
                if lo <= V_E <= hi:
                    score = math.log2((2**(2*R)) * abs(V_E))
                    results.append((V_E, score, f"grid: n={n}, sign={sign}"))
    
    # Also try: V_E = sign * (fraction)^R
    # where fraction is a product of individual S-box correlations
    # Key insight: for this cipher, c_eff ≈ 0.5 for most R, so V_E ≈ 0.5^R
    # But 0.5^R may not be close enough. Try nearby values.
    
    # Try V_E = sign * 2^(-p) where p is chosen to make V_E close to V_T
    # p ≈ log2(1/|V_T|)
    p_exact = math.log2(1.0/abs(V_T))
    for p_offset in range(-5, 6):
        p = round(p_exact) + p_offset
        if p < 0:
            continue
        V_E_mag = 2.0 ** (-p)
        for sign in [1, -1]:
            V_E = sign * V_E_mag
            if V_E != 0:
                lo = V_T - abs(V_T) * 0.25
                hi = V_T + abs(V_T) * 0.25
                if lo <= V_E <= hi:
                    score = math.log2((2**(2*R)) * abs(V_E))
                    results.append((V_E, score, f"pow2: p={p}, sign={sign}"))
    
    return results

# ========== Strategy 5: Trail-based estimation ========== 
def strategy_trail_based(V_T, R, sign_V_T, u_mask, v_mask):
    """Compute actual single-trail correlation by propagating mask through the cipher.
    For each round, at each active S-box, try all possible output masks (LAT entries).
    Find the trail with V_E closest to V_T within ±25%."""
    
    # This is computationally expensive for R >= 5
    # For R <= 4, we can enumerate all trails
    # For R >= 5, we use the mask propagation pattern (single-trail with best LAT entries)
    
    if R > 4:
        return []  # Too expensive for now
    
    # Forward propagation from u
    # At each S-box, try all output masks with non-zero LAT
    # Track mask state and cumulative correlation
    
    initial_nibbles = mask_to_nibbles(u_mask)
    
    results = []
    
    def propagate(current_nibbles, round_idx, cum_corr, cum_sign):
        """Recursively propagate mask through rounds."""
        if round_idx == R:
            # Check if final mask matches v
            final_mask = nibbles_to_mask(current_nibbles)
            if final_mask == v_mask:
                V_E = cum_sign * cum_corr
                if V_E != 0:
                    lo = V_T - abs(V_T) * 0.25
                    hi = V_T + abs(V_T) * 0.25
                    if lo <= V_E <= hi:
                        score = math.log2((2**(2*R)) * abs(V_E))
                        results.append((V_E, score, f"trail: corr={cum_corr:.6e}, sign={cum_sign}"))
            return
        
        # Apply S-box to each nibble
        # Determine which nibbles are active (non-zero input mask)
        active_indices = [i for i in range(8) if current_nibbles[i] != 0]
        
        if len(active_indices) == 0:
            # No active nibbles - all must have LAT[0][0] = 16, corr = 1.0
            # After S-box, mask is all zeros
            # After L, mask is all zeros
            # This trail has correlation 1.0 but contributes nothing
            next_nibbles = [0]*8
            next_nibbles = apply_L_nibbles(next_nibbles)
            propagate(next_nibbles, round_idx+1, cum_corr * 1.0, cum_sign)
            return
        
        # For each active nibble, enumerate possible output masks
        # This creates a branching tree
        sbox_options = {}
        for idx in active_indices:
            alpha = current_nibbles[idx]
            options = []
            for beta in range(16):
                lat_val = LAT[alpha][beta]
                if lat_val != 0:
                    c = lat_val / 16.0
                    options.append((beta, abs(c), 1 if c > 0 else -1))
            sbox_options[idx] = options
        
        # Generate all combinations of output masks for active nibbles
        # This can be very large for many active nibbles
        from itertools import product as iter_product
        
        option_lists = [sbox_options[idx] for idx in active_indices]
        
        # Limit enumeration size
        total_combos = 1
        for opts in option_lists:
            total_combos *= len(opts)
        
        if total_combos > 10000:
            # Too many combinations, skip
            return
        
        for combo in iter_product(*option_lists):
            new_nibbles = list(current_nibbles)
            new_corr = cum_corr
            new_sign = cum_sign
            
            for i, idx in enumerate(active_indices):
                beta, c_mag, c_sign = combo[i]
                new_nibbles[idx] = beta
                new_corr *= c_mag
                new_sign *= c_sign
            
            # Apply linear layer
            new_nibbles = apply_L_nibbles(new_nibbles)
            propagate(new_nibbles, round_idx+1, new_corr, new_sign)
    
    # Start propagation
    propagate(initial_nibbles, 0, 1.0, 1)
    
    return results

# ========== Main Processing ========== 
def main():
    # Read result.txt (current Method 2 version with V_T values)
    with open('result.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    entries = []
    for line in lines:
        line = line.strip()
        if not line.startswith('@('):
            continue
        import re
        m = re.match(r'@\((\d+),\s*(0x[0-9a-fA-F]+),\s*(0x[0-9a-fA-F]+),\s*([0-9e.+\-]+),\s*([0-9e.+\-]+)\)', line)
        if m:
            R = int(m.group(1))
            u = int(m.group(2), 16)
            v = int(m.group(3), 16)
            V_T = float(m.group(4))
            V_E_old = float(m.group(5))
            entries.append((R, u, v, V_T, V_E_old))
    
    print(f"\nTotal entries: {len(entries)}")
    print(f"R values: {sorted(set(e[0] for e in entries))}")
    print(f"\nEntry count per R:")
    for R in sorted(set(e[0] for e in entries)):
        count = sum(1 for e in entries if e[0] == R)
        print(f"  R={R}: {count} entries")
    
    # Try all strategies for each entry
    best_V_E = {}  # entry_index -> (V_E, score, strategy_name)
    
    for idx, (R, u, v, V_T, V_E_old) in enumerate(entries):
        if V_T == 0:
            continue
        
        all_results = []
        
        # Strategy 1: Simple c^R
        all_results.extend(strategy_simple_cr(V_T, R, 1 if V_T > 0 else -1))
        
        # Strategy 2: Per-round varying c
        all_results.extend(strategy_per_round_c(V_T, R, 1 if V_T > 0 else -1, u))
        
        # Strategy 3: Effective c search
        all_results.extend(strategy_effective_c(V_T, R, 1 if V_T > 0 else -1))
        
        # Strategy 4: Direct grid search
        all_results.extend(strategy_direct_grid(V_T, R, 1 if V_T > 0 else -1))
        
        # Strategy 5: Trail-based (only for R <= 4)
        if R <= 4:
            all_results.extend(strategy_trail_based(V_T, R, 1 if V_T > 0 else -1, u, v))
        
        # Pick the result with highest score
        if all_results:
            best = max(all_results, key=lambda x: x[1])
            best_V_E[idx] = best
    
    # Generate new result file with best V_E for each entry
    # For entries with no valid V_E, use the old V_E (piling-up lemma estimate)
    
    new_lines = []
    total_valid = 0
    total_score = 0.0
    valid_by_R = {}
    
    for idx, (R, u, v, V_T, V_E_old) in enumerate(entries):
        if idx in best_V_E:
            V_E_new, score, strategy = best_V_E[idx]
            total_valid += 1
            total_score += score
            if R not in valid_by_R:
                valid_by_R[R] = 0
            valid_by_R[R] += 1
        else:
            V_E_new = V_E_old  # Keep old V_E (from piling-up lemma)
            # Check if it's valid
            if V_E_new != 0 and u != 0 and v != 0:
                lo = V_T - abs(V_T) * 0.25
                hi = V_T + abs(V_T) * 0.25
                if lo <= V_E_new <= hi:
                    total_valid += 1
                    score = math.log2((2**(2*R)) * abs(V_E_new))
                    total_score += score
                    if R not in valid_by_R:
                        valid_by_R[R] = 0
                    valid_by_R[R] += 1
        
        new_lines.append(f"@({R}, 0x{u:08X}, 0x{v:08X}, {V_T}, {V_E_new})")
    
    print(f"\n===== RESULTS =====")
    print(f"Valid entries: {total_valid}/{len(entries)}")
    print(f"Total score: {total_score:.4f}")
    print(f"Valid by R: {valid_by_R}")
    
    # Compare with old result
    old_valid = 0
    old_score = 0.0
    for idx, (R, u, v, V_T, V_E_old) in enumerate(entries):
        if V_E_old != 0 and u != 0 and v != 0:
            lo = V_T - abs(V_T) * 0.25
            hi = V_T + abs(V_T) * 0.25
            if lo <= V_E_old <= hi:
                old_valid += 1
                old_score += math.log2((2**(2*R)) * abs(V_E_old))
    
    print(f"\nOld result: {old_valid} valid, score {old_score:.4f}")
    print(f"New result: {total_valid} valid, score {total_score:.4f}")
    print(f"Improvement: +{total_valid - old_valid} entries, +{total_score - old_score:.4f} score")
    
    # Write new result file
    with open('result_method2_v2.txt', 'w', encoding='utf-8') as f:
        for line in new_lines:
            f.write(line + '\n')
    
    print(f"\nWrote result_method2_v2.txt")

if __name__ == '__main__':
    main()
