"""
Cryptographic helpers for Diffie-Hellman and RSA.
This module wraps both simple textbook-style RSA helpers (for demonstration)
and proper cryptography primitives from `cryptography`.
It also provides utilities for packing fields for signing, serialising keys,
and verifying certificates and DH message signatures.
"""

import secrets
import hashlib
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa
from constants import *


def get_rsa_constants(demo_key=True):
    """Return RSA (n, e, d) either from demo constants or from a fresh keypair.

    When `demo_key` is True, the function returns fixed RSA constants from
    `constants.py` so that signatures and examples are reproducible in the demo.
    Otherwise, it generates a new 2048-bit RSA key and extracts n, e, d.

    Args:
        demo_key: If True, return DEMO_N/DEMO_E/DEMO_D instead of generating.

    Returns:
        Tuple[int, int, int]: (n, e, d) RSA parameters.
    """
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
    """Generate a fresh RSA private/public keypair.

    Returns:
        Tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]: The generated keypair.
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    return (private_key, private_key.public_key())


def generate_nonce(n_bytes=16):
    """Generate a cryptographically secure random nonce.

    Args:
        n_bytes: Number of random bytes to generate.

    Returns:
        bytes: Random nonce.
    """
    return secrets.token_bytes(n_bytes)


def to_bytes(x):
    """Convert a supported value into a big-endian bytes representation.

    Supports bytes (returned as-is), strings (UTF-8 encoded), and non-negative
    integers (minimal big-endian representation, with 0 mapped to b"\\x00").

    Args:
        x: The value to convert.

    Returns:
        bytes: Byte representation of `x`.

    Raises:
        TypeError: If `x` is of an unsupported type.
    """
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
    """Pack (name, value) pairs into a deterministic byte string.

    The layout is:
        [name_len:2][name][value_len:4][value]...

    This gives a structured, unambiguous representation for signing.

    Args:
        *named_fields: Iterable of (name, value) pairs.

    Returns:
        bytes: Packed, structured representation suitable for hashing/signing.
    """
    out = b""
    for name, value in named_fields:
        name_b = to_bytes(name)
        val_b = to_bytes(value)
        out += len(name_b).to_bytes(2, "big") + name_b
        out += len(val_b).to_bytes(4, "big") + val_b
    return out


def simple_sign(message_bytes, d, n):
    """Compute a textbook-style RSA signature over SHA-256(message).

    This is intentionally "simple" and not padding-safe; it exists purely
    for demonstration purposes.

    Args:
        message_bytes: The message to sign.
        d: RSA private exponent.
        n: RSA modulus.

    Returns:
        bytes: The raw signature value as a big-endian byte string.
    """
    h = hashlib.sha256(message_bytes).digest()
    m_int = int.from_bytes(h, "big")
    sig_int = pow(m_int, d, n)
    return sig_int.to_bytes((n.bit_length() + 7) // 8, "big")


def simple_verify(message_bytes, sig_bytes, e, n):
    """Verify a textbook-style RSA signature over SHA-256(message).

    Args:
        message_bytes: The original message bytes.
        sig_bytes: The signature to verify.
        e: RSA public exponent.
        n: RSA modulus.

    Returns:
        bool: True if verification succeeds, False otherwise.
    """
    h = hashlib.sha256(message_bytes).digest()
    m_int = int.from_bytes(h, "big")
    s_int = int.from_bytes(sig_bytes, "big")
    recovered = pow(s_int, e, n)
    return recovered == m_int


def sign(message_bytes, private_key):
    """Sign a message using a real RSA key and PKCS#1 v1.5 + SHA-256.

    Args:
        message_bytes: The message to sign.
        private_key: An RSAPrivateKey from `cryptography`.

    Returns:
        bytes: The generated signature.
    """
    return private_key.sign(
        message_bytes,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )


def verify(message_bytes, signature, public_key):
    """Verify a PKCS#1 v1.5 + SHA-256 RSA signature.

    Args:
        message_bytes: The original message bytes.
        signature: The signature to verify.
        public_key: An RSAPublicKey from `cryptography`.

    Returns:
        bool: True if the signature is valid, False otherwise.
    """
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
    """Serialise an RSA public key to a PEM string.

    Args:
        public_key: An RSAPublicKey instance.

    Returns:
        str: PEM-encoded public key.
    """
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def public_key_deserialize_from_pem(pem):
    """Load an RSA public key from a PEM string.

    Args:
        pem: The PEM-encoded public key as a string.

    Returns:
        RSAPublicKey: The deserialised public key object.
    """
    return serialization.load_pem_public_key(pem.encode("utf-8"))


def verify_certificate(cert, ca_public_key):
    """Verify a certificate signed by the CA and extract the subject key.

    Args:
        cert: Dictionary with 'body' and 'signature' keys.
              `body` must contain 'name', 'public_key', and 'issuer'.
        ca_public_key: The CA's public RSA key.

    Returns:
        tuple[bool, RSAPublicKey | None]:
            (is_valid, subject_public_key) where `subject_public_key` is the
            key embedded in the certificate if verification succeeds, else None.
    """
    try:
        # Extract cert components.
        cert_body = cert.get("body")
        cert_sig_hex = cert.get("signature")

        if not cert_body or not cert_sig_hex:
            return (False, None)

        # Reconstruct the signed certificate body bytes.
        cert_body_bytes = pack_for_signing(
            ("name", cert_body["name"]),
            ("public_key", cert_body["public_key"]),
            ("issuer", cert_body["issuer"]),
        )

        # Verify the CA's signature.
        cert_sig = bytes.fromhex(cert_sig_hex)
        is_valid = verify(cert_body_bytes, cert_sig, ca_public_key)

        if not is_valid:
            return (False, None)

        # Extract and deserialize the public key from the certificate.
        public_key_pem = cert_body["public_key"]
        public_key = public_key_deserialize_from_pem(public_key_pem)

        return (True, public_key)

    except Exception:
        # Any parsing or verification failure is treated as an invalid cert.
        return (False, None)


def verify_dh_signature(
    data, ca_public_key, is_demo=False, logging=False, expected_name=None
):
    """Verify a DH message signature, optionally with full certificate checking.

    For demo stages, this can use a simple hard-coded RSA key. For the fully
    authenticated stage, it verifies the sender's certificate with the CA,
    checks that the identity matches what we expect, and then verifies the
    DH signature using the public key from the certificate.

    Args:
        data: Message data containing 'body', 'signature', and optionally 'cert'.
        ca_public_key: The CA's public RSA key, used to verify certificates.
        is_demo: If True, use simple demo verification (DEMO_N/DEMO_E) instead
                 of the full certificate-based path.
        logging: If True, print diagnostic information during verification.
        expected_name: Optional string; if provided, the certificate subject
                      must match this name.

    Returns:
        bool: True if the DH signature (and certificate, if applicable) is valid.
    """
    from signed_fields import DHSignedFields

    # Reconstruct the signed fields from the message.
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
        # Demo mode: use simple verification with hardcoded keys.
        from constants import DEMO_E, DEMO_N

        result = simple_verify(message_bytes, sig, DEMO_E, DEMO_N)
    else:
        # Stage 8+: Verify certificate first, then verify DH signature.
        cert = data.get("cert")
        if not cert:
            if logging:
                print("No certificate found in message")
            return False

        # Verify the certificate using CA's public key.
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

        # Verify the DH message signature using the public key from the cert.
        result = verify(message_bytes, sig, sender_public_key)

        if logging and result:
            print("DH signature verified")

    return result
