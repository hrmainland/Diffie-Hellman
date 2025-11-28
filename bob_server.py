"""
This module represents Bob's server. It handles HTTP endpoints that
initiate the different stages of the demo and processes responses.

It receives messages from Alice(via the MITM), responds according to
the current stage of the protocol, and participates in
Diffie–Hellman and authenticated key exchange flows.
"""

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

# Suppress default werkzeug request logging so our custom logger is clearer.
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

app = Flask(__name__)
config = load_config()

# Ports and URLs for participants in the demo.
bob_port = config[BOB]["base_url"].split(":")[-1]
alice_url = config[ALICE]["base_url"] + "/receive"
mitm_url = config[MITM]["base_url"] + "/receive"
ca_url = config[CA]["base_url"] + "/request"

# Global state to emulate persistent server-side storage.
current_dh = None
current_rsa = None
logger = Logger(BOB, BLUE)


def send(msg_obj: MessageObj):
    """Send a message via the networking layer and log the attempt.

    Logs the outgoing message with the custom logger, forwards it using
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


def populate_dh(data, logging=True):
    """Initialise Bob's Diffie–Hellman state from Alice's parameters.

    Uses the p, g, and A values in the incoming message to construct a
    DiffieHellmanState, generate Bob's key pair, and compute the shared key.

    Args:
        data: The JSON-like message payload containing DH fields under data["body"].
        logging: If True, log the resulting DH state.

    Returns:
        An initialised DiffieHellmanState instance.
    """
    dh = DiffieHellmanState()
    dh.set_values(data["body"]["p"], data["body"]["g"])
    dh.generate_keys()
    dh.set_shared_key_from_pub(data["body"]["A"])
    if logging:
        logger.log_dh_state(dh)
    return dh


def verify_and_extract_dh(data):
    """Verify Alice's authenticated DH message and build Bob's DH state.

    First verifies Alice's signature and certificate against the CA,
    then, if valid, extracts the DH values and computes the shared key.

    Args:
        data: Message data received from Alice (via the MITM).

    Returns:
        A DiffieHellmanState if verification succeeds, or None if it fails.
    """
    sig_valid = verify_dh_signature(data, ca_public_key, expected_name=ALICE)
    if not sig_valid:
        logger.log("Rejecting message due to invalid signature or certificate")
        return None

    logger.log("Certificate and signature verified")
    return populate_dh(data)


def send_authenticated_dh_response(dh, rsa_state, stage):
    """Send Bob's side of the authenticated DH exchange back to Alice.

    Builds a message containing Bob's DH values, a fresh nonce, a signature
    over those fields, and Bob's certificate, then sends it via the MITM.

    Args:
        dh: A DiffieHellmanState with Bob's DH values and shared key.
        rsa_state: An RSAState containing Bob's keys and certificate.
        stage: The protocol stage for this message.
    """
    nonce = generate_nonce()
    dh_fields = build_dh_fields(NAME, dh, nonce)
    message_bytes = dh_fields.to_bytes()
    dh_sig = get_signature(message_bytes, rsa_state)

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
    """Handle the full authenticated DH response flow from Bob's side.

    This encapsulates Bob's behaviour when Alice initiates a fully
    authenticated DH exchange:
    1) Verify Alice's signed, certified DH message and build a DH state.
    2) Generate Bob's RSA key pair and obtain a certificate from the CA.
    3) Send an authenticated DH response with Bob's certificate and signature.

    Args:
        data: The incoming message from Alice that starts this flow.

    Returns:
        A JSON response indicating success or failure of the authentication step.
    """
    global current_rsa
    stage = float(data["stage"])

    # Step 1: Verify Alice's message and extract DH values.
    current_dh = verify_and_extract_dh(data)
    if current_dh is None:
        return jsonify({BOB: "Message rejected"})

    # Step 2: Generate RSA key pair and obtain certificate from CA.
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

    # Step 3: Send authenticated DH response to Alice.
    send_authenticated_dh_response(current_dh, current_rsa, stage)


def handle_response(data):
    """Main dispatcher for handling messages received by Bob.

    Behaviour is determined entirely by the protocol stage:
    - 0–1: Simple plaintext HTTP examples.
    - 2–5: Basic DH key exchange (weak/strong parameters).
    - 6–7: DH plus signature demo (no certificate).
    - 8 and above: Fully authenticated DH with certificates.

    Args:
        data: The JSON payload received from Alice or the MITM.
    """
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

    # Stages 2–5: simple DH without signatures.
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
    """HTTP endpoint for receiving messages destined for Bob.

    For each incoming message, this logs the payload, delegates to the
    response handler, and returns a simple acknowledgement.
    """
    data = request.json
    handle_response(data)
    return jsonify({BOB: "Message received"})


if __name__ == "__main__":
    debug = False
    if not debug:
        print("\n" * 200)
    app.run(port=bob_port, debug=debug)
