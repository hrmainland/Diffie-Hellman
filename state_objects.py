"""State classes for RSA, Diffie–Hellman, and combined user state.

This module provides small containers for cryptographic state used
throughout the secure communication demo. RSAState tracks key material
and certificates. DiffieHellmanState tracks DH parameters, secrets,
and derived keys. UserState groups RSA and DH state for an entity.
"""

import random
from diffie_hellman_utils import *
from constants import *
from crypto_utils import *

random.seed(SEED)


class RSAState:
    """Container for RSA key material and associated certificate data."""

    def __init__(self):
        self.public_key = None
        self.private_key = None
        self.cert = None
        self.n = None
        self.e = None
        self.d = None

    def __str__(self):
        return f"RSAState(public_key={self.public_key}, private_key={self.private_key}, cert={self.cert}, n={self.n}, e={self.e}, d={self.d})"

    def generate_values(self, is_demo=False):
        """Generate RSA keys or load demo constants."""
        if is_demo:
            n, e, d = get_rsa_constants()
            self.n = n
            self.e = e
            self.d = d
        else:
            private_key, public_key = get_rsa_keys()
            self.private_key = private_key
            self.public_key = public_key

    def public_info(self):
        """Return public-facing RSA information."""
        return {
            "public_key": self.public_key,
            "cert": self.cert,
        }


class DiffieHellmanState:
    """Container for Diffie–Hellman parameters, secrets, and derived key."""

    def __init__(self):
        self.p = None
        self.g = None
        self.x = None
        self.A = None
        self.B = None
        self.K = None

    def __str__(self):
        return f"DiffiehellmanState(p={self.p}, g={self.g}, x={self.x}, A={self.A}, K={self.K})"

    def generate_values(self, is_weak):
        """Generate p and g with adjustable strength."""
        if is_weak:
            self.p = generate_prime_with_digits(1)
        else:
            self.p = generate_prime_with_digits(15)
        self.g = smallest_primitive_root(self.p)

    def set_values(self, p, g):
        """Set p and g directly."""
        self.p = p
        self.g = g

    def generate_keys(self):
        """Generate secret exponent and corresponding public value."""
        self.x = random.randint(2, self.p - 1)
        self.A = pow(self.g, self.x, self.p)

    def set_A(self, A):
        """Set the DH public value A."""
        self.A = A

    def set_B(self, B):
        """Set the remote DH public value B."""
        self.B = B

    def set_shared_key_from_pub(self, recived_A):
        """Derive the shared key from the received public value."""
        self.B = recived_A
        self.K = pow(recived_A, self.x, self.p)

    def generate_shared_key_from_secrets(self, x1, x2):
        """Compute shared key using externally discovered exponents."""
        self.K = pow(self.g, x1 * x2, self.p)
        return self.K

    def public_info(self):
        """Return DH parameters and public value A for exchange."""
        return {
            "p": self.p,
            "g": self.g,
            "A": self.A,
        }


class UserState:
    """Combined RSA and DH state for a named participant."""

    def __init__(self, name, rsa_state: RSAState, dh_state: DiffieHellmanState):
        self.name = name
        self.rsa = rsa_state
        self.dh = dh_state

    def start_new_dh(self, p, g, x, A):
        """Replace existing DH state with supplied parameters."""
        self.dh = DiffieHellmanState(p, g, x, A)
