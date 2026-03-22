import json
import re
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "terminalboard"
CONFIG_FILE = CONFIG_DIR / "config.json"

MAX_PROFILES = 50
MAX_PROFILE_NAME_LEN = 50
_SAFE_NAME_RE = re.compile(r'^[\w \-\.]+$')

PROFILE_DEFAULTS = {
    "grid_cols": 3,
    "grid_rows": 3,
    "buttons": {},
}


def sanitize_profile_name(name: str) -> str:
    """Validate and clean a profile name. Raises ValueError on bad input."""
    name = name.strip()
    if not name:
        raise ValueError("Profile name cannot be empty.")
    if len(name) > MAX_PROFILE_NAME_LEN:
        raise ValueError(
            f"Profile name must be {MAX_PROFILE_NAME_LEN} characters or fewer.")
    if not _SAFE_NAME_RE.match(name):
        raise ValueError(
            "Profile name may only contain letters, numbers, spaces, "
            "hyphens, dots, and underscores.")
    return name


def _migrate(data: dict) -> dict:
    """Move flat grid_cols/grid_rows/buttons into a 'Default' profile."""
    if "profiles" in data:
        return data
    profile = {}
    for key in ("grid_cols", "grid_rows", "buttons"):
        if key in data:
            profile[key] = data.pop(key)
    for key, val in PROFILE_DEFAULTS.items():
        profile.setdefault(key, val.copy() if isinstance(val, dict) else val)
    data["profiles"] = {"Default": profile}
    data.setdefault("active_profile", "Default")
    return data


def load() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
            data = _migrate(data)
            data.setdefault("theme", "auto")
            data.setdefault("active_profile", "Default")
            data.setdefault("profiles", {"Default": {**PROFILE_DEFAULTS}})
            if data["active_profile"] not in data["profiles"]:
                data["active_profile"] = next(iter(data["profiles"]))
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "theme": "auto",
        "active_profile": "Default",
        "profiles": {"Default": {**PROFILE_DEFAULTS}},
    }


def save(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(cfg, f, indent=2)
    tmp.replace(CONFIG_FILE)


def active_profile(cfg: dict) -> dict:
    """Return the active profile's data dict (mutable reference)."""
    name = cfg.get("active_profile", "Default")
    profiles = cfg.get("profiles", {})
    if name not in profiles:
        name = next(iter(profiles), "Default")
        cfg["active_profile"] = name
    profile = profiles.get(name)
    if profile is None:
        profile = {**PROFILE_DEFAULTS}
        profiles[name] = profile
    return profile
