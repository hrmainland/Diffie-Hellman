from flask import Flask, request, jsonify
from config_utils import load_config
import networking_utils
from message import MessageObj
import builtins
from constants import *
from state_objects import *
from crypto_utils import *
from dh_signed_fields import DHSignedFields
import time
import logging

NAME = BOB

log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)
app = Flask(__name__)
config = load_config()

bob_port = config[BOB]["base_url"].split(":")[-1]
alice_url = config[ALICE]["base_url"] + "/receive"
mitm_url = config[MITM]["base_url"] + "/receive"
ca_url = config["ca"]["base_url"] + "/request"

current_dh = None


def send(msg_obj: MessageObj):
    print(f"[{msg_obj.from_name}] Sending:", msg_obj.body)
    networking_utils.send(msg_obj)


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


def verify_signature(data, is_demo=False, logging=True):
    fields = DHSignedFields(
        name=data["body"]["name"],
        p=data["body"]["p"],
        g=data["body"]["g"],
        A=data["body"]["A"],
        nonce=bytes.fromhex(data["body"]["nonce"]),
    )

    message_bytes = fields.to_bytes()
    sig = bytes.fromhex(data["signature"])
    if is_demo:
        result = simple_verify(message_bytes, sig, DEMO_E, DEMO_N)
    else:
        # pull public key from CA
        public_key = None
        ##### ^ UPDATE
        result = verify(message_bytes, sig, public_key)
    if logging:
        if result:
            print("Signature is valid")
        else:
            print("Signature is invalid rejecting packet")
    return result


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

        verify_signature(data, is_demo=True)

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
