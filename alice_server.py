from flask import Flask, request, jsonify
from config_utils import load_config
import networking_utils
from message import MessageObj
from dh_signed_fields import DHSignedFields
import builtins
from constants import *
from state_objects import *
from crypto_utils import *
import time
import logging

NAME = ALICE
VERBOSE = False

log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)
app = Flask(__name__)
config = load_config()

alice_port = config[ALICE]["base_url"].split(":")[-1]
bob_url = config[BOB]["base_url"] + "/receive"
mitm_url = config[MITM]["base_url"] + "/receive"
ca_url = config["ca"]["base_url"] + "/request"

current_dh = None
current_rsa = None


def send(msg_obj: MessageObj):
    print(f"[{msg_obj.from_name}] Sending:", msg_obj.body)
    if msg_obj.signature is not None:
        print(f"[{msg_obj.from_name}] Signature:", msg_obj.signature[:5] + "...")

    networking_utils.send(msg_obj)


def print(*args, **kwargs):
    def green(text):
        return f"\033[92m{text}\033[0m"

    colored = " ".join(green(str(arg)) for arg in args)
    builtins.print(colored, **kwargs)


def populate_dh(is_weak_dh, logging=True):
    dh = DiffieHellmanState()
    dh.generate_values(is_weak_dh)
    dh.generate_keys()
    if logging:
        print(dh)
    return dh


def populate_rsa(is_demo=False):
    rsa = RSAState()
    rsa.generate_values(is_demo)
    return rsa


def build_dh_fields(nonce):
    global current_dh
    return DHSignedFields(
        name=NAME,
        p=current_dh.p,
        g=current_dh.g,
        A=current_dh.A,
        nonce=nonce,
    )


def get_signature(message_bytes):
    if current_rsa.private_key is not None:
        return sign(message_bytes, current_rsa.private_key)
    elif current_rsa.n is not None:
        return simple_sign(message_bytes, current_rsa.d, current_rsa.n)
    else:
        raise Exception("No means to sign message - missing keys and constants")


def send_first_msg(stage):
    global current_dh
    global current_rsa
    is_weak_dh = stage != 4

    if stage == 0:
        msg_obj = MessageObj("Morning Bob", ALICE, "Bob", bob_url, stage)
    elif stage == 1:
        msg_obj = MessageObj(
            "What's your pin number again?", ALICE, "Bob", mitm_url, stage
        )

    # stages 2 -5 are simple DH
    elif 2 <= stage <= 5:
        current_dh = populate_dh(is_weak_dh)
        msg_obj = MessageObj(current_dh.public_info(), ALICE, BOB, mitm_url, stage)

    # signature stage
    elif 6 <= stage <= 7:
        # generate DH values
        current_dh = populate_dh(is_weak_dh)

        # generate signature
        current_rsa = populate_rsa(is_demo=True)
        nonce = generate_nonce()
        dh_fields = build_dh_fields(nonce)
        message_bytes = dh_fields.to_bytes()
        sig = get_signature(message_bytes)

        msg_obj = MessageObj(
            dh_fields.serializable(), ALICE, BOB, mitm_url, stage, sig.hex()
        )

        if VERBOSE:
            bits = "".join(f"{b:08b}" for b in message_bytes)
            print(bits)

    send(msg_obj)


def handle_response(data):
    """
    Handles responses from Bob and MITM
    """
    global current_dh
    stage = int(data["stage"])
    if stage == 0:
        return
    elif 1 <= stage < 2:
        return
    # stages 2-5 all DH
    elif 2 <= stage < 6:
        current_dh.set_shared_key(data["body"]["A"])
        print(current_dh)
        return


@app.route("/begin", methods=["POST"])
def begin():
    data = request.json
    send_first_msg(data["stage"])
    return jsonify({ALICE: "Message received"})


@app.route("/receive", methods=["POST"])
def receive_message():
    data = request.json
    print(ALICE, "Received:", data["body"])
    handle_response(data)
    return jsonify({ALICE: "Message received"})


if __name__ == "__main__":
    app.run(port=alice_port, debug=True)
