#include <iostream>
#include <iomanip>
#include <vector>
#include <cstdint>
#include <string>
#include <cmath>

using namespace std;

typedef unsigned char Cell;
typedef unsigned int uint;

Cell Sbox[16] = {0xC, 0x6, 0x9, 0x0, 0x1, 0xA, 0x2, 0xB, 0x3, 0x8, 0x5, 0xD, 0x4, 0xE, 0x7, 0xF};

inline void round_op(Cell* state) {
    // S-box
    #pragma unroll
    for (int i = 0; i < 8; ++i) 
        state[i] = Sbox[state[i]];

    // SR
    Cell t0 = state[0], t1 = state[5], t2 = state[2], t3 = state[7];
    Cell t4 = state[4], t5 = state[1], t6 = state[6], t7 = state[3];
    
    // MC
    state[0] = t0 ^ t2 ^ t3;
    state[1] = t0;
    state[2] = t1 ^ t2;
    state[3] = t0 ^ t2;
    
    state[4] = t4 ^ t6 ^ t7;
    state[5] = t4;
    state[6] = t5 ^ t6;
    state[7] = t4 ^ t6;
}

inline uint perm( uint x, int R ) 
{
    Cell state[8]; 
    state[0] = x >> 28 & 0xF;
    state[1] = x >> 24 & 0xF;
    state[2] = x >> 20 & 0xF;
    state[3] = x >> 16 & 0xF;
    state[4] = x >> 12 & 0xF;
    state[5] = x >> 8 & 0xF;
    state[6] = x >> 4 & 0xF;
    state[7] = x >> 0 & 0xF;
    
    for(int r=0; r<R; ++r) 
        round_op(state);

    uint res = 0;
    res |= ((uint)state[7]);
    res |= ((uint)state[6]) << 4;
    res |= ((uint)state[5]) << 8;
    res |= ((uint)state[4]) << 12;
    res |= ((uint)state[3]) << 16;
    res |= ((uint)state[2]) << 20;
    res |= ((uint)state[1]) << 24;
    res |= ((uint)state[0]) << 28;

    return res;
}

inline int dot(uint u, uint y) 
{
    uint z = u & y;

    z ^= z >> 1;
    z ^= z >> 2;
    z ^= z >> 4;
    z ^= z >> 8;
    z ^= z >> 16;

    return z & 1;
}

// 可用于一次性计算给定v，所有u的相关性，时间复杂度 O(32 x 2^32)，空间复杂度 O(2^32)
void fwht(vector<int>& a) 
{
    size_t n = a.size();
    for (size_t len = 1; len < n; len <<= 1) {
        for (size_t i = 0; i < n; i += 2 * len) {
            for (size_t j = 0; j < len; ++j) {
                int u = a[i + j];
                int v = a[i + j + len];
                a[i + j] = u + v;
                a[i + j + len] = u - v;
            }
        }
    }

    for ( int i = 0; i < n; ++i )
        a[i] /= n;
}

double computeCor_uv( uint u, uint v, int R ) {
    long long count = 0;
    const uint64_t total = 1ULL << 32;
    
    for ( uint64_t x = 0; x < total; ++x ) {
        uint y = perm( (uint)x, R );
        if ( dot( u, (uint)x ) == dot( v, y ) )
            count++;
        else
            count--;
    }

    return (double)count / (double)total;
}

int main() 
{
    int R;
    string u_str, v_str;
    uint u, v;

    cout << "--- Linear Correlation Calculator ---" << endl;

    // 1. Input R
    cout << "Enter number of rounds (R): ";
    if (!(cin >> R)) {
        cerr << "Error: Invalid input for R." << endl;
        return 1;
    }

    // 2. Input u
    cout << "Enter  input mask u (hex, e.g., 0x000ee0f0): ";
    cin >> u_str;
    try {
        u = stoul(u_str, nullptr, 16);
    } catch (...) {
        cerr << "Error: Invalid hex format for u." << endl;
        return 1;
    }

    // 3. Input v
    cout << "Enter output mask v (hex, e.g., 0x08088880): ";
    cin >> v_str;
    try {
        v = stoul(v_str, nullptr, 16);
    } catch (...) {
        cerr << "Error: Invalid hex format for v." << endl;
        return 1;
    }

    cout << endl;
    cout << "Parameters:" << endl;
    cout << "  R = " << R << endl;
    cout << "  u = 0x" << hex << setw(8) << setfill( '0' ) << u << dec << endl;
    cout << "  v = 0x" << hex << setw(8) << setfill( '0' ) << v << dec << endl;
    cout << endl;

    // Calculate
    double correlation = computeCor_uv(u, v, R);

    // Output Result
    cout << endl;
    cout << "Result:" << endl;
    cout << "  Correlation = " << setprecision(10) << '\t' << correlation << endl;
    cout << "  -log|Correlation| = " << setprecision(10) << '\t' << log2( abs( correlation ) ) << endl;

    
    return 0;
}





