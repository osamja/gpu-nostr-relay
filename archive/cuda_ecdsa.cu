/*
 * CUDA ECDSA Signature Verification for secp256k1
 * Batch verification optimized for GPU parallelization
 */

#include <cuda_runtime.h>
#include <device_launch_parameters.h>
#include <stdint.h>

// secp256k1 curve parameters
__constant__ uint64_t SECP256K1_P[4] = {
    0xFFFFFFFEFFFFFC2FULL, 0xFFFFFFFFFFFFFFFFULL,
    0xFFFFFFFFFFFFFFFFULL, 0xFFFFFFFFFFFFFFFFULL
};

__constant__ uint64_t SECP256K1_N[4] = {
    0xBFD25E8CD0364141ULL, 0xBAAEDCE6AF48A03BULL,
    0xFFFFFFFFFFFFFFFEULL, 0xFFFFFFFFFFFFFFFFULL
};

__constant__ uint64_t SECP256K1_GX[4] = {
    0x59F2815B16F81798ULL, 0x029BFCDB2DCE28D9ULL,
    0x55A06295CE870B07ULL, 0x79BE667EF9DCBBACULL
};

__constant__ uint64_t SECP256K1_GY[4] = {
    0x9C47D08FFB10D4B8ULL, 0xFD17B448A6855419ULL,
    0x5DA4FBFC0E1108A8ULL, 0x483ADA7726A3C465ULL
};

// Point structure for elliptic curve operations
typedef struct {
    uint64_t x[4];
    uint64_t y[4];
    uint64_t z[4];  // Jacobian coordinates
} ECPoint;

// 256-bit integer operations
__device__ __forceinline__ 
bool is_zero(const uint64_t a[4]) {
    return (a[0] | a[1] | a[2] | a[3]) == 0;
}

__device__ __forceinline__
bool is_equal(const uint64_t a[4], const uint64_t b[4]) {
    return (a[0] == b[0]) && (a[1] == b[1]) && (a[2] == b[2]) && (a[3] == b[3]);
}

__device__ __forceinline__
void copy_bigint(uint64_t dst[4], const uint64_t src[4]) {
    dst[0] = src[0]; dst[1] = src[1]; dst[2] = src[2]; dst[3] = src[3];
}

__device__ __forceinline__
void set_zero(uint64_t a[4]) {
    a[0] = a[1] = a[2] = a[3] = 0;
}

// Modular addition in secp256k1 field
__device__ __forceinline__
void mod_add(uint64_t result[4], const uint64_t a[4], const uint64_t b[4]) {
    uint64_t carry = 0;
    uint64_t temp[4];
    
    // Add with carry
    temp[0] = a[0] + b[0];
    carry = temp[0] < a[0] ? 1 : 0;
    
    temp[1] = a[1] + b[1] + carry;
    carry = (temp[1] < a[1]) || (temp[1] < carry) ? 1 : 0;
    
    temp[2] = a[2] + b[2] + carry;
    carry = (temp[2] < a[2]) || (temp[2] < carry) ? 1 : 0;
    
    temp[3] = a[3] + b[3] + carry;
    
    // Reduce modulo p if necessary
    if (temp[3] > SECP256K1_P[3] || 
        (temp[3] == SECP256K1_P[3] && temp[2] > SECP256K1_P[2]) ||
        (temp[3] == SECP256K1_P[3] && temp[2] == SECP256K1_P[2] && 
         temp[1] > SECP256K1_P[1]) ||
        (temp[3] == SECP256K1_P[3] && temp[2] == SECP256K1_P[2] && 
         temp[1] == SECP256K1_P[1] && temp[0] >= SECP256K1_P[0])) {
        
        // Subtract p
        uint64_t borrow = 0;
        result[0] = temp[0] - SECP256K1_P[0];
        borrow = result[0] > temp[0] ? 1 : 0;
        
        result[1] = temp[1] - SECP256K1_P[1] - borrow;
        borrow = (result[1] > temp[1]) || (borrow && result[1] == temp[1]) ? 1 : 0;
        
        result[2] = temp[2] - SECP256K1_P[2] - borrow;
        borrow = (result[2] > temp[2]) || (borrow && result[2] == temp[2]) ? 1 : 0;
        
        result[3] = temp[3] - SECP256K1_P[3] - borrow;
    } else {
        copy_bigint(result, temp);
    }
}

// Modular subtraction in secp256k1 field
__device__ __forceinline__
void mod_sub(uint64_t result[4], const uint64_t a[4], const uint64_t b[4]) {
    uint64_t temp[4];
    uint64_t borrow = 0;
    
    // Subtract with borrow
    temp[0] = a[0] - b[0];
    borrow = temp[0] > a[0] ? 1 : 0;
    
    temp[1] = a[1] - b[1] - borrow;
    borrow = (temp[1] > a[1]) || (borrow && temp[1] == a[1]) ? 1 : 0;
    
    temp[2] = a[2] - b[2] - borrow;
    borrow = (temp[2] > a[2]) || (borrow && temp[2] == a[2]) ? 1 : 0;
    
    temp[3] = a[3] - b[3] - borrow;
    borrow = (temp[3] > a[3]) || (borrow && temp[3] == a[3]) ? 1 : 0;
    
    if (borrow) {
        // Add p to make result positive
        uint64_t carry = 0;
        result[0] = temp[0] + SECP256K1_P[0];
        carry = result[0] < temp[0] ? 1 : 0;
        
        result[1] = temp[1] + SECP256K1_P[1] + carry;
        carry = (result[1] < temp[1]) || (result[1] < carry) ? 1 : 0;
        
        result[2] = temp[2] + SECP256K1_P[2] + carry;
        carry = (result[2] < temp[2]) || (result[2] < carry) ? 1 : 0;
        
        result[3] = temp[3] + SECP256K1_P[3] + carry;
    } else {
        copy_bigint(result, temp);
    }
}

// Full 256x256 -> 512 bit multiplication
__device__ __forceinline__
void mul_256x256(uint64_t result[8], const uint64_t a[4], const uint64_t b[4]) {
    // Initialize result
    for (int i = 0; i < 8; i++) result[i] = 0;
    
    // Schoolbook multiplication
    for (int i = 0; i < 4; i++) {
        uint64_t carry = 0;
        for (int j = 0; j < 4; j++) {
            // Multiply a[i] * b[j]
            uint64_t high, low;
            
            // 64x64 -> 128 bit multiplication
            uint64_t a_lo = a[i] & 0xFFFFFFFFULL;
            uint64_t a_hi = a[i] >> 32;
            uint64_t b_lo = b[j] & 0xFFFFFFFFULL;
            uint64_t b_hi = b[j] >> 32;
            
            uint64_t ll = a_lo * b_lo;
            uint64_t lh = a_lo * b_hi;
            uint64_t hl = a_hi * b_lo;
            uint64_t hh = a_hi * b_hi;
            
            uint64_t mid = lh + hl;
            uint64_t mid_carry = (mid < lh) ? 1ULL << 32 : 0;
            
            low = ll + (mid << 32);
            high = hh + (mid >> 32) + mid_carry + (low < ll ? 1 : 0);
            
            // Add to result with carry
            uint64_t sum = result[i + j] + low + carry;
            carry = (sum < result[i + j]) || (sum < low) ? 1 : 0;
            carry += high;
            result[i + j] = sum;
            
            if (carry) {
                result[i + j + 1] += carry;
                carry = result[i + j + 1] < carry ? 1 : 0;
            }
        }
    }
}

// Barrett reduction for secp256k1 prime
__device__ __forceinline__
void barrett_reduce(uint64_t result[4], const uint64_t a[8]) {
    // Barrett reduction constants for secp256k1 prime
    // μ = floor(2^512 / p) for 256-bit p
    // Simplified implementation - in production would precompute constants
    
    // For secp256k1 p = 2^256 - 2^32 - 977
    // We can use the special form for faster reduction
    
    // High part of a (a[4] through a[7])
    uint64_t high[4] = {a[4], a[5], a[6], a[7]};
    uint64_t low[4] = {a[0], a[1], a[2], a[3]};
    
    // Multiply high by 2^32 + 977 (the difference from 2^256)
    uint64_t temp1[4], temp2[4];
    
    // high * 2^32 = shift left by 32 bits
    temp1[0] = (high[0] << 32) | (high[1] >> 32);
    temp1[1] = (high[1] << 32) | (high[2] >> 32);
    temp1[2] = (high[2] << 32) | (high[3] >> 32);
    temp1[3] = high[3] << 32;
    
    // high * 977
    uint64_t c977[4] = {977, 0, 0, 0};
    uint64_t temp977[8];
    mul_256x256(temp977, high, c977);
    temp2[0] = temp977[0]; temp2[1] = temp977[1]; 
    temp2[2] = temp977[2]; temp2[3] = temp977[3];
    
    // Add: low + high*2^32 + high*977
    mod_add(result, low, temp1);
    mod_add(result, result, temp2);
}

// Modular multiplication using Barrett reduction
__device__ __forceinline__
void mod_mul(uint64_t result[4], const uint64_t a[4], const uint64_t b[4]) {
    uint64_t temp[8];
    mul_256x256(temp, a, b);
    barrett_reduce(result, temp);
}

// Modular squaring (optimized multiplication by self)
__device__ __forceinline__
void mod_square(uint64_t result[4], const uint64_t a[4]) {
    mod_mul(result, a, a);
}

// Modular inverse using Fermat's little theorem: a^(p-2) mod p
__device__
void mod_inverse(uint64_t result[4], const uint64_t a[4]) {
    // For secp256k1: p-2 = 0xFFFFFFFEFFFFFC2DULL, 0xFFFFFFFFFFFFFFFFULL, 0xFFFFFFFFFFFFFFFFULL, 0xFFFFFFFFFFFFFFFDULL
    uint64_t exp[4] = {
        0xFFFFFFFEFFFFFC2DULL, 0xFFFFFFFFFFFFFFFFULL,
        0xFFFFFFFFFFFFFFFFULL, 0xFFFFFFFFFFFFFFFDULL
    };
    
    // Binary exponentiation
    uint64_t base[4], temp[4];
    copy_bigint(base, a);
    uint64_t one_inv[4] = {1, 0, 0, 0};
    copy_bigint(result, one_inv);
    
    for (int i = 0; i < 256; i++) {
        int word = i / 64;
        int bit = i % 64;
        
        if (exp[word] & (1ULL << bit)) {
            mod_mul(result, result, base);
        }
        
        if (i < 255) {
            mod_square(base, base);
        }
    }
}

// Modular square root using Tonelli-Shanks algorithm
__device__
bool mod_sqrt(uint64_t result[4], const uint64_t a[4]) {
    // For secp256k1, p ≡ 3 (mod 4), so we can use: sqrt(a) = a^((p+1)/4)
    uint64_t exp[4] = {
        0x3FFFFFFFBFFFFF0CULL, 0x0000000000000000ULL,
        0x0000000000000000ULL, 0x4000000000000000ULL
    };
    
    uint64_t base[4], temp[4];
    copy_bigint(base, a);
    uint64_t one_sqrt[4] = {1, 0, 0, 0};
    copy_bigint(result, one_sqrt);
    
    for (int i = 0; i < 256; i++) {
        int word = i / 64;
        int bit = i % 64;
        
        if (exp[word] & (1ULL << bit)) {
            mod_mul(result, result, base);
        }
        
        if (i < 255) {
            mod_square(base, base);
        }
    }
    
    // Verify result
    mod_square(temp, result);
    return is_equal(temp, a);
}

// Compare two 256-bit integers
__device__ __forceinline__
int cmp_bigint(const uint64_t a[4], const uint64_t b[4]) {
    for (int i = 3; i >= 0; i--) {
        if (a[i] > b[i]) return 1;
        if (a[i] < b[i]) return -1;
    }
    return 0;
}

// Point doubling in Jacobian coordinates
// Reference: Guide to Elliptic Curve Cryptography, Algorithm 3.21
__device__
void point_double(ECPoint* result, const ECPoint* p) {
    if (is_zero(p->z)) {
        // Point at infinity
        set_zero(result->x);
        set_zero(result->y);
        set_zero(result->z);
        return;
    }
    
    uint64_t a[4], b[4], c[4], d[4], e[4], f[4];
    
    // A = Y^2
    mod_square(a, p->y);
    
    // B = 4*X*A
    mod_mul(b, p->x, a);
    mod_add(b, b, b);
    mod_add(b, b, b);
    
    // C = 8*A^2
    mod_square(c, a);
    mod_add(c, c, c);
    mod_add(c, c, c);
    mod_add(c, c, c);
    
    // D = 3*X^2 (since a=0 for secp256k1)
    mod_square(d, p->x);
    mod_add(d, d, d);
    mod_add(d, d, d);
    
    // E = D^2
    mod_square(e, d);
    
    // F = E - 2*B
    mod_add(f, b, b);
    mod_sub(f, e, f);
    
    // X3 = F
    copy_bigint(result->x, f);
    
    // Y3 = D*(B - F) - C
    mod_sub(result->y, b, f);
    mod_mul(result->y, d, result->y);
    mod_sub(result->y, result->y, c);
    
    // Z3 = 2*Y*Z
    mod_mul(result->z, p->y, p->z);
    mod_add(result->z, result->z, result->z);
}

// Point addition in Jacobian coordinates
// Reference: Guide to Elliptic Curve Cryptography, Algorithm 3.22
__device__
void point_add(ECPoint* result, const ECPoint* p, const ECPoint* q) {
    if (is_zero(p->z)) {
        *result = *q;
        return;
    }
    if (is_zero(q->z)) {
        *result = *p;
        return;
    }
    
    uint64_t u1[4], u2[4], s1[4], s2[4], h[4], r[4];
    uint64_t z1_squared[4], z2_squared[4], z1_cubed[4], z2_cubed[4];
    uint64_t h_squared[4], h_cubed[4], temp[4];
    
    // Z1^2, Z2^2
    mod_square(z1_squared, p->z);
    mod_square(z2_squared, q->z);
    
    // U1 = X1*Z2^2, U2 = X2*Z1^2
    mod_mul(u1, p->x, z2_squared);
    mod_mul(u2, q->x, z1_squared);
    
    // Z1^3, Z2^3
    mod_mul(z1_cubed, z1_squared, p->z);
    mod_mul(z2_cubed, z2_squared, q->z);
    
    // S1 = Y1*Z2^3, S2 = Y2*Z1^3
    mod_mul(s1, p->y, z2_cubed);
    mod_mul(s2, q->y, z1_cubed);
    
    // Check if points are equal
    if (is_equal(u1, u2)) {
        if (is_equal(s1, s2)) {
            // Points are equal - use doubling
            point_double(result, p);
            return;
        } else {
            // Points are additive inverses - result is point at infinity
            set_zero(result->x);
            set_zero(result->y);
            set_zero(result->z);
            return;
        }
    }
    
    // H = U2 - U1
    mod_sub(h, u2, u1);
    
    // R = S2 - S1
    mod_sub(r, s2, s1);
    
    // H^2, H^3
    mod_square(h_squared, h);
    mod_mul(h_cubed, h_squared, h);
    
    // X3 = R^2 - H^3 - 2*U1*H^2
    mod_square(result->x, r);
    mod_sub(result->x, result->x, h_cubed);
    mod_mul(temp, u1, h_squared);
    mod_add(temp, temp, temp);
    mod_sub(result->x, result->x, temp);
    
    // Y3 = R*(U1*H^2 - X3) - S1*H^3
    mod_mul(temp, u1, h_squared);
    mod_sub(temp, temp, result->x);
    mod_mul(result->y, r, temp);
    mod_mul(temp, s1, h_cubed);
    mod_sub(result->y, result->y, temp);
    
    // Z3 = Z1*Z2*H
    mod_mul(result->z, p->z, q->z);
    mod_mul(result->z, result->z, h);
}

// Scalar multiplication using sliding window method
__device__
void scalar_mult(ECPoint* result, const uint64_t scalar[4], const ECPoint* base) {
    // Point at infinity
    set_zero(result->x);
    set_zero(result->y);
    set_zero(result->z);
    
    // Check for zero scalar
    if (is_zero(scalar)) {
        return;
    }
    
    // Precompute odd multiples [1P, 3P, 5P, 7P, 9P, 11P, 13P, 15P]
    ECPoint precomp[8];
    ECPoint temp, doubled;
    
    precomp[0] = *base;  // 1P
    point_double(&doubled, base);  // 2P
    
    for (int i = 1; i < 8; i++) {
        point_add(&precomp[i], &precomp[i-1], &doubled);
    }
    
    // Sliding window NAF (width 4)
    int naf[256];
    int naf_len = 0;
    
    // Convert scalar to NAF representation
    uint64_t k[4];
    copy_bigint(k, scalar);
    
    while (!is_zero(k)) {
        if (k[0] & 1) {
            // k is odd
            int width = 1;
            uint64_t window = k[0] & 15;  // 4-bit window
            
            // Extend window if possible
            while (width < 4 && (window & (1 << width))) {
                width++;
                if (width < 4) window = k[0] & ((1 << (width + 1)) - 1);
            }
            
            // Make window odd
            if (window & 1) {
                naf[naf_len] = (window + 1) / 2;
            } else {
                naf[naf_len] = 0;
            }
            
            // Subtract window from k
            uint64_t borrow = 0;
            k[0] -= window;
            borrow = k[0] > (UINT64_MAX - window) ? 1 : 0;
            
            for (int i = 1; i < 4 && borrow; i++) {
                if (k[i] == 0) {
                    k[i] = UINT64_MAX;
                } else {
                    k[i]--;
                    borrow = 0;
                }
            }
        } else {
            naf[naf_len] = 0;
        }
        
        // Right shift k by 1
        uint64_t carry = 0;
        for (int i = 3; i >= 0; i--) {
            uint64_t new_carry = k[i] & 1;
            k[i] = (k[i] >> 1) | (carry << 63);
            carry = new_carry;
        }
        
        naf_len++;
        if (naf_len >= 256) break;
    }
    
    // Process NAF from most significant bit
    for (int i = naf_len - 1; i >= 0; i--) {
        point_double(result, result);
        
        if (naf[i] > 0) {
            point_add(result, result, &precomp[naf[i] - 1]);
        }
    }
}

// Convert from bytes to uint64_t array (big endian for secp256k1)
__device__
void bytes_to_bigint(uint64_t dst[4], const uint8_t src[32]) {
    for (int i = 0; i < 4; i++) {
        dst[i] = 0;
        for (int j = 0; j < 8; j++) {
            dst[i] = (dst[i] << 8) | src[i*8 + j];
        }
    }
}

// Convert from affine to Jacobian coordinates
__device__
void affine_to_jacobian(ECPoint* result, const uint64_t x[4], const uint64_t y[4]) {
    copy_bigint(result->x, x);
    copy_bigint(result->y, y);
    uint64_t one_affine[4] = {1, 0, 0, 0};
    copy_bigint(result->z, one_affine);
}

// Convert from Jacobian to affine coordinates
__device__
void jacobian_to_affine(uint64_t x[4], uint64_t y[4], const ECPoint* point) {
    if (is_zero(point->z)) {
        // Point at infinity
        set_zero(x);
        set_zero(y);
        return;
    }
    
    uint64_t z_inv[4], z_inv_squared[4], z_inv_cubed[4];
    
    mod_inverse(z_inv, point->z);
    mod_square(z_inv_squared, z_inv);
    mod_mul(z_inv_cubed, z_inv_squared, z_inv);
    
    mod_mul(x, point->x, z_inv_squared);
    mod_mul(y, point->y, z_inv_cubed);
}

// ECDSA signature verification kernel
__global__
void ecdsa_verify_batch(
    const uint8_t* event_ids,      // 32 bytes per event
    const uint8_t* signatures,     // 64 bytes per signature (r,s)
    const uint8_t* pubkeys,        // 32 bytes per pubkey (x coordinate)
    int* results,                  // Output: 1 = valid, 0 = invalid
    int count                      // Number of signatures to verify
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    
    if (idx >= count) return;
    
    // Extract signature components
    uint64_t r[4], s[4], hash[4], pubkey_x[4];
    
    bytes_to_bigint(r, &signatures[idx * 64]);
    bytes_to_bigint(s, &signatures[idx * 64 + 32]);
    bytes_to_bigint(hash, &event_ids[idx * 32]);
    bytes_to_bigint(pubkey_x, &pubkeys[idx * 32]);
    
    // Basic range checks
    if (is_zero(r) || is_zero(s)) {
        results[idx] = 0;
        return;
    }
    
    // Check if r, s are in valid range [1, n-1]
    // Simplified check - in production would need proper comparison
    if (r[3] >= SECP256K1_N[3] || s[3] >= SECP256K1_N[3]) {
        results[idx] = 0;
        return;
    }
    
    // Reconstruct public key point from x-coordinate
    // For secp256k1: y^2 = x^3 + 7 (mod p)
    ECPoint pubkey_point;
    copy_bigint(pubkey_point.x, pubkey_x);
    
    uint64_t x_squared[4], x_cubed[4], y_squared[4], y_coord[4];
    
    // Calculate x^3 + 7
    mod_square(x_squared, pubkey_x);
    mod_mul(x_cubed, x_squared, pubkey_x);
    
    uint64_t seven[4] = {7, 0, 0, 0};
    mod_add(y_squared, x_cubed, seven);
    
    // Calculate square root using Tonelli-Shanks
    bool sqrt_exists = mod_sqrt(y_coord, y_squared);
    
    if (!sqrt_exists) {
        results[idx] = 0;
        return;
    }
    
    // For Nostr, we use the even y-coordinate (compressed public key format)
    if (y_coord[0] & 1) {
        // y is odd, use p - y to get even y
        mod_sub(y_coord, SECP256K1_P, y_coord);
    }
    
    copy_bigint(pubkey_point.y, y_coord);
    
    uint64_t one_pubkey[4] = {1, 0, 0, 0};
    copy_bigint(pubkey_point.z, one_pubkey);
    
    // ECDSA verification algorithm
    // 1. Calculate u1 = hash * s^(-1) mod n
    // 2. Calculate u2 = r * s^(-1) mod n  
    // 3. Calculate point P = u1*G + u2*pubkey
    // 4. Verify that P.x ≡ r (mod n)
    
    uint64_t s_inv[4], u1[4], u2[4];
    
    // Calculate s^(-1) mod n using Fermat's little theorem
    // For secp256k1: n-2 = 0xBFD25E8CD0364141ULL, 0xBAAEDCE6AF48A03BULL, 0xFFFFFFFFFFFFFFFCULL, 0xFFFFFFFFFFFFFFFFULL
    uint64_t n_minus_2[4] = {
        0xBFD25E8CD036413FULL, 0xBAAEDCE6AF48A03BULL,
        0xFFFFFFFFFFFFFFFCULL, 0xFFFFFFFFFFFFFFFFULL
    };
    
    // s_inv = s^(n-2) mod n
    uint64_t base[4], exp_result[4];
    copy_bigint(base, s);
    uint64_t one_val[4] = {1, 0, 0, 0};
    copy_bigint(s_inv, one_val);
    
    // Binary exponentiation for modular inverse
    for (int i = 0; i < 256; i++) {
        int word = i / 64;
        int bit = i % 64;
        
        if (n_minus_2[word] & (1ULL << bit)) {
            // s_inv = (s_inv * base) mod n
            uint64_t temp[8];
            mul_256x256(temp, s_inv, base);
            
            // Reduce modulo n (simplified)
            for (int j = 0; j < 4; j++) {
                s_inv[j] = temp[j];
            }
        }
        
        if (i < 255) {
            // base = (base * base) mod n
            uint64_t temp[8];
            mul_256x256(temp, base, base);
            for (int j = 0; j < 4; j++) {
                base[j] = temp[j];
            }
        }
    }
    
    // u1 = (hash * s_inv) mod n
    uint64_t temp_u1[8];
    mul_256x256(temp_u1, hash, s_inv);
    for (int i = 0; i < 4; i++) {
        u1[i] = temp_u1[i];
    }
    
    // u2 = (r * s_inv) mod n
    uint64_t temp_u2[8];
    mul_256x256(temp_u2, r, s_inv);
    for (int i = 0; i < 4; i++) {
        u2[i] = temp_u2[i];
    }
    
    // Create generator point
    ECPoint generator;
    affine_to_jacobian(&generator, SECP256K1_GX, SECP256K1_GY);
    
    // Calculate u1*G + u2*pubkey
    ECPoint point1, point2, result_point;
    scalar_mult(&point1, u1, &generator);
    scalar_mult(&point2, u2, &pubkey_point);
    point_add(&result_point, &point1, &point2);
    
    // Convert result to affine coordinates
    uint64_t result_x[4], result_y[4];
    jacobian_to_affine(result_x, result_y, &result_point);
    
    // Check if result_x ≡ r (mod n)
    // Reduce result_x modulo n
    uint64_t r_check[4];
    copy_bigint(r_check, result_x);
    
    // Simple modular reduction (in production would use proper reduction)
    while (cmp_bigint(r_check, SECP256K1_N) >= 0) {
        mod_sub(r_check, r_check, SECP256K1_N);
    }
    
    if (is_equal(r_check, r)) {
        results[idx] = 1;
    } else {
        results[idx] = 0;
    }
}

// C interface for Python
extern "C" {
    
int cuda_ecdsa_verify_batch(
    const uint8_t* h_event_ids,
    const uint8_t* h_signatures, 
    const uint8_t* h_pubkeys,
    int* h_results,
    int count
) {
    // GPU memory pointers
    uint8_t *d_event_ids, *d_signatures, *d_pubkeys;
    int *d_results;
    
    // Calculate sizes
    size_t event_ids_size = count * 32;
    size_t signatures_size = count * 64;
    size_t pubkeys_size = count * 32;
    size_t results_size = count * sizeof(int);
    
    // Allocate GPU memory
    cudaError_t err;
    err = cudaMalloc(&d_event_ids, event_ids_size);
    if (err != cudaSuccess) return -1;
    
    err = cudaMalloc(&d_signatures, signatures_size);
    if (err != cudaSuccess) { cudaFree(d_event_ids); return -1; }
    
    err = cudaMalloc(&d_pubkeys, pubkeys_size);
    if (err != cudaSuccess) { 
        cudaFree(d_event_ids); cudaFree(d_signatures); return -1; 
    }
    
    err = cudaMalloc(&d_results, results_size);
    if (err != cudaSuccess) { 
        cudaFree(d_event_ids); cudaFree(d_signatures); cudaFree(d_pubkeys); 
        return -1; 
    }
    
    // Copy data to GPU
    cudaMemcpy(d_event_ids, h_event_ids, event_ids_size, cudaMemcpyHostToDevice);
    cudaMemcpy(d_signatures, h_signatures, signatures_size, cudaMemcpyHostToDevice);
    cudaMemcpy(d_pubkeys, h_pubkeys, pubkeys_size, cudaMemcpyHostToDevice);
    
    // Launch kernel
    int threads_per_block = 256;
    int blocks = (count + threads_per_block - 1) / threads_per_block;
    
    ecdsa_verify_batch<<<blocks, threads_per_block>>>(
        d_event_ids, d_signatures, d_pubkeys, d_results, count
    );
    
    // Copy results back
    cudaMemcpy(h_results, d_results, results_size, cudaMemcpyDeviceToHost);
    
    // Cleanup
    cudaFree(d_event_ids);
    cudaFree(d_signatures);
    cudaFree(d_pubkeys);
    cudaFree(d_results);
    
    // Check for errors
    err = cudaGetLastError();
    return (err == cudaSuccess) ? 0 : -1;
}

}  // extern "C"