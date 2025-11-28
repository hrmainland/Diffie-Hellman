"""
Shared utility functions for Alice and Bob servers.

This module provides helper functions for constructing Diffie–Hellman
signed fields, generating RSA state, signing messages, and requesting
certificates from the Certificate Authority (CA). It is imported by both
Alice and Bob to keep their server logic clean and consistent.
"""

from state_objects import RSAState
from signed_fields import DHSignedFields, CSRSignedFields
from crypto_utils import sign, simple_sign, public_key_pem_serialize
from message import MessageObj
import networking_utils


def populate_rsa(is_demo=False):
    """Create an RSAState and generate its key material.

    For demo mode, RSAState may load pre-defined n/e/d constants.
    For normal mode, it generates a real RSA private/public keypair.

    Args:
        is_demo: Whether to use demo RSA parameters.

    Returns:
        RSAState: The RSA key state for signing operations.
    """
    rsa = RSAState()
    rsa.generate_values(is_demo)
    return rsa


def build_dh_fields(name, dh, nonce):
    """Construct DHSignedFields from a Diffie–Hellman state and nonce.

    Args:
        name: Identity string ("Alice" or "Bob").
        dh: A DiffieHellmanState with p, g, A values.
        nonce: Random nonce to include in the signed structure.

    Returns:
        DHSignedFields: Ready for serialisation and signing.
    """
    return DHSignedFields(
        name=name,
        p=dh.p,
        g=dh.g,
        A=dh.A,
        nonce=nonce,
    )


def get_signature(message_bytes, rsa_state):
    """Sign the given message using the provided RSAState.

    Uses proper cryptography-based signing when a private_key exists,
    and falls back to simple textbook RSA when using demo constants.

    Args:
        message_bytes: Raw bytes to sign.
        rsa_state: RSAState containing either private_key or (n, d).

    Returns:
        bytes: The resulting signature.

    Raises:
        Exception: If no signing method is available.
    """
    if rsa_state.private_key is not None:
        return sign(message_bytes, rsa_state.private_key)
    elif rsa_state.n is not None:
        return simple_sign(message_bytes, rsa_state.d, rsa_state.n)
    else:
        raise Exception("No means to sign message - missing keys and constants")


def request_certificate_from_ca(name, rsa_state, ca_url, stage, from_name, logger=None):
    """Send a CSR to the Certificate Authority and return the signed certificate.

    This function:
      1. Serialises the subject's public key to PEM.
      2. Builds a CSRSignedFields structure.
      3. Signs it (proof of possession).
      4. Sends it to the CA as a MessageObj.
      5. Parses the CA’s response.

    Args:
        name: Name to appear on the certificate (e.g., "Alice").
        rsa_state: RSAState containing a valid keypair.
        ca_url: The CA's /request endpoint.
        stage: Protocol stage for routing/logging.
        from_name: Who is sending the CSR ("Alice" or "Bob").
        logger: Optional logger for status output.

    Returns:
        dict | None: Certificate returned by CA, or None on failure.
    """
    # Step 1: Serialize public key into PEM
    pub_pem = public_key_pem_serialize(rsa_state.public_key)

    # Step 2: Prepare CSR fields
    csr_fields = CSRSignedFields(name=name, public_key_pem=pub_pem)
    csr_bytes = csr_fields.to_bytes()

    # Step 3: Sign CSR
    csr_sig = get_signature(csr_bytes, rsa_state)

    # Step 4: Send CSR to CA
    if logger:
        logger.log(f"Requesting certificate from CA for {name}")

    msg_obj = MessageObj(
        csr_fields.serializable(),
        from_name,
        "CA",
        ca_url,
        stage,
        csr_sig.hex(),
    )

    response = networking_utils.send(msg_obj)

    # Step 5: Handle CA response
    if response is None:
        if logger:
            logger.log("Warning: CA server did not respond or timed out")
        return None

    if response.status_code != 200:
        if logger:
            logger.log("Failed to request certificate from CA")
            logger.log(str(response.json()))
        return None

    if logger:
        logger.log(f"Certificate received from CA for {name}")

    return response.json()
