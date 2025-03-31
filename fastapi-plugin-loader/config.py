import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Configurable paths
PLUGINS_DIR = os.getenv("PLUGINS_DIR", str(BASE_DIR / "plugins"))
SHARED_VENV_DIR = os.getenv("SHARED_VENV_DIR", str(BASE_DIR / "shared_venv"))
PLUGINS_JSON = os.getenv("PLUGINS_JSON", str(BASE_DIR / "plugins.json"))