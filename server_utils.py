"""
Shared utility functions for Alice and Bob servers.
"""

from state_objects import RSAState
from signed_fields import DHSignedFields, CSRSignedFields
from crypto_utils import sign, simple_sign, public_key_pem_serialize
from message import MessageObj
import networking_utils


def populate_rsa(is_demo=False):
    """Generate RSA key pair for signing."""
    rsa = RSAState()
    rsa.generate_values(is_demo)
    return rsa


def build_dh_fields(name, dh, nonce):
    """Build DHSignedFields from DH state and nonce."""
    return DHSignedFields(
        name=name,
        p=dh.p,
        g=dh.g,
        A=dh.A,
        nonce=nonce,
    )


def get_signature(message_bytes, rsa_state):
    """
    Sign message bytes using RSA state.

    Args:
        message_bytes: The bytes to sign
        rsa_state: RSAState object containing keys

    Returns:
        Signature bytes
    """
    if rsa_state.private_key is not None:
        return sign(message_bytes, rsa_state.private_key)
    elif rsa_state.n is not None:
        return simple_sign(message_bytes, rsa_state.d, rsa_state.n)
    else:
        raise Exception("No means to sign message - missing keys and constants")


def request_certificate_from_ca(name, rsa_state, ca_url, stage, from_name):
    """
    Request a certificate from the CA.

    Args:
        name: The name for the certificate (e.g., "Alice", "Bob")
        rsa_state: RSAState object with generated keys
        ca_url: The CA's URL endpoint
        stage: The current protocol stage
        from_name: The sender name for the message

    Returns:
        dict: The certificate from the CA, or None if request failed
    """
    # Step 1: Serialize public key to PEM
    pub_pem = public_key_pem_serialize(rsa_state.public_key)

    # Step 2: Create CSR (Certificate Signing Request)
    csr_fields = CSRSignedFields(name=name, public_key_pem=pub_pem)
    csr_bytes = csr_fields.to_bytes()

    # Step 3: Sign the CSR (proof of possession)
    csr_sig = get_signature(csr_bytes, rsa_state)

    # Step 4: Send CSR to CA
    print(f"Requesting certificate from CA for {name}")
    msg_obj = MessageObj(
        csr_fields.serializable(),
        from_name,
        "CA",
        ca_url,
        stage,
        csr_sig.hex(),
    )

    response = networking_utils.send(msg_obj)

    # Step 5: Check response
    if response.status_code != 200:
        print("Failed to request certificate from CA")
        print(response.json())
        return None

    print(f"Certificate received from CA for {name}")
    return response.json()
