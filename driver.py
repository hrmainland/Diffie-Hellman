"""
Driver code for the project.
Accepts a stage number as an argument, defaults to 0 if not provided.
Sends the initial message to the /begin endpoint of the Alice server.
"""

import requests
import sys

args = sys.argv[1:]


def begin(stage):
    """Sends the initial message to the /begin endpoint of the Alice server.

    Args:
        stage (str): the stage to execute
    """
    url = "http://127.0.0.1:5001/begin"
    payload = {"stage": stage}
    requests.post(url, json=payload)


if __name__ == "__main__":
    stage = 0 if not args else int(args[0])
    begin(stage)
