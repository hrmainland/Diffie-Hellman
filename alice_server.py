from flask import Flask, request, jsonify
from config_utils import load_config
import networking_utils
from message import MessageObj
import builtins
from constants import *
from state_objects import *
import time

app = Flask(__name__)
config = load_config()

alice_port = config[ALICE]["base_url"].split(":")[-1]
bob_url = config[BOB]["base_url"] + "/receive"
mitm_url = config[MITM]["base_url"] + "/receive"
ca_url = config["ca"]["base_url"] + "/request"

current_dh = None


def send(msg_obj: MessageObj):
    print(f"[{msg_obj.from_name}] Sending:", msg_obj.text)
    networking_utils.send(msg_obj)


def print(*args, **kwargs):
    def green(text):
        return f"\033[92m{text}\033[0m"

    colored = " ".join(green(str(arg)) for arg in args)
    builtins.print(colored, **kwargs)


def send_first_msg(stage):
    global current_dh
    if stage == 0:
        msg_obj = MessageObj("Morning Bob", ALICE, "Bob", bob_url, stage)
    elif stage == 1:
        msg_obj = MessageObj(
            "What's your pin number again?", ALICE, "Bob", mitm_url, stage
        )

    # stages 2 -5 are simple DH
    elif 2 <= stage <= 5:
        is_weak_dh = stage != 4
        current_dh = DiffieHellmanState()
        current_dh.generate_values(is_weak_dh)
        current_dh.generate_keys()
        print(current_dh)
        msg_obj = MessageObj(current_dh.public_info(), ALICE, "Bob", mitm_url, stage)
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
        current_dh.set_shared_key(data["text"]["A"])
        print(current_dh)
        return


@app.route("/begin", methods=["POST"])
def begin():
    data = request.json
    stage = int(data["stage"])
    send_first_msg(data["stage"])
    return jsonify({ALICE: "Message received"})


@app.route("/receive", methods=["POST"])
def receive_message():
    data = request.json
    print(ALICE, "Received:", data["text"])
    handle_response(data)
    return jsonify({ALICE: "Message received"})


if __name__ == "__main__":
    app.run(port=alice_port, debug=True)
