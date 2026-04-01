import os
import configparser
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "vaultar.conf"

DEFAULT_CONFIG_CONTENT = """# Vaultar Configuration File
# This file defines the default behavior for the vaultar CLI.

[defaults]
# Default compression type: tar, tar.gz, tar.zst, zip
compression = tar.gz

# Default encryption method: senha, chave
encryption_method = senha

# Default verbose mode: s, N
verbose = N

# Default backup destination
# destination = /path/to/backup/folder
"""

def get_config():
    config = configparser.ConfigParser()
    if DEFAULT_CONFIG_PATH.exists():
        config.read(DEFAULT_CONFIG_PATH)
    else:
        # Create default config if it doesn't exist
        DEFAULT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DEFAULT_CONFIG_PATH, "w") as f:
            f.write(DEFAULT_CONFIG_CONTENT)
        config.read_string(DEFAULT_CONFIG_CONTENT)
    return config

def get_default(key, fallback=None):
    config = get_config()
    return config.get("defaults", key, fallback=fallback)
