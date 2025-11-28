"""Colored logging utilities for the secure communication demo.

This module provides simple colorized print wrappers (green, blue, red)
and a `Logger` class that formats and displays messages exchanged between
Alice, Bob, the MITM, and other components. It also provides a compact
preview helper for large values.
"""

import builtins
from constants import *
from message import MessageObj
from time import sleep


def green_print(*args, **kwargs):
    """Print text in green for readability."""

    def green(text):
        return f"\033[92m{text}\033[0m"

    colored = " ".join(green(str(arg)) for arg in args)
    builtins.print(colored, **kwargs)


def blue_print(*args, **kwargs):
    """Print text in blue for readability."""

    def blue(text):
        return f"\033[94m{text}\033[0m"

    colored = " ".join(blue(str(arg)) for arg in args)
    builtins.print(colored, **kwargs)


def red_print(*args, **kwargs):
    """Print text in red for highlighting errors or warnings."""

    def red(body):
        return f"\033[91m{body}\033[0m"

    colored = " ".join(red(str(arg)) for arg in args)
    builtins.print(colored, **kwargs)


def preview(obj):
    """Return a shortened preview of an object for logging.

    Large numbers or long byte strings can overwhelm the console.
    This helper trims values to 15 characters, adding '...' if needed.
    """
    text = str(obj)
    return text if len(text) <= 15 else text[:15] + "..."


class Logger:
    """Simple colorized logger used by Alice, Bob, and other servers.

    The logger writes structured outgoing and incoming message information,
    along with Diffie–Hellman state previews. Colors are chosen based on
    which participant is doing the logging (green for Alice, blue for Bob,
    red for MITM, etc.).
    """

    def __init__(self, name, color):
        """Initialise the logger with a participant name and color theme.

        Args:
            name: The identity of the participant (e.g., "Alice").
            color: A constant selecting green, blue, or red print functions.
        """
        if color == GREEN:
            self.log = green_print
        elif color == BLUE:
            self.log = blue_print
        elif color == RED:
            self.log = red_print
        self.name = name

    def log(self, message):
        """Placeholder overwritten in __init__ with a color print function."""
        self.log.append(message)

    def log_outgoing_message(self, msg_obj: MessageObj):
        """Pretty-print a structured view of an outgoing message."""
        self.log("*" * 40)
        self.log(f"[{msg_obj.from_name}] Sending Message:")
        for key, value in msg_obj.__dict__.items():
            if isinstance(value, dict):
                self.log(key + ":")
                for subkey, subvalue in value.items():
                    self.log(f"   {subkey}: {preview(subvalue)}")
            else:
                # Skip internal routing fields
                if key in ("to_url", "stage", "method"):
                    continue
                # Skip empty certificate/signature fields
                if (key == "cert" and not value) or (key == "signature" and not value):
                    continue
                self.log(f"{key}: {preview(value)}")

    def log_incoming_message(self, data):
        """Pretty-print a structured view of an incoming message."""
        self.log("*" * 40)
        self.log(f"[{self.name}] Received Message:")
        for key, value in data.items():
            if isinstance(value, dict):
                self.log(key + ":")
                for subkey, subvalue in value.items():
                    self.log(f"   {subkey}: {preview(subvalue)}")
            else:
                # Skip routing/meta fields
                if key in ("to_url", "stage", "method"):
                    continue
                # Skip empty certificate/signature fields
                if (key == "cert" and not value) or (key == "signature" and not value):
                    continue
                self.log(f"{key}: {preview(value)}")

    def log_dh_state(self, dh_state):
        """Log the internal values of a Diffie–Hellman state object."""
        self.log("*" * 40)
        self.log(f"[{self.name}] Diffie-Hellman State:")
        for key, value in dh_state.__dict__.items():
            self.log(f"{key}: {preview(value)}")

    def new_exchange(self):
        """Add spacing in the log before the start of a new exchange."""
        self.log("\n" * 3)
