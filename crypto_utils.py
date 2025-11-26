import secrets
import hashlib
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa
from constants import *


def get_rsa_constants(demo_key=True):

    if demo_key:
        return (DEMO_N, DEMO_E, DEMO_D)

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    priv_nums = private_key.private_numbers()
    pub_nums = private_key.public_key().public_numbers()

    n = pub_nums.n
    e = pub_nums.e
    d = priv_nums.d

    return (n, e, d)


def get_rsa_keys():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    return (private_key, private_key.public_key())


def generate_nonce(n_bytes=16):
    return secrets.token_bytes(n_bytes)


def to_bytes(x):
    if isinstance(x, bytes):
        return x
    if isinstance(x, str):
        return x.encode("utf-8")
    if isinstance(x, int):
        if x == 0:
            return b"\x00"
        length = (x.bit_length() + 7) // 8
        return x.to_bytes(length, "big")
    raise TypeError(f"Cannot convert {type(x)} to bytes")


def pack_for_signing(*named_fields):
    out = b""
    for name, value in named_fields:
        name_b = to_bytes(name)
        val_b = to_bytes(value)
        out += len(name_b).to_bytes(2, "big") + name_b
        out += len(val_b).to_bytes(4, "big") + val_b
    return out


def simple_sign(message_bytes, d, n):
    h = hashlib.sha256(message_bytes).digest()
    m_int = int.from_bytes(h, "big")
    sig_int = pow(m_int, d, n)
    return sig_int.to_bytes((n.bit_length() + 7) // 8, "big")


def simple_verify(message_bytes, sig_bytes, e, n):
    h = hashlib.sha256(message_bytes).digest()
    m_int = int.from_bytes(h, "big")
    s_int = int.from_bytes(sig_bytes, "big")
    recovered = pow(s_int, e, n)
    return recovered == m_int


def sign(message_bytes, private_key):
    return private_key.sign(
        message_bytes,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )


def verify(message_bytes, signature, public_key):
    public_key.verify(
        signature,
        message_bytes,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )


def public_key_pem_serialize(public_key):
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def public_key_deserialize_from_pem(pem):
    return serialization.load_pem_public_key(pem.encode("utf-8"))
