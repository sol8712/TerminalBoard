import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "terminalboard"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "grid_cols": 3,
    "grid_rows": 3,
    "theme": "auto",
    "buttons": {},
}


def load() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
            for key, val in DEFAULTS.items():
                data.setdefault(key, val)
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULTS.copy()


def save(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # Write to a temp file then rename for atomicity
    tmp = CONFIG_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(cfg, f, indent=2)
    tmp.replace(CONFIG_FILE)
