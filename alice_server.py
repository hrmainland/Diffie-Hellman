from flask import Flask, request, jsonify
from config_utils import load_config
import networking_utils
from message import MessageObj
import builtins
from signed_fields import *
from constants import *
from state_objects import *
from crypto_utils import *
from server_utils import (
    populate_rsa,
    build_dh_fields,
    get_signature,
    request_certificate_from_ca,
)
from logger import Logger
from ca_server import ca_public_key
import logging

NAME = ALICE
VERBOSE = False

# Suppress default logging
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

app = Flask(__name__)
config = load_config()

# Define server ports
alice_port = config[ALICE]["base_url"].split(":")[-1]
bob_url = config[BOB]["base_url"] + "/receive"
mitm_url = config[MITM]["base_url"] + "/receive"
ca_url = config[CA]["base_url"] + "/request"

# global variables imitating databases/persistent state on real servers
current_dh = None
current_rsa = None
logger = Logger(ALICE, GREEN)


def send(msg_obj: MessageObj):
    # Log outgoing message fields before forwarding to the networking layer.
    logger.log_outgoing_message(msg_obj)
    response = networking_utils.send(msg_obj)
    if response is None:
        logger.log(f"Warning: {msg_obj.to_name} server did not respond or timed out")
    return response


def populate_dh(is_weak_dh, logging=True):
    dh = DiffieHellmanState()
    dh.generate_values(is_weak_dh)
    dh.generate_keys()
    if logging:
        logger.log_dh_state(dh)
    return dh


def build_authenticated_dh_message(dh_state, rsa_state, stage, dest_url):
    """
    Build and send initial DH message with signature and certificate.

    Args:
        dh: DiffieHellmanState with computed values
        rsa_state: RSAState with certificate
        stage: Current protocol stage
        dest_url: Destination URL (typically MITM or Bob)

    Returns:
        None
    """
    # Generate DH signature
    nonce = generate_nonce()
    dh_fields = build_dh_fields(NAME, dh_state, nonce)
    message_bytes = dh_fields.to_bytes()
    dh_sig = get_signature(message_bytes, rsa_state)

    # Send message with DH values, signature, and certificate
    msg_obj = MessageObj(
        dh_fields.serializable(),
        ALICE,
        BOB,
        dest_url,
        stage,
        dh_sig.hex(),
        cert=rsa_state.cert,
    )

    return msg_obj


def full_auth_dh(is_weak_dh=False, stage=FULL_AUTH_DH_STAGE):
    global current_dh
    # Step 1: Generate DH values
    current_dh = populate_dh(is_weak_dh)

    # Step 2: Generate RSA key pair and obtain certificate from CA
    current_rsa = populate_rsa()
    current_rsa.cert = request_certificate_from_ca(
        name=NAME,
        rsa_state=current_rsa,
        ca_url=ca_url,
        stage=stage,
        from_name=ALICE,
        logger=logger,
    )

    if current_rsa.cert is None:
        logger.log("Failed to obtain certificate from CA - aborting authentication")
        return

    # Step 3: Send authenticated DH message to Bob
    msg_obj = build_authenticated_dh_message(current_dh, current_rsa, stage, mitm_url)
    send(msg_obj)


def send_first_msg(stage):
    global current_dh
    global current_rsa

    logger.new_exchange()

    is_weak_dh = stage not in (4, 9)

    if stage == 0:
        msg_obj = MessageObj("Morning Bob", ALICE, "Bob", bob_url, stage)
        send(msg_obj)

    elif stage == 1:
        msg_obj = MessageObj("What's your pin?", ALICE, "Bob", mitm_url, stage)
        send(msg_obj)

    # stages 2 -5 are simple DH
    elif 2 <= stage <= 5:
        current_dh = populate_dh(is_weak_dh)
        msg_obj = MessageObj(current_dh.public_info(), ALICE, BOB, mitm_url, stage)
        send(msg_obj)

    # signature stage
    elif 6 <= stage <= 7:
        # generate DH values
        current_dh = populate_dh(is_weak_dh)

        # generate signature
        current_rsa = populate_rsa(is_demo=True)
        nonce = generate_nonce()
        dh_fields = build_dh_fields(NAME, current_dh, nonce)
        message_bytes = dh_fields.to_bytes()
        sig = get_signature(message_bytes, current_rsa)

        msg_obj = MessageObj(
            dh_fields.serializable(), ALICE, BOB, mitm_url, stage, sig.hex()
        )

        if VERBOSE:
            bits = "".join(f"{b:08b}" for b in message_bytes)
            logger.log("DH message bits: " + bits)

        send(msg_obj)

    elif stage == 8:
        full_auth_dh(is_weak_dh, stage)
        return

    else:
        full_auth_dh()


def handle_response(data):
    """
    Handles responses from Bob and MITM
    """
    global current_dh
    stage = float(data["stage"])
    if 0 <= stage < 2:
        return
    # stages 2-5 all DH
    elif 2 <= stage < 6:
        current_dh.set_shared_key_from_pub(data["body"]["A"])
        logger.log_dh_state(current_dh)
        return
    # stages 6-7 demo signatures
    elif 6 <= stage < 8:
        return
    # stage 8.1 - Bob's response with certificate
    else:
        # Verify Bob's signature and certificate
        sig_valid = verify_dh_signature(data, ca_public_key, expected_name=BOB)
        if not sig_valid:
            logger.log(
                "\nRejecting Bob's message due to invalid signature or certificate!\n"
            )
            return

        logger.log("Certificate and signature verified")

        # If verification passes, complete DH key exchange
        current_dh.set_shared_key_from_pub(data["body"]["A"])
        logger.log_dh_state(current_dh)
        logger.log("\nAuthenticated key exchange completed successfully!\n")
        return


@app.route("/begin", methods=["POST"])
def begin():
    data = request.json
    send_first_msg(data["stage"])
    return jsonify({ALICE: "Message received"})


@app.route("/receive", methods=["POST"])
def receive_message():
    data = request.json
    logger.log_incoming_message(data)
    handle_response(data)
    return jsonify({ALICE: "Message received"})


if __name__ == "__main__":
    app.run(port=alice_port, debug=True)
