from dataclasses import dataclass
from typing import Any

# reuse your to_bytes / pack_for_signing helpers
from crypto_utils import pack_for_signing


@dataclass
class DHSignedFields:
    name: str
    p: int
    g: int
    A: int
    nonce: bytes

    def serializable(self):
        return {
            "name": self.name,
            "p": self.p,
            "g": self.g,
            "A": self.A,
            "nonce": self.nonce.hex(),
        }

    def to_bytes(self) -> bytes:
        return pack_for_signing(
            ("name", self.name),
            ("p", self.p),
            ("g", self.g),
            ("A", self.A),
            ("nonce", self.nonce),
        )
