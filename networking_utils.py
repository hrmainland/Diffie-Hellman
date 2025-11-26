import requests
from message import MessageObj
import json


def send(msg_obj: MessageObj):
    if msg_obj.method == "POST":
        payload = msg_obj.__dict__
        response = requests.post(msg_obj.to_url, json=payload)
    else:
        raise Exception("Unsupported method in send function")
    return response
