from flask import Flask, request, jsonify
from config_utils import load_config
import networking_utils
from message import MessageObj
import builtins
from constants import *
from state_objects import *
from crypto_utils import *
from signed_fields import *
from logger import Logger
from server_utils import (
    populate_rsa,
    build_dh_fields,
    get_signature,
    request_certificate_from_ca,
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
logger = Logger(BOB, BLUE)


def send(msg_obj: MessageObj):
    logger.log_outgoing_message(msg_obj)
    response = networking_utils.send(msg_obj)
    if response is None:
        logger.log(f"Warning: {msg_obj.to_name} server did not respond or timed out")
    return response


def populate_dh(data, logging=True):
    dh = DiffieHellmanState()
    dh.set_values(data["body"]["p"], data["body"]["g"])
    dh.generate_keys()
    dh.set_shared_key_from_pub(data["body"]["A"])
    if logging:
        logger.log_dh_state(dh)
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
    sig_valid = verify_dh_signature(data, ca_public_key, expected_name=ALICE)
    if not sig_valid:
        logger.log("Rejecting message due to invalid signature or certificate")
        return None

    logger.log("Certificate and signature verified")
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


def full_auth_dh_response(data):
    global current_rsa
    stage = float(data["stage"])

    # Step 1: Verify Alice's message and extract DH values
    current_dh = verify_and_extract_dh(data)
    if current_dh is None:
        return jsonify({BOB: "Message rejected"})

    # Step 2: Generate RSA key pair and obtain certificate from CA
    current_rsa = populate_rsa()
    logger.log(f"Generated RSA key pair for {NAME}")

    current_rsa.cert = request_certificate_from_ca(
        name=NAME,
        rsa_state=current_rsa,
        ca_url=ca_url,
        stage=stage,
        from_name=BOB,
        logger=logger,
    )

    if current_rsa.cert is None:
        logger.log("Failed to obtain certificate from CA - aborting authentication")
        return jsonify({BOB: "Certificate request failed"})

    # Step 3: Send authenticated DH response to Alice
    send_authenticated_dh_response(current_dh, current_rsa, stage)


def handle_response(data):
    global current_dh
    if data["from_name"] == ALICE:
        logger.new_exchange()
    logger.log_incoming_message(data)
    stage = float(data["stage"])
    if stage == 0:
        msg_obj = MessageObj("Hi Alice", BOB, ALICE, alice_url, stage + 0.1)
        send(msg_obj)
    elif 1 <= stage < 2:
        msg_obj = MessageObj("It's 4293", BOB, ALICE, mitm_url, stage + 0.1)
        send(msg_obj)
    # both 2 - 5 are simple DH
    elif 2 <= stage < 6:
        current_dh = populate_dh(data)
        msg_obj = MessageObj(
            current_dh.public_info(), BOB, ALICE, mitm_url, stage + 0.1
        )
        send(msg_obj)
    elif 6 <= stage < 8:
        sig_valid = verify_dh_signature(data, ca_public_key, is_demo=True)
        if not sig_valid:
            logger.log("\nRejecting message due to invalid signature or certificate!\n")
            return

        logger.log("Certificate and signature verified")
    else:
        return full_auth_dh_response(data)


@app.route("/receive", methods=["POST"])
def receive_message():
    data = request.json
    handle_response(data)
    return jsonify({BOB: "Message received"})


if __name__ == "__main__":
    app.run(port=bob_port, debug=True)
