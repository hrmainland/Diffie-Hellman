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

print("=" * 60)
print("CA PRIVATE KEY (for ca_server.py):")
print("=" * 60)
print(f'CA_PRIVATE_KEY_PEM = """{private_pem}"""')
print()

print("=" * 60)
print("CA PUBLIC KEY (for ca_server.py):")
print("=" * 60)
print(f'CA_PUBLIC_KEY_PEM = """{public_pem}"""')
print()

print("=" * 60)
print("HOW TO USE:")
print("=" * 60)
print("1. Copy both CA_PRIVATE_KEY_PEM and CA_PUBLIC_KEY_PEM into ca_server.py")
print("2. Replace the generation code with:")
print()
print("   ca_private_key = serialization.load_pem_private_key(")
print("       CA_PRIVATE_KEY_PEM.encode('utf-8'),")
print("       password=None")
print("   )")
print("   ca_public_key = serialization.load_pem_public_key(")
print("       CA_PUBLIC_KEY_PEM.encode('utf-8')")
print("   )")
