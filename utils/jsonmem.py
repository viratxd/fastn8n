import json
from pathlib import Path
from config import PLUGINS_JSON

def load_plugins_memory():
    """Load plugins data from JSON file, create if missing, handle empty/invalid JSON."""
    plugins_file = Path(PLUGINS_JSON)
    if not plugins_file.exists():
        # Agar file nahi hai to empty JSON banao
        with open(plugins_file, "w") as f:
            json.dump({}, f)
        return {}
    
    try:
        with open(plugins_file, "r") as f:
            content = f.read().strip()  # File ka content padho aur whitespace hatao
            if not content:  # Agar file empty hai
                return {}
            return json.loads(content)  # Valid JSON parse karo
    except json.JSONDecodeError:
        # Agar JSON invalid hai, to default empty dict return karo aur file ko reset karo
        with open(plugins_file, "w") as f:
            json.dump({}, f)
        return {}

def save_plugins_memory(data):
    """Save plugins data to JSON file."""
    with open(PLUGINS_JSON, "w") as f:
        json.dump(data, f, indent=4)