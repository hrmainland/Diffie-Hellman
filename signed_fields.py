"""Signed field structures used in the secure communication demo.

These dataclasses represent the structured data that is signed
during Diffie–Hellman exchanges (DHSignedFields) and during certificate
signing requests (CSRSignedFields). Each class provides:
- A `serializable()` method used when embedding fields inside messages.
- A `to_bytes()` method that packs the fields deterministically for signing.
"""

from dataclasses import dataclass
from typing import Any

# Uses the same deterministic packing format shared with crypto_utils.
from crypto_utils import pack_for_signing


@dataclass
class DHSignedFields:
    """Structured representation of all fields that must be signed in DH messages.

    The MITM, Alice, and Bob all reconstruct this representation so that
    verification is consistent. Using deterministic packing ensures that
    both sides compute the identical byte sequence before signing.
    """

    name: str
    # Prime
    p: int
    # Generator (alpha)
    g: int
    # Public key
    A: int
    # Random nonce
    nonce: bytes

    def serializable(self):
        """Return the structure in JSON-serialisable form.

        This is used when embedding into a MessageObj that will be sent
        across the network.
        """
        return {
            "name": self.name,
            "p": self.p,
            "g": self.g,
            "A": self.A,
            "nonce": self.nonce.hex(),
        }

    def to_bytes(self) -> bytes:
        """Return the packed, deterministic byte representation for signing."""
        return pack_for_signing(
            ("name", self.name),
            ("p", self.p),
            ("g", self.g),
            ("A", self.A),
            ("nonce", self.nonce),
        )


@dataclass
class CSRSignedFields:
    """Fields included in a Certificate Signing Request (CSR).

    Contains the subject's name and PEM-encoded public key. This is sent
    to the CA, signed by the requester as proof of possession.
    """

    # Identity to appear on the certificate
    name: str
    # PEM-encoded RSA public key
    public_key_pem: str

    def serializable(self):
        """Return a JSON-ready representation for MessageObj."""
        return {
            "name": self.name,
            "public_key": self.public_key_pem,
        }

    def to_bytes(self) -> bytes:
        """Return deterministic packed bytes for CSR signing."""
        return pack_for_signing(
            ("name", self.name),
            ("public_key", self.public_key_pem),
        )
