#!/usr/bin/env python3
"""
Environment variables loader for QCMD.

This module provides functionality to load environment variables from 
.env files and access application settings.
"""
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional

# Default values in case .env file is not found
DEFAULT_VERSION = "1.0.16"
DEFAULT_OLLAMA_API = "http://127.0.0.1:11434/api"
DEFAULT_TIMEOUT = 30
DEFAULT_MODEL = "qwen2.5-coder"
DEFAULT_TEMPERATURE = 0.2

# Find the project root directory (where .env file should be)
def get_project_root() -> Path:
    """Get the path to the project root directory."""
    # Start from the current file's directory
    current_dir = Path(__file__).parent.absolute()
    
    # Go up the directory tree until we find the root
    # (typically where .env or pyproject.toml is located)
    max_levels = 5  # Limit the search to 5 levels up to avoid infinite loop
    for _ in range(max_levels):
        if (current_dir / ".env").exists() or (current_dir / "pyproject.toml").exists():
            return current_dir
        parent = current_dir.parent
        if parent == current_dir:  # Reached filesystem root
            break
        current_dir = parent
        
    # If we didn't find the root, return the directory containing this file's parent
    return Path(__file__).parent.parent.parent.absolute()

def load_env_file() -> Dict[str, str]:
    """
    Load environment variables from .env file.
    
    Returns:
        Dictionary of environment variables from .env file
    """
    env_vars = {}
    env_path = get_project_root() / ".env"
    
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                    
                # Parse variable assignment
                match = re.match(r'^([A-Za-z0-9_]+)=(.*)$', line)
                if match:
                    key, value = match.groups()
                    # Remove quotes if present
                    value = value.strip('\'"')
                    env_vars[key] = value
    
    return env_vars

# Load environment variables when module is imported
_env_vars = load_env_file()

def get_env(key: str, default: Any = None) -> Any:
    """
    Get environment variable, with the following precedence:
    1. OS environment variable
    2. .env file variable
    3. Provided default value
    
    Args:
        key: Environment variable name
        default: Default value if not found
        
    Returns:
        Value of environment variable or default
    """
    # Check OS environment first
    value = os.environ.get(key)
    if value is not None:
        return value
        
    # Then check .env file
    if key in _env_vars:
        return _env_vars[key]
        
    # Fall back to default
    return default

# Application version
def get_version() -> str:
    """Get the application version."""
    return get_env("QCMD_VERSION", DEFAULT_VERSION)

# API settings
def get_ollama_api_url() -> str:
    """Get the Ollama API URL."""
    return get_env("OLLAMA_API_URL", DEFAULT_OLLAMA_API)

def get_request_timeout() -> int:
    """Get the request timeout in seconds."""
    timeout = get_env("REQUEST_TIMEOUT", DEFAULT_TIMEOUT)
    try:
        return int(timeout)
    except (ValueError, TypeError):
        return DEFAULT_TIMEOUT

# Model settings
def get_default_model() -> str:
    """Get the default model name."""
    return get_env("DEFAULT_MODEL", DEFAULT_MODEL)

def get_default_temperature() -> float:
    """Get the default temperature."""
    temp = get_env("DEFAULT_TEMPERATURE", DEFAULT_TEMPERATURE)
    try:
        return float(temp)
    except (ValueError, TypeError):
        return DEFAULT_TEMPERATURE 