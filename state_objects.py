import random
from diffie_hellman_utils import *
from constants import *
from crypto_utils import *

random.seed(SEED)


class RSAState:
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
        return {
            "public_key": self.public_key,
            "cert": self.cert,
        }


class DiffieHellmanState:

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
        # Prime
        if is_weak:
            self.p = generate_prime_with_digits(1)
        else:
            self.p = generate_prime_with_digits(15)
        # Generator
        self.g = smallest_primitive_root(self.p)

    def set_values(self, p, g):
        self.p = p
        self.g = g

    def generate_keys(self):
        # Secret Exponent
        self.x = random.randint(2, self.p - 1)
        # DH Public Key
        self.A = pow(self.g, self.x, self.p)

    def set_A(self, A):
        self.A = A

    def set_B(self, B):
        self.B = B

    def set_shared_key_from_pub(self, recived_A):
        self.B = recived_A
        self.K = pow(recived_A, self.x, self.p)

    def generate_shared_key_from_secrets(self, x1, x2):
        self.K = pow(self.g, x1 * x2, self.p)
        return self.K

    def public_info(self):
        return {
            "p": self.p,
            "g": self.g,
            "A": self.A,
        }


class UserState:
    def __init__(self, name, rsa_state: RSAState, dh_state: DiffieHellmanState):
        self.name = name
        self.rsa = rsa_state
        self.dh = dh_state

    def start_new_dh(self, p, g, x, A):
        self.dh = DiffieHellmanState(p, g, x, A)
