import os
from pathlib import Path
from typing import Any, Dict
import yaml
from dotenv import load_dotenv

# Automatically load .env if available
load_dotenv()

_CACHED_CONFIG: Dict[str, Any] = {}

def get_project_root() -> Path:
    """Return the project root path."""
    return Path(__file__).resolve().parent.parent.parent

def get_config(reload: bool = False) -> Dict[str, Any]:
    """Load settings.yaml configuration as a dictionary."""
    global _CACHED_CONFIG
    if _CACHED_CONFIG and not reload:
        return _CACHED_CONFIG

    root = get_project_root()
    settings_path = root / "config" / "settings.yaml"

    if settings_path.exists():
        with open(settings_path, "r", encoding="utf-8") as f:
            _CACHED_CONFIG = yaml.safe_load(f) or {}
    else:
        _CACHED_CONFIG = {}

    return _CACHED_CONFIG
