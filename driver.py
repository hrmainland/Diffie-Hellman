import requests
import json
import sys

args = sys.argv[1:]


def begin(stage):
    url = "http://127.0.0.1:5001/begin"
    payload = {"stage": stage}
    response = requests.post(url, json=payload)


if __name__ == "__main__":
    stage = 0 if not args else int(args[0])
    begin(stage)
