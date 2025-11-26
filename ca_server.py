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

ca_private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)
ca_public_key = ca_private_key.public_key()


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
