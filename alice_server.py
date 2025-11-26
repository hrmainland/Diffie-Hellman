from flask import Flask, request, jsonify
from config_utils import load_config
import networking_utils
from message import MessageObj
import builtins
from signed_fields import *
from constants import *
from state_objects import *
from crypto_utils import *
from server_utils import populate_rsa, build_dh_fields, get_signature, request_certificate_from_ca
from ca_server import ca_public_key
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
ca_url = config[CA]["base_url"] + "/request"

current_dh = None
current_rsa = None


def send(msg_obj: MessageObj):
    print(f"[{msg_obj.from_name}] Sending:", msg_obj.body)
    if msg_obj.signature is not None:
        print(f"[{msg_obj.from_name}] Signature:", msg_obj.signature[:5] + "...")

    return networking_utils.send(msg_obj)


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


def send_authenticated_dh_message(dh, rsa_state, stage, dest_url):
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
    dh_fields = build_dh_fields(NAME, dh, nonce)
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

    send(msg_obj)




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
        dh_fields = build_dh_fields(NAME, current_dh, nonce)
        message_bytes = dh_fields.to_bytes()
        sig = get_signature(message_bytes, current_rsa)

        msg_obj = MessageObj(
            dh_fields.serializable(), ALICE, BOB, mitm_url, stage, sig.hex()
        )

        if VERBOSE:
            bits = "".join(f"{b:08b}" for b in message_bytes)
            print(bits)

    elif stage == 8:
        # Step 1: Generate DH values
        current_dh = populate_dh(is_weak_dh)

        # Step 2: Generate RSA key pair and obtain certificate from CA
        current_rsa = populate_rsa()
        current_rsa.cert = request_certificate_from_ca(
            name=NAME,
            rsa_state=current_rsa,
            ca_url=ca_url,
            stage=stage,
            from_name=ALICE
        )

        if current_rsa.cert is None:
            return

        # Step 3: Send authenticated DH message to Bob
        send_authenticated_dh_message(current_dh, current_rsa, stage, mitm_url)
        return

    send(msg_obj)


def handle_response(data):
    """
    Handles responses from Bob and MITM
    """
    global current_dh
    stage = float(data["stage"])
    if stage == 0:
        return
    elif 1 <= stage < 2:
        return
    # stages 2-5 all DH
    elif 2 <= stage < 6:
        current_dh.set_shared_key(data["body"]["A"])
        print(current_dh)
        return
    # stages 6-7 demo signatures
    elif 6 <= stage < 8:
        return
    # stage 8.1 - Bob's response with certificate
    elif 8 <= stage < 9:
        # Verify Bob's signature and certificate
        sig_valid = verify_dh_signature(data, ca_public_key)
        if not sig_valid:
            print("Rejecting Bob's message due to invalid signature or certificate")
            return

        # If verification passes, complete DH key exchange
        current_dh.set_shared_key(data["body"]["A"])
        print(current_dh)
        print("Authenticated key exchange completed successfully!")
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
