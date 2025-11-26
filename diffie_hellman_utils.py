import random
from math import isqrt
from constants import *

random.seed(SEED)


def _is_probable_prime(n: int, k: int = 15) -> bool:
    """
    Miller–Rabin probabilistic primality test.
    """
    if n < 2:
        return False

    # Write n-1 as d * 2^r with d odd
    r = 0
    d = n - 1
    while d % 2 == 0:
        d //= 2
        r += 1

    # avoid empty range
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
            # None of the squarings made it n-1 it's composite
            return False

    #  It's probably prime
    return True


def generate_prime_with_digits(num_digits: int) -> int:
    """
    Generate a random prime with AT LEAST `num_digits` decimal digits.

    - We pick a random odd number in [10^(d-1), 10^d - 1] and test it.
    - Keep trying until we hit a probable prime.
    - This is fine for demo sized primes (e.g. 8–30 digits).
    """
    if num_digits < 1:
        raise ValueError("num_digits must be >= 1")

    lower = 10 ** (num_digits - 1)
    upper = 10**num_digits - 1

    while True:
        # pick a random odd candidate in [lower, upper]
        candidate = random.randrange(lower, upper)
        if candidate % 2 == 0 or candidate % 5 == 0:
            candidate += 1

        if _is_probable_prime(candidate):
            return candidate


def _prime_factors(n: int) -> set[int]:
    """
    Very simple trial-division factorisation.
    Good enough for factoring p-1 where p is not astronomically large.
    """
    factors = set()
    # factor out 2s
    while n % 2 == 0:
        factors.add(2)
        n //= 2

    # factor odd numbers
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
    """
    Find the smallest primitive root modulo a prime p.

    A number g is a primitive root mod p if its powers generate all
    non-zero residues modulo p; equivalently, for every prime factor q
    of (p-1), we have g^((p-1)/q) != 1 (mod p).
    """
    if p < 3:
        raise ValueError("p must be an odd prime >= 3")

    phi = p - 1
    factors = _prime_factors(phi)

    # Try candidates g = 2,3,4,... until we find a primitive root
    for g in range(2, p):
        for q in factors:
            # if g^((p-1)/q) ≡ 1 (mod p) for some q, then g is NOT primitive
            if pow(g, phi // q, p) == 1:
                break
        else:
            # no factor q made it 1 → this g is a primitive root
            return g

    raise RuntimeError("No primitive root found – this should not happen for prime p.")


def brute_force_dlp(g, p, A, B):
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

        # timeout
        if x > 10**6.5:
            return None

    return a, b
