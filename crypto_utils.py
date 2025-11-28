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
    try:
        public_key.verify(
            signature,
            message_bytes,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


def public_key_pem_serialize(public_key):
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def public_key_deserialize_from_pem(pem):
    return serialization.load_pem_public_key(pem.encode("utf-8"))


def verify_certificate(cert, ca_public_key):
    """
    Verify a certificate signed by the CA.

    Args:
        cert: Dictionary with 'body' and 'signature' keys
        ca_public_key: The CA's public key

    Returns:
        tuple: (is_valid: bool, public_key: RSA public key or None)
    """
    try:
        # Extract cert components
        cert_body = cert.get("body")
        cert_sig_hex = cert.get("signature")

        if not cert_body or not cert_sig_hex:
            return (False, None)

        # Reconstruct the signed certificate body bytes
        cert_body_bytes = pack_for_signing(
            ("name", cert_body["name"]),
            ("public_key", cert_body["public_key"]),
            ("issuer", cert_body["issuer"]),
        )

        # Verify the CA's signature
        cert_sig = bytes.fromhex(cert_sig_hex)
        is_valid = verify(cert_body_bytes, cert_sig, ca_public_key)

        if not is_valid:
            return (False, None)

        # Extract and deserialize the public key from the certificate
        public_key_pem = cert_body["public_key"]
        public_key = public_key_deserialize_from_pem(public_key_pem)

        return (True, public_key)

    except Exception:
        return (False, None)


def verify_dh_signature(
    data, ca_public_key, is_demo=False, logging=False, expected_name=None
):
    """
    Verify a DH message signature, with optional certificate verification.

    Args:
        data: Message data containing body and signature
        ca_public_key: The CA's public key (for certificate verification)
        is_demo: If True, use simple demo verification instead of certificates
        logging: If True, print verification status messages

    Returns:
        bool: True if signature is valid, False otherwise
    """
    from signed_fields import DHSignedFields

    # Reconstruct the signed fields from the message
    fields = DHSignedFields(
        name=data["body"]["name"],
        p=data["body"]["p"],
        g=data["body"]["g"],
        A=data["body"]["A"],
        nonce=bytes.fromhex(data["body"]["nonce"]),
    )

    message_bytes = fields.to_bytes()
    sig = bytes.fromhex(data["signature"])

    if is_demo:
        # Demo mode: use simple verification with hardcoded keys
        from constants import DEMO_E, DEMO_N

        result = simple_verify(message_bytes, sig, DEMO_E, DEMO_N)
    else:
        # Stage 8+: Verify certificate first, then verify DH signature
        cert = data.get("cert")
        if not cert:
            if logging:
                print("No certificate found in message")
            return False

        # Verify the certificate using CA's public key
        cert_valid, sender_public_key = verify_certificate(cert, ca_public_key)

        if not cert_valid:
            if logging:
                print("Certificate verification failed")
            return False

        # Bind identity: cert must match expected peer and message body.
        cert_name = cert["body"].get("name")
        body_name = data["body"].get("name")
        if expected_name and cert_name != expected_name:
            if logging:
                print(f"Certificate name mismatch: expected {expected_name}, got {cert_name}")
            return False
        if body_name and cert_name != body_name:
            if logging:
                print(f"Certificate/name mismatch between cert ({cert_name}) and body ({body_name})")
            return False

        if logging:
            print(f"Certificate verified for: {cert['body']['name']}")

        # Verify the DH message signature using the public key from the cert
        result = verify(message_bytes, sig, sender_public_key)

        if logging and result:
            print("DH signature verified")

    return result
