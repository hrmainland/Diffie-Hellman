from flask import Flask, request, jsonify
from config_utils import load_config
import networking_utils
from message import MessageObj
import builtins
from constants import *
from state_objects import *
from crypto_utils import *
from signed_fields import *
from server_utils import (
    populate_rsa,
    build_dh_fields,
    get_signature,
    request_certificate_from_ca,
    log_outgoing_message,
)
import logging
from ca_server import ca_public_key

NAME = BOB

log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)
app = Flask(__name__)
config = load_config()

bob_port = config[BOB]["base_url"].split(":")[-1]
alice_url = config[ALICE]["base_url"] + "/receive"
mitm_url = config[MITM]["base_url"] + "/receive"
ca_url = config[CA]["base_url"] + "/request"

current_dh = None
current_rsa = None


def send(msg_obj: MessageObj):
    log_outgoing_message(msg_obj, print)
    return networking_utils.send(msg_obj)


def print(*args, **kwargs):
    def blue(text):
        return f"\033[94m{text}\033[0m"

    colored = " ".join(blue(str(arg)) for arg in args)
    builtins.print(colored, **kwargs)


def populate_dh(data, logging=True):
    dh = DiffieHellmanState()
    dh.set_values(data["body"]["p"], data["body"]["g"])
    dh.generate_keys()
    dh.set_shared_key(data["body"]["A"])
    if logging:
        print(dh)
    return dh


def verify_and_extract_dh(data):
    """
    Verify incoming DH message signature and certificate, then extract DH values.

    Args:
        data: Message data from Alice

    Returns:
        DiffieHellmanState if valid, None if verification fails
    """
    # Verify Alice's signature and certificate
    sig_valid = verify_dh_signature(data, ca_public_key)
    if not sig_valid:
        print("Rejecting message due to invalid signature or certificate")
        return None

    # Extract Alice's DH values and compute shared key
    return populate_dh(data)


def send_authenticated_dh_response(dh, rsa_state, stage):
    """
    Build and send DH response with signature and certificate.

    Args:
        dh: DiffieHellmanState with computed values
        rsa_state: RSAState with certificate
        stage: Current protocol stage

    Returns:
        None
    """
    # Generate DH signature
    nonce = generate_nonce()
    dh_fields = build_dh_fields(NAME, dh, nonce)
    message_bytes = dh_fields.to_bytes()
    dh_sig = get_signature(message_bytes, rsa_state)

    # Send response to Alice with Bob's DH values, signature, and certificate
    msg_obj = MessageObj(
        dh_fields.serializable(),
        BOB,
        ALICE,
        mitm_url,
        stage + 0.1,
        dh_sig.hex(),
        cert=rsa_state.cert,
    )

    send(msg_obj)


def handle_response(data):
    global current_dh
    stage = int(data["stage"])
    if stage == 0:
        msg_obj = MessageObj("Hi Alice", BOB, ALICE, alice_url, stage + 0.1)
    elif 1 <= stage < 2:
        msg_obj = MessageObj("It's 4925", BOB, ALICE, mitm_url, stage + 0.1)
    # both 2 - 5 are simple DH
    elif 2 <= stage < 6:
        current_dh = populate_dh(data)
        msg_obj = MessageObj(
            current_dh.public_info(), BOB, ALICE, mitm_url, stage + 0.1
        )
    elif 6 <= stage < 8:

        verify_dh_signature(data, ca_public_key, is_demo=True)

        return jsonify({BOB: "Message received"})
    elif stage == 8:
        global current_rsa

        # Step 1: Verify Alice's message and extract DH values
        current_dh = verify_and_extract_dh(data)
        if current_dh is None:
            return jsonify({BOB: "Message rejected"})

        # Step 2: Generate RSA key pair and obtain certificate from CA
        current_rsa = populate_rsa()
        print(f"Generated RSA key pair for {NAME}")

        current_rsa.cert = request_certificate_from_ca(
            name=NAME,
            rsa_state=current_rsa,
            ca_url=ca_url,
            stage=stage,
            from_name=BOB
        )

        if current_rsa.cert is None:
            return jsonify({BOB: "Certificate request failed"})

        # Step 3: Send authenticated DH response to Alice
        send_authenticated_dh_response(current_dh, current_rsa, stage)

        return jsonify({BOB: "Message received"})
    send(msg_obj)


@app.route("/receive", methods=["POST"])
def receive_message():
    data = request.json
    print(BOB, "Received:", data["body"])
    handle_response(data)
    return jsonify({BOB: "Message received"})


if __name__ == "__main__":
    app.run(port=bob_port, debug=True)
