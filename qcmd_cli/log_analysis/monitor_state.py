"""Monitor state management for log analysis."""

import os
import json
from typing import Dict, Any
from ..ui.display import Colors

ACTIVE_MONITORS_FILE = '/tmp/active_log_monitors.json'

# Global dictionary to track active log monitors
active_log_monitors: Dict[int, str] = {}

def get_active_monitors() -> Dict[int, str]:
    """Get the active monitor dictionary."""
    return active_log_monitors

def save_active_monitors() -> None:
    """Save the active log monitors to a JSON file."""
    try:
        with open(ACTIVE_MONITORS_FILE, 'w') as f:
            json.dump(active_log_monitors, f)
    except Exception as e:
        print(f"{Colors.RED}Error saving active log monitors: {e}{Colors.END}")

def load_active_monitors() -> None:
    """Load the active log monitors from a JSON file."""
    try:
        if os.path.exists(ACTIVE_MONITORS_FILE):
            with open(ACTIVE_MONITORS_FILE, 'r') as f:
                active_log_monitors.clear()
                active_log_monitors.update(json.load(f))
    except Exception as e:
        print(f"{Colors.RED}Error loading active log monitors: {e}{Colors.END}")
