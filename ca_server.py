from flask import Flask, request, jsonify
from config_utils import load_config
from signed_fields import CSRSignedFields
from crypto_utils import pack_for_signing, public_key_deserialize_from_pem
from constants import *
from networking_utils import send
from message import MessageObj

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding

app = Flask(__name__)
config = load_config()

alice_receive_url = config[ALICE]["base_url"] + "/receive"
bob_receive_url = config[BOB]["base_url"] + "/receive"

ca_port = int(config[CA]["base_url"].split(":")[-1])

# # TODO: Replace with hardcoded CA key pair
# ca_private_key = rsa.generate_private_key(
#     public_exponent=65537,
#     key_size=2048,
# )
# ca_public_key = ca_private_key.public_key()

CA_PRIVATE_KEY_PEM = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCOYQUf+K7AiYwX
aQ32xH9DiwuVnmOJhZiEUevWbZAA7X/+uMI2cSYvlyNor1FT76cqPT5W30YjvN6C
9Os7rBMnS9l0vMUtLMAq8QzMmDzAAZWYM/MLxHuL+qadsJANA56zNv9O1L/Cmh2F
SJ46ncuZXoAHJBECRY7G3+5dxC7lZO+qLaVli1C2pQizpQxoSFnUYAD5sGRfuAuo
yWLFo0l3CeUbidvNh+9I1yI/ZNU1O2vyKzK+Pt8cLQYJFYFoYPdg2/adi5kDS4ZE
8wNsoZnkvO2nQigzhBApXYP2RL2vu2EXgMNCTyWvvNNjOGIsTzoNVJM1VOc71qSW
vqeGVvrNAgMBAAECggEAC1roAHqCH2do5ZYSj8dwmeetOxfIeveNaCIrc6zFwxkt
79f230YrZDjC0W7IBvByTc9YGTAR5ThDK8ESQK5S0bu+Ik4K0LVEtzgFzAxpLewC
bQLZo6reKpYJM0LZXjxXbBYbCwOzLndBmvdlbSnYCsmLXuZst9hp0GkcFtzWW6OQ
dcw+74+ab1XuyfxCvALwlpuUTmy9p++dsFTTEqqYtV6XjW4iHKwRne3P70ZI35J3
mvjp9uS+0gYPsvssZfpWIUTkMApsevIrLGZHIYNiDy5g/MVz2D/gqMko6vKGDdi/
GRQ0ar2hvYBU3qvbgmWq8j4GyiTvwAD/I0OdKn43OQKBgQDESU8yqINkmGrByH1t
WtIA6OHjXjIU3ul1W0Aw1lnF+qi09np8PVJqgvjviH1Xss2Qj4VaRsUl1y0aqOrV
2xStBx6P7bQJeJz/jpmJgdYXN/oBcXY1ayxiRXxelf5TgK0QJNIpdjICuTTxySKe
soLNKncaadL2EMPqPOSWBOx9hQKBgQC5sW3SfTvwIygQI8i58NzE9v6UO99I3r9M
s9oc3K3dditKa7o1lfSIumLKWT770hOUkKAxDedT61AixMNeEoJFpLaO9omZAEKl
AJqRTXMpT1M7Antoxl9ZUfr/MRyAR5RfuUB1uiLeNvicv/JeFuOvidwWLhQf31oh
0XU/uVsGqQKBgFlNpTu+EXGeKswZpH8xV+RUEBm7DHwUYxEiwBS4IUYC4ejbTyTh
XXLaPdn1NlnFHuOLeLd3BVFPEdVUTuuXblO+rnf7RPMeLgfTYCWAreAIdrVbYtWw
+hOH26rJAVoKbDKxHfEBNoWor97ljNu5CevAS0n4JaQQQqJ6q+FZQiNlAoGBAIMy
uUVe9lpUfJnqroexhkojuPtC0h/KQZ8P86swwCcYtr1+H7J8oKl6BxKwu69wXiU5
ifUevbKtL5FhNCfjK+fI2LNpvQ49ANlT8+F1t0gYo9Wti0Qb5IJXSd/D8z8vU8XO
PZzwRnJ6pG0bsUKJKZV88eM56z4ZsLT0KMM9UvMBAoGAUmRf9aN//1lLR3aiFYcb
AdVXr7P05pZDTO+wZDMtL8kFCuXW04F1Dwp+UmcaERk3TmyQFz0Yx3Lfwo4N1+TY
tZPqx7aGrdAD6dVhy+kQ3vw5qrN6oZnETi39NI9EQNPAUqpRW0tXvRH9o1ZBeTIy
LQ8sXO+bNbWxGpKGpVfEPfI=
-----END PRIVATE KEY-----
"""

CA_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAjmEFH/iuwImMF2kN9sR/
Q4sLlZ5jiYWYhFHr1m2QAO1//rjCNnEmL5cjaK9RU++nKj0+Vt9GI7zegvTrO6wT
J0vZdLzFLSzAKvEMzJg8wAGVmDPzC8R7i/qmnbCQDQOeszb/TtS/wpodhUieOp3L
mV6AByQRAkWOxt/uXcQu5WTvqi2lZYtQtqUIs6UMaEhZ1GAA+bBkX7gLqMlixaNJ
dwnlG4nbzYfvSNciP2TVNTtr8isyvj7fHC0GCRWBaGD3YNv2nYuZA0uGRPMDbKGZ
5Lztp0IoM4QQKV2D9kS9r7thF4DDQk8lr7zTYzhiLE86DVSTNVTnO9aklr6nhlb6
zQIDAQAB
-----END PUBLIC KEY-----
"""

# load the CA keys from PEM format
ca_private_key = serialization.load_pem_private_key(
    CA_PRIVATE_KEY_PEM.encode("utf-8"), password=None
)
ca_public_key = public_key_deserialize_from_pem(CA_PUBLIC_KEY_PEM)


@app.route("/request", methods=["POST"])
def handle_csr():
    data = request.json

    body = data.get("body")
    sig_hex = data.get("signature")
    if body is None or sig_hex is None:
        print("Missing body or signature")
        return jsonify({"error": "Missing body or signature"}), 400

    name = body.get("name")
    pub_pem = body.get("public_key")
    if not name or not pub_pem:
        print("CSR body missing name/public_key")
        return jsonify({"error": "CSR body missing name/public_key"}), 400

    csr_fields = CSRSignedFields(
        name=name,
        public_key_pem=pub_pem,
    )

    csr_bytes = csr_fields.to_bytes()

    try:
        # revert public key from pem format
        requester_pub = public_key_deserialize_from_pem(pub_pem)
    except Exception:
        return jsonify({"error": "Invalid public key in CSR"}), 400

    try:
        requester_pub.verify(
            bytes.fromhex(sig_hex),
            csr_bytes,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except Exception:
        print("Proof-of-possession failed")
        return jsonify({"error": "Proof-of-possession failed"}), 400

    cert_body = {
        "name": name,
        "public_key": pub_pem,
        "issuer": "Demo CA",
    }

    cert_body_bytes = pack_for_signing(
        ("name", cert_body["name"]),
        ("public_key", cert_body["public_key"]),
        ("issuer", cert_body["issuer"]),
    )

    cert_sig = ca_private_key.sign(
        cert_body_bytes,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    cert_sig_hex = cert_sig.hex()

    cert = {
        "body": cert_body,
        "signature": cert_sig_hex,
    }

    return jsonify(cert), 200


if __name__ == "__main__":
    app.run(port=ca_port, debug=True)
