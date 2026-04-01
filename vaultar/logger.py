import json
import logging
import os
from datetime import datetime
from pathlib import Path

LOG_DIR = Path.home() / ".cache" / "vaultar"
LOG_FILE = LOG_DIR / "vaultar.log"
JSON_LOG_FILE = LOG_DIR / "vaultar.json"

def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Text logging
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

def log_event(event_type, details):
    """Logs a structured event to both text and JSON files."""
    setup_logging()
    
    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "event_type": event_type,
        **details
    }
    
    # Log to text file
    logging.info(f"{event_type}: {details}")
    
    # Log to JSON file
    logs = []
    if JSON_LOG_FILE.exists():
        try:
            with open(JSON_LOG_FILE, "r") as f:
                logs = json.load(f)
        except json.JSONDecodeError:
            logs = []
            
    logs.append(log_entry)
    
    with open(JSON_LOG_FILE, "w") as f:
        json.dump(logs, f, indent=4)
