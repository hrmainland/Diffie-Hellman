"""
Generates a fresh RSA key pair for the demo CA and prints the private and
public keys in PEM format so they can be copied into ca_server.py.
"""


from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Generate CA key pair
ca_private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)
ca_public_key = ca_private_key.public_key()

# Serialize private key to PEM
private_pem = ca_private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
).decode('utf-8')

# Serialize public key to PEM
public_pem = ca_public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')
