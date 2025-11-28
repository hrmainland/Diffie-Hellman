import json
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name("network_config.json")

# Load the network configuration
def load_config():
    with CONFIG_PATH.open() as f:
        return json.load(f)
