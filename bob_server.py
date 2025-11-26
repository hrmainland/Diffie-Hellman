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

bob_port = config[BOB]["base_url"].split(":")[-1]
alice_url = config[ALICE]["base_url"] + "/receive"
mitm_url = config[MITM]["base_url"] + "/receive"
ca_url = config["ca"]["base_url"] + "/request"

current_dh = None


def send(msg_obj: MessageObj):
    print(f"[{msg_obj.from_name}] Sending:", msg_obj.text)
    networking_utils.send(msg_obj)


def print(*args, **kwargs):
    def blue(text):
        return f"\033[94m{text}\033[0m"

    colored = " ".join(blue(str(arg)) for arg in args)
    builtins.print(colored, **kwargs)


def handle_response(data):
    global current_dh
    stage = int(data["stage"])
    if stage == 0:
        msg_obj = MessageObj("Hi Alice", BOB, ALICE, alice_url, stage + 0.1)
    elif 1 <= stage < 2:
        msg_obj = MessageObj("It's 4925", BOB, ALICE, mitm_url, stage + 0.1)
    # both 2 - 5 are simple DH
    elif 2 <= stage < 6:
        current_dh = DiffieHellmanState()
        current_dh.set_values(data["text"]["p"], data["text"]["g"])
        current_dh.generate_keys()
        current_dh.set_shared_key(data["text"]["A"])
        print(current_dh)
        msg_obj = MessageObj(
            current_dh.public_info(), BOB, ALICE, mitm_url, stage + 0.1
        )
    send(msg_obj)


@app.route("/receive", methods=["POST"])
def receive_message():
    data = request.json
    print(BOB, "Received:", data["text"])
    handle_response(data)
    return jsonify({BOB: "Message received"})


if __name__ == "__main__":
    app.run(port=bob_port, debug=True)
