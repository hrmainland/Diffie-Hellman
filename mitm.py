from flask import Flask, request, jsonify
from config_utils import load_config
import networking_utils
from message import MessageObj
from constants import *
from diffie_hellman_utils import *
from state_objects import *
import builtins
import time

app = Flask(__name__)
config = load_config()

alice_receive_url = config[ALICE]["base_url"] + "/receive"
bob_receive_url = config[BOB]["base_url"] + "/receive"

mitm_port = int(config[MITM]["base_url"].split(":")[-1])

shared_dh = None
alice_dh = None
bob_dh = None


def send(msg_obj: MessageObj):
    print(f"[MITM] Sending:", msg_obj.text)
    return networking_utils.send(msg_obj)


def print(*args, **kwargs):
    def red(text):
        return f"\033[91m{text}\033[0m"

    colored = " ".join(red(str(arg)) for arg in args)
    builtins.print(colored, **kwargs)


def simple_relay(data):

    to_name = data.get("to_name")

    if to_name == ALICE:
        target_url = alice_receive_url
    elif to_name == BOB:
        target_url = bob_receive_url
    else:
        raise Exception("Unknown recipient")

    msg_obj = MessageObj(
        data["text"],
        data.get("from_name"),
        to_name,
        target_url,
        data.get("stage"),
    )

    downstream_resp = send(msg_obj)

    return jsonify(
        {
            "MITM": "Relayed",
            "downstream_status": downstream_resp.status_code,
            "downstream_body": downstream_resp.json(),
        }
    )


@app.route("/receive", methods=["POST"])
def relay():
    global shared_dh
    global alice_dh
    global bob_dh

    data = request.json
    stage = int(data["stage"])
    print("[MITM] Incoming:", data["text"])

    if stage < 3:
        return simple_relay(data)

    elif stage < 5:
        if data["from_name"] == ALICE:
            shared_dh = DiffieHellmanState()
            shared_dh.set_values(data["text"]["p"], data["text"]["g"])
            shared_dh.set_A(data["text"]["A"])
        else:
            shared_dh.set_B(data["text"]["A"])
            print("Generating...")
            secrets = brute_force_dlp(
                shared_dh.g, shared_dh.p, shared_dh.A, shared_dh.B
            )
            if secrets:
                shared_dh.generate_shared_key_from_secrets(secrets[0], secrets[1])
                print("The shared key is:", shared_dh.K)
            else:
                print("Timeout no secrets found")
        return simple_relay(data)

    elif stage == 5:
        if data["from_name"] == ALICE:
            alice_dh = DiffieHellmanState()
            alice_dh.set_values(data["text"]["p"], data["text"]["g"])
            alice_dh.generate_keys()
            alice_dh.set_shared_key(data["text"]["A"])
            print(alice_dh)
            msg_obj = MessageObj(
                alice_dh.public_info(), BOB, ALICE, alice_receive_url, stage + 0.1
            )
            send(msg_obj)
            return jsonify(
                {
                    "MITM": "Relayed",
                    "downstream_status": 200,
                }
            )

        else:
            bob_dh = DiffieHellmanState()
            bob_dh.set_values(data["text"]["p"], data["text"]["g"])
            bob_dh.set_A(data["text"]["A"])


if __name__ == "__main__":
    app.run(port=mitm_port, debug=True)
