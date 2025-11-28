"""MITM Flask server for the secure communication demo.

This server sits between Alice and Bob and can:
- Transparently relay messages.
- Tamper with Diffie–Hellman values.
- Perform a brute-force DLP attack on weak DH parameters.
It helps illustrate how a man-in-the-middle can interfere with or break
insecure protocols.
"""

from flask import Flask, request, jsonify
from config_utils import load_config
import networking_utils
from message import MessageObj
from constants import *
from diffie_hellman_utils import *
from state_objects import *
from logger import Logger
import builtins
import time
import logging


# Suppress default werkzeug request logging so our own logger is clearer.
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)
app = Flask(__name__)
config = load_config()

# URLs for forwarding messages on to Alice and Bob.
alice_receive_url = config[ALICE]["base_url"] + "/receive"
bob_receive_url = config[BOB]["base_url"] + "/receive"

# MITM port is taken from the configured base URL.
mitm_port = int(config[MITM]["base_url"].split(":")[-1])

# Global DH state used for attack and relaying.
shared_dh = None
alice_dh = None
bob_dh = None

logger = Logger(MITM, RED)


def send(msg_obj: MessageObj):
    """Send a message via the networking layer and log the attempt."""
    logger.log_outgoing_message(msg_obj)
    response = networking_utils.send(msg_obj)
    if response is None:
        logger.log(f"Warning: {msg_obj.to_name} server did not respond or timed out")
    return response


def simple_relay(data):
    """Forward a message unchanged to Alice or Bob based on `to_name`."""
    to_name = data.get("to_name")

    if to_name == ALICE:
        target_url = alice_receive_url
    elif to_name == BOB:
        target_url = bob_receive_url
    else:
        raise Exception("Unknown recipient")

    msg_obj = MessageObj(
        data["body"],
        data.get("from_name"),
        to_name,
        target_url,
        data.get("stage"),
        data.get("signature"),
        data.get("cert"),
    )

    downstream_resp = send(msg_obj)

    if downstream_resp is None:
        return jsonify({MITM: "Downstream server did not respond"})

    return downstream_resp.json()


def update_body_and_relay(data):
    """Modify the DH public value `A` in the body before relaying.

    This demonstrates how a MITM can tamper with protocol messages and
    potentially break or subvert the security guarantees.
    """
    to_name = data.get("to_name")

    if to_name == ALICE:
        target_url = alice_receive_url
    elif to_name == BOB:
        target_url = bob_receive_url
    else:
        raise Exception("Unknown recipient")

    # Overwrite the DH public value A to simulate tampering.
    data["body"]["A"] = 99

    msg_obj = MessageObj(
        data["body"],
        data.get("from_name"),
        to_name,
        target_url,
        data.get("stage"),
        data.get("signature"),
    )

    downstream_resp = send(msg_obj)

    if downstream_resp is None:
        return jsonify({MITM: "Downstream server did not respond"})

    return downstream_resp.json()


def respond_dh_with_alice(data):
    """Act as Bob toward Alice: complete DH and respond with MITM's public value."""
    global alice_dh
    stage = float(data["stage"])
    alice_dh = DiffieHellmanState()
    alice_dh.set_values(data["body"]["p"], data["body"]["g"])
    alice_dh.generate_keys()
    alice_dh.set_shared_key_from_pub(data["body"]["A"])
    logger.log_dh_state(alice_dh)
    msg_obj = MessageObj(
        alice_dh.public_info(), BOB, ALICE, alice_receive_url, stage + 0.1
    )
    send(msg_obj)


def begin_dh_with_bob(data):
    """Act as Alice toward Bob: start a new (weak) DH exchange with Bob."""
    global bob_dh
    stage = float(data["stage"])
    bob_dh = DiffieHellmanState()
    bob_dh.generate_values(is_weak=True)
    bob_dh.generate_keys()
    logger.log_dh_state(bob_dh)
    msg_obj = MessageObj(bob_dh.public_info(), ALICE, BOB, bob_receive_url, stage + 0.1)
    send(msg_obj)


def finish_dh_with_bob(data):
    """Finish DH with Bob by incorporating his public value and logging the state."""
    global bob_dh
    bob_dh.set_shared_key_from_pub(data["body"]["A"])
    logger.log_dh_state(bob_dh)


@app.route("/receive", methods=["POST"])
def respond():
    """Main MITM entrypoint: inspect and route all messages.

    Behaviour depends on stage:
      - <3: transparent relay.
      - 3–4.x: collect DH parameters and attempt a brute-force DLP attack.
      - 5: split exchange, pretending to be Bob to Alice and Alice to Bob.
      - 6: relay signatures.
      - 7: tamper with DH value A before relaying.
      - All others: default to simple relay.
    """
    global shared_dh
    global alice_dh
    global bob_dh

    data = request.json
    stage = float(data["stage"])

    if data["from_name"] == ALICE:
        logger.new_exchange()
    logger.log_incoming_message(data)

    # Early stages: just pass traffic through.
    if stage < 3:
        return simple_relay(data)

    # Stages 3–4.x: weak DH attack demo.
    elif stage < 5:
        if data["from_name"] == ALICE:
            shared_dh = DiffieHellmanState()
            shared_dh.set_values(data["body"]["p"], data["body"]["g"])
            shared_dh.set_A(data["body"]["A"])
        else:
            shared_dh.set_B(data["body"]["A"])
            logger.log("Generating...")
            secrets = brute_force_dlp(
                shared_dh.g, shared_dh.p, shared_dh.A, shared_dh.B
            )
            if secrets:
                shared_dh.generate_shared_key_from_secrets(secrets[0], secrets[1])
                logger.log(f"The shared key is: {shared_dh.K}")
            else:
                logger.log("Timeout no secrets found")
        return simple_relay(data)

    # Stage 5: MITM runs two separate exchanges, one with Alice and one with Bob.
    elif stage == 5:
        if data["from_name"] == ALICE:
            respond_dh_with_alice(data)
            begin_dh_with_bob(data)
            return jsonify({BOB: "Message received"})

        else:
            finish_dh_with_bob(data)
            return jsonify({ALICE: "Message received"})

    # Stage 6: relay without tampering.
    elif stage == 6:
        return simple_relay(data)

    # Stage 7: tamper with DH field A.
    elif stage == 7:
        return update_body_and_relay(data)

    # Any later stage: default to pass-through behaviour.
    else:
        return simple_relay(data)


if __name__ == "__main__":
    debug = False
    if not debug:
        print("\n" * 200)
    app.run(port=mitm_port, debug=debug)
