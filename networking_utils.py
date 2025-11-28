import requests
from message import MessageObj
from constants import *
from time import sleep
import json


def send(msg_obj: MessageObj):
    """
    Send a message via HTTP POST.

    Returns:
        Response object on success, None on failure
    """
    if msg_obj.stage < FULL_AUTH_DH_STAGE and NETWORKING_DELAY_ON:
        sleep(1.5)
    if msg_obj.method == "POST":
        payload = msg_obj.__dict__
        try:
            response = requests.post(msg_obj.to_url, json=payload, timeout=10)
            return response
        except requests.exceptions.Timeout:
            return None
        except requests.exceptions.ConnectionError:
            return None
        except Exception:
            return None
    else:
        raise Exception("Unsupported method in send function")
