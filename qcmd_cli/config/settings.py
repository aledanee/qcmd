#!/usr/bin/env python3
"""
Configuration settings functionality for QCMD.
"""
import os
import json
import sys
import shlex
from typing import Dict, Any, Optional, List

# Import from UI module
from ..ui.display import Colors

# Default settings
DEFAULT_MODEL = "qwen2.5-coder:0.5b"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_CHECK_UPDATES = True

# Default UI settings
DEFAULT_UI_SETTINGS = {
    "show_iraq_banner": True,
    "show_progress_bar": True,
    "compact_mode": False,
    "banner_font": "slant",
    "progress_delay": 0.05
}

# Configuration paths
CONFIG_DIR = os.path.expanduser("~/.qcmd")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

def load_config() -> Dict:
    """
    Load configuration from file
    
    Returns:
        Dictionary containing configuration values
    """
    config = {
        'model': DEFAULT_MODEL,
        'temperature': DEFAULT_TEMPERATURE,
        'max_attempts': DEFAULT_MAX_ATTEMPTS,
        'check_updates': DEFAULT_CHECK_UPDATES,
        'ui': DEFAULT_UI_SETTINGS,
        'colors': Colors.get_all_colors()
    }
    
    # Create config directory if it doesn't exist
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    # If config file exists, load it and update defaults
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                user_config = json.load(f)
                
            # Update top-level keys
            for key, value in user_config.items():
                if key in config and isinstance(config[key], dict) and isinstance(value, dict):
                    # For nested dictionaries, update each sub-key
                    config[key].update(value)
                else:
                    # For top-level keys, replace the value
                    config[key] = value
                    
            # Apply colors from config
            Colors.load_from_config(config)
        
        except (json.JSONDecodeError, IOError) as e:
            print(f"{Colors.YELLOW}Error loading config: {e}{Colors.END}")
            print(f"{Colors.YELLOW}Using default configuration.{Colors.END}")
    
    return config

def save_config(config: Dict) -> None:
    """
    Save configuration to file
    
    Args:
        config: Dictionary containing configuration values
    """
    try:
        # Create config directory if it doesn't exist
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        
        # Save as JSON
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"{Colors.YELLOW}Error saving configuration: {e}{Colors.END}", file=sys.stderr)

def handle_config_command(args):
    """Handle configuration subcommands"""
    config = load_config()
    
    # Split the command into parts, handling quoted values correctly
    parts = shlex.split(args) if args else []
    
    if not parts:
        # Display current configuration
        print(f"\n{Colors.BOLD}Current Configuration:{Colors.END}")
        print(f"  {Colors.CYAN}model: {Colors.END}{config.get('model', DEFAULT_MODEL)}")
        print(f"  {Colors.CYAN}temperature: {Colors.END}{config.get('temperature', DEFAULT_TEMPERATURE)}")
        print(f"  {Colors.CYAN}max_attempts: {Colors.END}{config.get('max_attempts', DEFAULT_MAX_ATTEMPTS)}")
        print(f"  {Colors.CYAN}check_updates: {Colors.END}{config.get('check_updates', DEFAULT_CHECK_UPDATES)}")
        
        print(f"\n{Colors.BOLD}UI Settings:{Colors.END}")
        ui_config = config.get('ui', {})
        print(f"  {Colors.CYAN}show_iraq_banner: {Colors.END}{ui_config.get('show_iraq_banner', True)}")
        print(f"  {Colors.CYAN}show_progress_bar: {Colors.END}{ui_config.get('show_progress_bar', True)}")
        print(f"  {Colors.CYAN}compact_mode: {Colors.END}{ui_config.get('compact_mode', False)}")
        print(f"  {Colors.CYAN}banner_font: {Colors.END}{ui_config.get('banner_font', 'slant')}")
        print(f"  {Colors.CYAN}progress_delay: {Colors.END}{ui_config.get('progress_delay', 0.05)}")
        
        print(f"\n{Colors.BOLD}Color Settings:{Colors.END}")
        for color_name, color_value in config.get('colors', {}).items():
            print(f"  {getattr(Colors, color_name, Colors.CYAN)}{color_name}: {color_value}{Colors.END}")
            
        return
    
    if parts[0] == "reset":
        # Reset to default configuration
        os.remove(CONFIG_FILE) if os.path.exists(CONFIG_FILE) else None
        Colors.reset_to_defaults()
        print(f"{Colors.GREEN}Configuration reset to defaults.{Colors.END}")
        return
        
    elif parts[0] == "set" and len(parts) >= 3:
        key = parts[1]
        value = parts[2]
        
        # Handle nested keys (ui.property or colors.property)
        if "." in key:
            main_key, sub_key = key.split(".", 1)
            
            # Make sure the main section exists
            if main_key not in config:
                config[main_key] = {}
                
            # Convert to appropriate type
            if value.lower() in ('true', 'yes', 'y', 'on'):
                config[main_key][sub_key] = True
            elif value.lower() in ('false', 'no', 'n', 'off'):
                config[main_key][sub_key] = False
            elif value.isdigit():
                config[main_key][sub_key] = int(value)
            elif value.replace('.', '', 1).isdigit() and value.count('.') <= 1:
                config[main_key][sub_key] = float(value)
            else:
                config[main_key][sub_key] = value
                
            print(f"{Colors.GREEN}Setting {main_key}.{sub_key} set to {config[main_key][sub_key]}{Colors.END}")
            
            # Handle special case for colors
            if main_key == 'colors' and hasattr(Colors, sub_key.upper()):
                Colors.load_from_config(config)
                print(f"{Colors.GREEN}Color applied!{Colors.END}")
                
        else:
            # Regular top-level key
            if key in config:
                # Convert value to appropriate type
                if value.lower() in ('true', 'yes', 'y', 'on'):
                    config[key] = True
                elif value.lower() in ('false', 'no', 'n', 'off'):
                    config[key] = False
                elif value.replace('.', '', 1).isdigit() and value.count('.') <= 1:
                    try:
                        if '.' in value:
                            config[key] = float(value)
                        else:
                            config[key] = int(value)
                    except ValueError:
                        print(f"{Colors.RED}Invalid number value: {value}{Colors.END}")
                        return
                else:
                    config[key] = value
                
                print(f"{Colors.GREEN}Setting {key} set to {config[key]}{Colors.END}")
            else:
                print(f"{Colors.RED}Unknown configuration key: {key}{Colors.END}")
                return
        
        # Save the updated configuration
        save_config(config)
    else:
        print(f"{Colors.YELLOW}Usage: /config [set <key> <value> | reset]{Colors.END}")
        print(f"{Colors.YELLOW}For UI settings: /config set ui.show_iraq_banner true{Colors.END}")
        print(f"{Colors.YELLOW}For colors: /config set colors.GREEN '\\033[92m'{Colors.END}")
        print(f"{Colors.YELLOW}Available UI settings: show_iraq_banner, show_progress_bar, compact_mode, banner_font, progress_delay{Colors.END}")

def get_config_path() -> str:
    """
    Get the path to the configuration file.
    
    Returns:
        Path to the configuration file
    """
    return CONFIG_FILE 