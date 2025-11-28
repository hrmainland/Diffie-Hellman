import builtins
from constants import *
from message import MessageObj
from time import sleep


def green_print(*args, **kwargs):
    def green(text):
        return f"\033[92m{text}\033[0m"

    colored = " ".join(green(str(arg)) for arg in args)
    builtins.print(colored, **kwargs)


def blue_print(*args, **kwargs):
    def blue(text):
        return f"\033[94m{text}\033[0m"

    colored = " ".join(blue(str(arg)) for arg in args)
    builtins.print(colored, **kwargs)


def red_print(*args, **kwargs):
    def red(body):
        return f"\033[91m{body}\033[0m"

    colored = " ".join(red(str(arg)) for arg in args)
    builtins.print(colored, **kwargs)


def preview(obj):
    text = str(obj)
    return text if len(text) <= 15 else text[:15] + "..."


class Logger:
    def __init__(self, name, color):
        if color == GREEN:
            self.log = green_print
        elif color == BLUE:
            self.log = blue_print
        elif color == RED:
            self.log = red_print
        self.name = name

    def log(self, message):
        self.log.append(message)

    def log_outgoing_message(self, msg_obj: MessageObj):
        self.log("*" * 40)
        self.log(f"[{msg_obj.from_name}] Sending Message:")
        for key, value in msg_obj.__dict__.items():
            if isinstance(value, dict):
                self.log(key + ":")
                for subkey, subvalue in value.items():
                    self.log(f"   {subkey}: {preview(subvalue)}")
            else:
                if key in ("to_url", "stage", "method"):
                    continue
                if (key == "cert" and not value) or (key == "signature" and not value):
                    continue
                self.log(f"{key}: {preview(value)}")
        # self.log("*" * 40)

    def log_incoming_message(self, data):
        self.log("*" * 40)
        self.log(f"[{self.name}] Received Message:")
        for key, value in data.items():
            if isinstance(value, dict):
                self.log(key + ":")
                for subkey, subvalue in value.items():
                    self.log(f"   {subkey}: {preview(subvalue)}")
            else:
                if key in ("to_url", "stage", "method"):
                    continue
                if (key == "cert" and not value) or (key == "signature" and not value):
                    continue
                self.log(f"{key}: {preview(value)}")
        # self.log("*" * 40)

    def log_dh_state(self, dh_state):
        self.log("*" * 40)
        self.log(f"[{self.name}] Diffie-Hellman State:")
        for key, value in dh_state.__dict__.items():
            self.log(f"{key}: {preview(value)}")
        # self.log("*" * 40)

    def new_exchange(self):
        self.log("\n" * 3)
        # self.log("*" * 40)
