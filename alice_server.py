"""
This module represents Alice's server. It handles HTTP endpoints that
initiate the different stages of the demo and processes responses.

Each flow is initiated by a POST request to the /begin endpoint, which
triggers the appropriate first message from Alice (based on the stage). The /receive endpoint
is used to receive responses from the other participants in the demo.
"""

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

# Suppress the default Flask/werkzeug request logging so our custom logger stands out.
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

app = Flask(__name__)
config = load_config()

# Ports and URLs for the other participants in the demo.
alice_port = config[ALICE]["base_url"].split(":")[-1]
bob_url = config[BOB]["base_url"] + "/receive"
mitm_url = config[MITM]["base_url"] + "/receive"
ca_url = config[CA]["base_url"] + "/request"

# Global state that stands in for persistent storage on a real server.
current_dh = None
current_rsa = None
logger = Logger(ALICE, GREEN)


def send(msg_obj: MessageObj):
    """Send a message via the networking layer and log the attempt.

    Logs the outgoing message through the custom logger, forwards it using
    the networking utilities, and warns if the destination does not respond.

    Args:
        msg_obj: The MessageObj instance to send.

    Returns:
        The response from the remote server, or None if the call failed.
    """
    logger.log_outgoing_message(msg_obj)
    response = networking_utils.send(msg_obj)
    if response is None:
        logger.log(f"Warning: {msg_obj.to_name} server did not respond or timed out")
    return response


def populate_dh(is_weak_dh, logging=True):
    """Create and initialise a Diffie–Hellman state object.

    Args:
        is_weak_dh: If True, use single digit primes (for demo).
        logging: If True, log the resulting DH state.

    Returns:
        An initialised DiffieHellmanState instance.
    """
    dh = DiffieHellmanState()
    dh.generate_values(is_weak_dh)
    dh.generate_keys()
    if logging:
        logger.log_dh_state(dh)
    return dh


def build_authenticated_dh_message(dh_state, rsa_state, stage, dest_url):
    """Construct an authenticated DH message, including signature and certificate.

    This builds the first message in the authenticated DH exchange: it packs
    Alice's DH parameters, a fresh nonce, a signature over those fields, and
    Alice's certificate into a MessageObj ready to be sent.

    Args:
        dh_state: A DiffieHellmanState with computed DH values.
        rsa_state: An RSAState containing Alice's keys and certificate.
        stage: The current protocol stage identifier.
        dest_url: The destination URL (typically MITM or Bob).

    Returns:
        A MessageObj instance representing the outbound authenticated DH message.
    """
    nonce = generate_nonce()
    dh_fields = build_dh_fields(NAME, dh_state, nonce)
    message_bytes = dh_fields.to_bytes()
    dh_sig = get_signature(message_bytes, rsa_state)

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
    """Run the full authenticated DH flow from Alice's perspective.

    This helper wraps all three major steps:
    1) Generate DH parameters.
    2) Generate RSA keys and obtain a certificate from the CA.
    3) Send the authenticated DH message to Bob (via the MITM URL).

    Args:
        is_weak_dh: If True, use weak DH parameters for demonstration.
        stage: The protocol stage identifier used in the outbound message.
    """
    global current_dh
    # Step 1: Generate DH values.
    current_dh = populate_dh(is_weak_dh)

    # Step 2: Generate RSA key pair and obtain certificate from CA.
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

    # Step 3: Send authenticated DH message to Bob.
    msg_obj = build_authenticated_dh_message(current_dh, current_rsa, stage, mitm_url)
    send(msg_obj)


def send_first_msg(stage):
    """Entry point for Alice's first message in a given demo stage.

    The behaviour here is driven entirely by the provided stage number:
    - 0–1: Plaintext HTTP examples.
    - 2–5: Simple DH (weak or strong).
    - 6–7: DH plus signatures (no certificates).
    - 8 and above: Fully authenticated DH with certificates.

    The function also initialises the global DH/RSA state as required.

    Args:
        stage: Integer stage identifier sent from the client.
    """
    global current_dh
    global current_rsa

    logger.new_exchange()

    # For certain stages we deliberately weaken the DH parameters.
    is_weak_dh = stage not in (4, 9)

    if stage == 0:
        msg_obj = MessageObj("Morning Bob", ALICE, BOB, bob_url, stage)
        send(msg_obj)

    elif stage == 1:
        msg_obj = MessageObj("What's your pin?", ALICE, BOB, mitm_url, stage)
        send(msg_obj)

    # Stages 2–5 are simple DH with no signatures.
    elif 2 <= stage <= 5:
        current_dh = populate_dh(is_weak_dh)
        msg_obj = MessageObj(current_dh.public_info(), ALICE, BOB, mitm_url, stage)
        send(msg_obj)

    # Stages 6–7 demonstrate DH with a raw signature but no certificate.
    elif 6 <= stage <= 7:
        current_dh = populate_dh(is_weak_dh)

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
    """Process a response message received from Bob or the MITM.

    Depending on the protocol stage, this either:
    - Ignores early plaintext responses.
    - Completes the DH key agreement.
    - Demonstrates signature verification.
    - Fully verifies Bob's certificate and signature before finalising the key.

    Args:
        data: The JSON payload received by the /receive endpoint.
    """
    global current_dh
    stage = float(data["stage"])

    # Simple plaintext demo; nothing to do on Alice's side.
    if 0 <= stage < 2:
        return

    # Stages 2–5: complete DH by incorporating Bob's public value.
    elif 2 <= stage < 6:
        current_dh.set_shared_key_from_pub(data["body"]["A"])
        logger.log_dh_state(current_dh)
        return

    # Stages 6–7: signature demo only (verification handled elsewhere).
    elif 6 <= stage < 8:
        return

    # Stage 8.x: Bob responds with signed DH and certificate.
    else:
        sig_valid = verify_dh_signature(data, ca_public_key, expected_name=BOB)
        if not sig_valid:
            logger.log(
                "\nRejecting Bob's message due to invalid signature or certificate!\n"
            )
            return

        logger.log("Certificate and signature verified")

        current_dh.set_shared_key_from_pub(data["body"]["A"])
        logger.log_dh_state(current_dh)
        logger.log("\nAuthenticated key exchange completed successfully!\n")
        return


@app.route("/begin", methods=["POST"])
def begin():
    """HTTP endpoint to start a protocol run for a given stage.

    Expects JSON of the form: {"stage": <int>}, then triggers the appropriate
    first message from Alice and returns a simple acknowledgement.
    """
    data = request.json
    send_first_msg(data["stage"])
    return jsonify({ALICE: "Message received"})


@app.route("/receive", methods=["POST"])
def receive_message():
    """HTTP endpoint for handling incoming messages destined for Alice.

    Logs the incoming message, passes it to the response handler, and returns
    a basic acknowledgement to the sender.
    """
    data = request.json
    if int(data.get("stage")) >= 0:
        logger.log_incoming_message(data)
        handle_response(data)
    return jsonify({ALICE: "Message received"})


if __name__ == "__main__":
    debug = False
    if not debug:
        print("\n" * 200)
    app.run(port=alice_port, debug=debug)
