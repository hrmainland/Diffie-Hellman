"""
Utility functions for generating demo-sized primes, finding primitive roots,
and performing small discrete-logarithm experiments.

This module includes:
- A Miller–Rabin probabilistic primality test.
- Helpers for generating primes with a minimum number of digits.
- A simple trial-division factorisation routine.
- A primitive-root finder for primes.
- A brute-force discrete log solver.

"""

import random
from math import isqrt
from constants import *

random.seed(SEED)


def _is_probable_prime(n: int, k: int = 15) -> bool:
    """Return True if n is probably prime using the Miller–Rabin test.

    Args:
        n: Integer to test.
        k: Number of random bases to try (more → lower error probability).

    This is a probabilistic test but is more than good enough for demo-sized primes.
    """
    if n < 2:
        return False

    # Write n - 1 as d * 2^r with d odd
    r = 0
    d = n - 1
    while d % 2 == 0:
        d //= 2
        r += 1

    # Handle small primes explicitly so ranges below do not break
    if n in [2, 3]:
        return True

    # Test k random bases a
    for _ in range(k):
        a = random.randrange(2, n - 2)
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            # None of the squarings hit n - 1 → definitely composite
            return False

    return True


def generate_prime_with_digits(num_digits: int) -> int:
    """Generate a random probable prime with at least `num_digits` decimal digits.

    The function samples random odd integers in the target range and runs
    `_is_probable_prime` until it finds one. This is fine for small demo primes.
    """
    if num_digits < 1:
        raise ValueError("num_digits must be >= 1")

    lower = 10 ** (num_digits - 1)
    upper = 10**num_digits - 1

    while True:
        # Pick a random candidate in [lower, upper] and nudge it to be odd
        candidate = random.randrange(lower, upper)
        if candidate % 2 == 0 or candidate % 5 == 0:
            candidate += 1

        if _is_probable_prime(candidate):
            return candidate


def _prime_factors(n: int) -> set[int]:
    """Return the set of prime factors of n using simple trial division.

    This is intentionally naive but is enough for factoring p - 1
    when p is not enormous.
    """
    factors = set()

    # Factor out 2s first
    while n % 2 == 0:
        factors.add(2)
        n //= 2

    # Then factor odd numbers up to sqrt(n)
    f = 3
    limit = isqrt(n) + 1
    while f <= limit and n > 1:
        while n % f == 0:
            factors.add(f)
            n //= f
            limit = isqrt(n) + 1
        f += 2

    if n > 1:
        factors.add(n)

    return factors


def smallest_primitive_root(p: int) -> int:
    """Find the smallest primitive root modulo a prime p.

    A number g is a primitive root mod p if its powers generate all non-zero
    residues modulo p. Equivalently, for every prime factor q of (p - 1),
    g^((p - 1) / q) must not be 1 (mod p).
    """
    if p < 3:
        raise ValueError("p must be an odd prime >= 3")

    phi = p - 1
    factors = _prime_factors(phi)

    # Try candidates g = 2, 3, 4, ... until we find a primitive root
    for g in range(2, p):
        for q in factors:
            # If g^((p - 1) / q) ≡ 1 (mod p) for some q, then g is not primitive
            if pow(g, phi // q, p) == 1:
                break
        else:
            # Passed all factor checks → g is a primitive root
            return g

    raise RuntimeError("No primitive root found – this should not happen for prime p.")


def brute_force_dlp(g, p, A, B):
    """Brute-force the discrete logs for A and B base g modulo p.

    Searches for exponents a and b such that:
        A ≡ g^a (mod p)
        B ≡ g^b (mod p)

    This is only intended for very small p; the loop includes a crude
    cutoff to avoid running forever.
    """
    a = None
    b = None

    for x in range(1, p):
        val = pow(g, x, p)

        if a is None and val == A:
            a = x
        if b is None and val == B:
            b = x

        if a is not None and b is not None:
            break

        # Give up if the search gets unreasonably large for a demo
        if x > 10**6.5:
            return None

    return a, b
