#!/usr/bin/env python3
"""
qcmd - A simple command-line tool that generates shell commands using Qwen2.5-Coder via Ollama.

Version: 1.0.0
Copyright (c) 2024
License: MIT
"""

import argparse
import json
import subprocess
import sys
import requests
import os
import textwrap
import tempfile
import readline
import threading
import time
import re
import configparser
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
import shutil
import shlex
import platform

try:
    # For Python 3.8+
    from importlib.metadata import version as get_version
    try:
        __version__ = get_version("ibrahimiq-qcmd")
    except Exception:
        # Use version from __init__.py
        from qcmd_cli import __version__
except ImportError:
    # Fallback for older Python versions
    try:
        import pkg_resources
        __version__ = pkg_resources.get_distribution("ibrahimiq-qcmd").version
    except Exception:
        # Use version from __init__.py
        from qcmd_cli import __version__

# Ollama API settings
OLLAMA_API = "http://127.0.0.1:11434/api"
DEFAULT_MODEL = "qwen2.5-coder:0.5b"

# Global variables
CONFIG_DIR = os.path.expanduser("~/.qcmd")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
HISTORY_FILE = os.path.join(CONFIG_DIR, "history.txt")
MAX_HISTORY = 1000  # Maximum number of history entries to keep
REQUEST_TIMEOUT = 30  # Timeout for API requests in seconds
LOG_CACHE_FILE = os.path.join(CONFIG_DIR, "log_cache.json")
LOG_CACHE_EXPIRY = 3600  # Cache expires after 1 hour (in seconds)
MONITORS_FILE = os.path.join(CONFIG_DIR, "active_monitors.json")
SESSIONS_FILE = os.path.join(CONFIG_DIR, "sessions.json")

# Additional dangerous patterns for improved detection
DANGEROUS_PATTERNS = [
    # File system operations
    "rm -rf", "rm -r /", "rm -f /", "rmdir /", "shred -uz", 
    "mkfs", "dd if=/dev/zero", "format", "fdisk", "mkswap",
    # Disk operations
    "> /dev/sd", "of=/dev/sd", "dd of=/dev", 
    # Network-dangerous
    ":(){ :|:& };:", ":(){:|:&};:", "fork bomb", "while true", "dd if=/dev/random of=/dev/port",
    # Permission changes
    "chmod -R 777 /", "chmod 777 /", "chown -R", "chmod 000", 
    # File moves/redirections
    "mv /* /dev/null", "> /dev/null", "2>&1",
    # System commands
    "halt", "shutdown", "poweroff", "reboot", "init 0", "init 6",
    # User management
    "userdel -r root", "passwd root", "deluser --remove-home"
]

# Terminal colors for better output
class Colors:
    # Default color values
    _DEFAULTS = {
        'HEADER': '\033[95m',
        'BLUE': '\033[94m',
        'CYAN': '\033[96m',
        'GREEN': '\033[92m',
        'YELLOW': '\033[93m',
        'RED': '\033[91m',
        'WHITE': '\033[97m',
        'BLACK': '\033[30;47m',  # Black text on white background
        'BOLD': '\033[1m',
        'UNDERLINE': '\033[4m',
        'END': '\033[0m'
    }
    
    # Class variables with default values
    HEADER = _DEFAULTS['HEADER']
    BLUE = _DEFAULTS['BLUE']
    CYAN = _DEFAULTS['CYAN']
    GREEN = _DEFAULTS['GREEN']
    YELLOW = _DEFAULTS['YELLOW']
    RED = _DEFAULTS['RED']
    WHITE = _DEFAULTS['WHITE']
    BLACK = _DEFAULTS['BLACK']
    BOLD = _DEFAULTS['BOLD']
    UNDERLINE = _DEFAULTS['UNDERLINE']
    END = _DEFAULTS['END']
    
    @classmethod
    def load_from_config(cls, config):
        """Load colors from configuration"""
        if 'colors' in config:
            for color_name, color_value in config['colors'].items():
                if hasattr(cls, color_name.upper()) and color_value:
                    setattr(cls, color_name.upper(), color_value)
    
    @classmethod
    def reset_to_defaults(cls):
        """Reset colors to default values"""
        for color_name, color_value in cls._DEFAULTS.items():
            setattr(cls, color_name, color_value)
    
    @classmethod
    def get_all_colors(cls):
        """Get all color values as a dictionary"""
        return {
            'HEADER': cls.HEADER,
            'BLUE': cls.BLUE,
            'CYAN': cls.CYAN, 
            'GREEN': cls.GREEN,
            'YELLOW': cls.YELLOW,
            'RED': cls.RED,
            'WHITE': cls.WHITE,
            'BLACK': cls.BLACK,
            'BOLD': cls.BOLD,
            'UNDERLINE': cls.UNDERLINE,
            'END': cls.END
        }

# Global variables to track active processes
ACTIVE_LOG_MONITORS = {}
ACTIVE_SESSIONS = {}

def save_monitors(monitors):
    """Save active monitors to file."""
    monitors_file = os.path.join(CONFIG_DIR, "active_monitors.json")
    os.makedirs(os.path.dirname(monitors_file), exist_ok=True)
    try:
        with open(monitors_file, 'w') as f:
            json.dump(monitors, f)
    except Exception as e:
        print(f"{Colors.YELLOW}Could not save active monitors: {e}{Colors.END}", file=sys.stderr)

def load_monitors():
    """Load active monitors from file."""
    monitors_file = os.path.join(CONFIG_DIR, "active_monitors.json")
    if os.path.exists(monitors_file):
        try:
            with open(monitors_file, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def cleanup_stale_monitors():
    """Clean up monitors with non-existent processes."""
    monitors = load_monitors()
    updated = {}
    
    for monitor_id, info in monitors.items():
        pid = info.get("pid")
        if pid is None:
            continue
            
        # Check if process is still running
        try:
            os.kill(int(pid), 0)  # Signal 0 doesn't kill the process, just checks if it exists
            # Process exists, keep the monitor
            updated[monitor_id] = info
        except (OSError, ValueError):
            # Process doesn't exist or invalid PID, discard the monitor
            pass
    
    save_monitors(updated)
    return updated

def save_to_history(prompt: str) -> None:
    """
    Save a command prompt to the history file
    
    Args:
        prompt: The command prompt to save
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        
        # Read existing history
        history = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    history = [line.strip() for line in f.readlines()]
            except UnicodeDecodeError:
                # If UTF-8 fails, try with a more permissive encoding
                with open(HISTORY_FILE, 'r', encoding='latin-1') as f:
                    history = [line.strip() for line in f.readlines()]
        
        # Add new entry with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history.append(f"{timestamp} | {prompt}")
        
        # Trim history if needed
        if len(history) > MAX_HISTORY:
            history = history[-MAX_HISTORY:]
        
        # Write back to file
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(history))
    except Exception as e:
        # Don't crash the program if history saving fails
        print(f"{Colors.YELLOW}Could not save to history: {e}{Colors.END}", file=sys.stderr)

def load_history(count: int = 10) -> List[str]:
    """
    Load recent command history
    
    Args:
        count: Number of history entries to load
        
    Returns:
        List of recent command prompts
    """
    try:
        if not os.path.exists(HISTORY_FILE):
            return []
        
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = [line.strip() for line in f.readlines()]
        except UnicodeDecodeError:
            # If UTF-8 fails, try with a more permissive encoding
            with open(HISTORY_FILE, 'r', encoding='latin-1') as f:
                history = [line.strip() for line in f.readlines()]
            
        # Extract just the prompts (remove timestamps)
        prompts = []
        for entry in reversed(history[-count:]):
            parts = entry.split(" | ", 1)
            if len(parts) > 1:
                prompts.append(parts[1])
                
        return prompts
    except Exception as e:
        print(f"{Colors.YELLOW}Could not load history: {e}{Colors.END}", file=sys.stderr)
        return []

def show_history(count: int = 20, search_term: str = None) -> None:
    """
    Display command history with optional search
    
    Args:
        count: Number of history entries to show
        search_term: Optional search term to filter history
    """
    try:
        if not os.path.exists(HISTORY_FILE):
            print(f"{Colors.YELLOW}No command history found.{Colors.END}")
            return
            
        with open(HISTORY_FILE, 'r') as f:
            history = [line.strip() for line in f.readlines()]
        
        if not history:
            print(f"{Colors.YELLOW}No command history found.{Colors.END}")
            return
            
        # Filter history if search term is provided
        if search_term:
            search_term = search_term.lower()
            filtered_history = []
            for entry in history:
                if search_term in entry.lower():
                    filtered_history.append(entry)
            history = filtered_history
            
            if not history:
                print(f"{Colors.YELLOW}No matching history entries found for '{search_term}'.{Colors.END}")
                return
                
            print(f"\n{Colors.GREEN}{Colors.BOLD}Command History matching '{search_term}':{Colors.END}")
        else:
            print(f"\n{Colors.GREEN}{Colors.BOLD}Command History:{Colors.END}")
            
        print(f"{Colors.CYAN}{'#':<4} {'Timestamp':<20} {'Command'}{Colors.END}")
        print("-" * 80)
        
        # Show the most recent entries first, up to the count limit
        for i, entry in enumerate(reversed(history[-count:])):
            idx = len(history) - count + i + 1
            parts = entry.split(" | ", 1)
            if len(parts) > 1:
                timestamp, prompt = parts
                print(f"{i+1:<4} {timestamp:<20} {prompt}")
            else:
                print(f"{i+1:<4} {'Unknown':<20} {entry}")
                
    except Exception as e:
        print(f"{Colors.YELLOW}Could not display history: {e}{Colors.END}", file=sys.stderr)

def generate_command(prompt: str, model: str = DEFAULT_MODEL, temperature: float = 0.2) -> str:
    """
    Generate a shell command from a natural language description.
    
    Args:
        prompt: The natural language description of what command to generate
        model: The model to use for generation
        temperature: Temperature for generation
        
    Returns:
        The generated command as a string
    """
    system_prompt = """You are a command-line expert. Generate a shell command based on the user's request.
Reply with ONLY the command, nothing else - no explanations or markdown."""

    formatted_prompt = f"""Generate a shell command for this request: "{prompt}"

Output only the exact command with no introduction, explanation, or markdown formatting."""
    
    # Get available models for fallback
    available_models = []
    try:
        available_models = list_models()
    except:
        pass
        
    # Try with the specified model first
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            # Prepare the request payload
            payload = {
                "model": model,
                "prompt": formatted_prompt,
                "system": system_prompt,
                "stream": False,
                "temperature": temperature,
            }
            
            if attempt > 0:
                print(f"{Colors.YELLOW}Retry attempt {attempt+1}/{max_retries}...{Colors.END}")
            else:
                print(f"{Colors.BLUE}Generating command with {Colors.BOLD}{model}{Colors.END}{Colors.BLUE}...{Colors.END}")
            
            # Make the API request with timeout
            response = requests.post(f"{OLLAMA_API}/generate", json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            result = response.json()
            
            # Extract the command from the response
            command = result.get("response", "").strip()
            
            # Clean up the command (remove any markdown formatting)
            if command.startswith("```") and "\n" in command:
                # Handle multiline code blocks
                lines = command.split("\n")
                command = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            elif command.startswith("```") and command.endswith("```"):
                # Handle single line code blocks with triple backticks
                command = command[3:-3].strip()
            elif command.startswith("`") and command.endswith("`"):
                # Handle inline code with single backticks
                command = command[1:-1].strip()
                
            return command
                
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                print(f"{Colors.YELLOW}Request timed out. Retrying in {retry_delay} seconds...{Colors.END}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                print(f"{Colors.RED}Error: Request to Ollama API timed out after {REQUEST_TIMEOUT} seconds.{Colors.END}")
                
                # Try fallback if the original model isn't available
                if available_models and model != DEFAULT_MODEL and DEFAULT_MODEL in available_models:
                    print(f"{Colors.YELLOW}Trying with fallback model {DEFAULT_MODEL}...{Colors.END}")
                    try:
                        # Use the default model as fallback
                        payload["model"] = DEFAULT_MODEL
                        response = requests.post(f"{OLLAMA_API}/generate", json=payload, timeout=REQUEST_TIMEOUT)
                        response.raise_for_status()
                        result = response.json()
                        command = result.get("response", "").strip()
                        if command:
                            print(f"{Colors.GREEN}Successfully generated command with fallback model.{Colors.END}")
                            return command
                    except:
                        # Fallback failed as well
                        pass
                        
                print(f"{Colors.YELLOW}Please check if Ollama is running and responsive.{Colors.END}")
                return "echo 'Error: Command generation failed due to timeout'"
                
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                print(f"{Colors.YELLOW}Connection error. Retrying in {retry_delay} seconds...{Colors.END}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                print(f"{Colors.RED}Error: Could not connect to Ollama API after {max_retries} attempts.{Colors.END}")
                print(f"{Colors.YELLOW}Make sure Ollama is running with 'ollama serve'{Colors.END}", file=sys.stderr)
                return "echo 'Error: Command generation failed - API connection issue'"
                
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                print(f"{Colors.YELLOW}Request error: {e}. Retrying in {retry_delay} seconds...{Colors.END}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                print(f"{Colors.RED}Error connecting to Ollama API: {e}{Colors.END}", file=sys.stderr)
                
                # Try fallback if the original model isn't available
                if available_models and model != DEFAULT_MODEL and DEFAULT_MODEL in available_models:
                    print(f"{Colors.YELLOW}Trying with fallback model {DEFAULT_MODEL}...{Colors.END}")
                    try:
                        # Use the default model as fallback
                        payload["model"] = DEFAULT_MODEL
                        response = requests.post(f"{OLLAMA_API}/generate", json=payload, timeout=REQUEST_TIMEOUT)
                        response.raise_for_status()
                        result = response.json()
                        command = result.get("response", "").strip()
                        if command:
                            print(f"{Colors.GREEN}Successfully generated command with fallback model.{Colors.END}")
                            return command
                    except:
                        # Fallback failed as well
                        pass
                        
                print(f"{Colors.YELLOW}Make sure Ollama is running with 'ollama serve'{Colors.END}", file=sys.stderr)
                return "echo 'Error: Command generation failed - API connection issue'"
                
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"{Colors.YELLOW}Unexpected error: {e}. Retrying in {retry_delay} seconds...{Colors.END}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                print(f"{Colors.RED}Unexpected error: {e}{Colors.END}", file=sys.stderr)
                return "echo 'Error: Command generation failed'"

def analyze_error(error_output: str, command: str, model: str = DEFAULT_MODEL) -> str:
    """
    Analyze command execution error using AI.
    
    Args:
        error_output: The error message from the command execution
        command: The command that was executed
        model: The Ollama model to use
        
    Returns:
        Analysis and suggested fix for the error
    """
    system_prompt = """You are a command-line expert. Analyze the error message from a failed shell command and provide:
1. A brief explanation of what went wrong
2. A specific suggestion to fix the issue
3. A corrected command that would work

Be concise and direct."""

    formatted_prompt = f"""The following command failed:
```
{command}
```

With this error output:
```
{error_output}
```

What went wrong and how should I fix it?"""
    
    try:
        # Prepare the request payload
        payload = {
            "model": model,
            "prompt": formatted_prompt,
            "system": system_prompt,
            "stream": False,
            "temperature": 0.2,
        }
        
        print(f"{Colors.BLUE}Analyzing error with {Colors.BOLD}{model}{Colors.END}{Colors.BLUE}...{Colors.END}")
        
        # Make the API request
        response = requests.post(f"{OLLAMA_API}/generate", json=payload)
        response.raise_for_status()
        result = response.json()
        
        # Extract the analysis from the response
        analysis = result.get("response", "").strip()
        return analysis
        
    except requests.exceptions.RequestException as e:
        return f"Error connecting to Ollama API: {e}"
    except Exception as e:
        return f"Error analyzing the command: {e}"

def list_models() -> List[str]:
    """
    List all available models from Ollama.
    
    Returns:
        List of available model names
    """
    model_names = []
    try:
        print(f"{Colors.BLUE}Fetching available models from Ollama...{Colors.END}")
        response = requests.get(f"{OLLAMA_API}/tags", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        models = response.json().get("models", [])
        
        if not models:
            print(f"{Colors.YELLOW}No models found. Try pulling some models with 'ollama pull <model>'{Colors.END}")
            return model_names
            
        print(f"\n{Colors.GREEN}{Colors.BOLD}Available models:{Colors.END}")
        print(f"{Colors.CYAN}{'Name':<25} {'Size':>10} {'Last Modified':<20}{Colors.END}")
        print("-" * 60)
        for model in models:
            name = model.get("name", "unknown")
            model_names.append(name)
            size = model.get("size", 0) // (1024*1024)  # Convert to MB
            modified = model.get("modified", "")
            # Highlight the default model
            if name == DEFAULT_MODEL:
                print(f"{Colors.BOLD}{name:<25} {size:>8} MB   {modified}{Colors.END} {Colors.GREEN}(default){Colors.END}")
            else:
                print(f"{name:<25} {size:>8} MB   {modified}")
        
        print(f"\n{Colors.YELLOW}💡 Tip: You can set a different default model with --model{Colors.END}")
        return model_names
            
    except requests.exceptions.Timeout:
        print(f"{Colors.RED}Error: Request to Ollama API timed out after {REQUEST_TIMEOUT} seconds.{Colors.END}")
        print(f"{Colors.YELLOW}Please check if Ollama is running and responsive.{Colors.END}")
        return model_names
    except requests.exceptions.RequestException as e:
        print(f"{Colors.RED}Error connecting to Ollama API: {e}{Colors.END}", file=sys.stderr)
        print(f"{Colors.YELLOW}Make sure Ollama is running with 'ollama serve'{Colors.END}", file=sys.stderr)
        return model_names
    except Exception as e:
        print(f"{Colors.RED}Unexpected error: {e}{Colors.END}", file=sys.stderr)
        return model_names

def execute_command(command: str, analyze_errors: bool = False, model: str = DEFAULT_MODEL) -> Tuple[int, str]:
    """
    Execute a shell command and capture its output.
    
    Args:
        command: The command to execute
        analyze_errors: Whether to analyze errors if the command fails
        model: The model to use for error analysis
        
    Returns:
        Tuple of (returncode, command_output)
    """
    try:
        # Check for potentially dangerous commands
        is_dangerous = any(pattern in command.lower() for pattern in DANGEROUS_PATTERNS)
        
        if is_dangerous:
            print(f"\n{Colors.RED}⚠️ WARNING: This command may be destructive! ⚠️{Colors.END}")
            print(f"{Colors.RED}Please review carefully before proceeding.{Colors.END}")
            confirmation = input(f"\n{Colors.RED}{Colors.BOLD}Are you ABSOLUTELY SURE you want to execute this potentially dangerous command? (yes/NO): {Colors.END}")
            if confirmation.lower() != "yes":
                print(f"{Colors.YELLOW}Command execution cancelled for safety.{Colors.END}")
                return 1, "Command execution cancelled for safety."
        
        print(f"\n{Colors.GREEN}Executing: {Colors.BOLD}{command}{Colors.END}\n")
        
        # Create a visual separator
        terminal_width = os.get_terminal_size().columns
        print("-" * terminal_width)
        
        # Capture the command output
        process = subprocess.Popen(
            command, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        output = ""
        for line in process.stdout:
            output += line
            sys.stdout.write(line)
            sys.stdout.flush()
        
        # Wait for the process to complete
        returncode = process.wait()
        
        # Create a visual separator
        print("-" * terminal_width)
        
        if returncode != 0:
            print(f"\n{Colors.YELLOW}Command exited with status code {returncode}{Colors.END}")
            
        return returncode, output
            
    except Exception as e:
        error_msg = f"Error executing command: {e}"
        print(f"{Colors.RED}{error_msg}{Colors.END}", file=sys.stderr)
        return 1, error_msg

def print_cool_header():
    """
    Print a cool banner for the tool.
    """
    print(f"""
{Colors.CYAN}╭─────────────────────────────────────────╮
│ {Colors.BOLD}qcmd - AI-powered Command Generator{Colors.END}{Colors.CYAN}    │
│ {Colors.BLUE}Powered by Qwen2.5-Coder via Ollama{Colors.END}{Colors.CYAN}    │
╰─────────────────────────────────────────╯{Colors.END}
    """)

def print_examples():
    """
    Print examples of how to use the command
    """
    # Use a more professional layout with clear sections
    print(f"\n{Colors.BOLD}╔═══════════════════════════════════════════════════════════════════════════════╗{Colors.END}")
    print(f"{Colors.BOLD}║{Colors.END} {Colors.CYAN}QCMD QUICK REFERENCE{Colors.END}                                                     {Colors.BOLD}║{Colors.END}")
    print(f"{Colors.BOLD}╚═══════════════════════════════════════════════════════════════════════════════╝{Colors.END}")
    
    # Basic Usage Section
    print(f"\n{Colors.BOLD}{Colors.GREEN}▶ BASIC COMMANDS{Colors.END}")
    print(f"  {Colors.YELLOW}qcmd \"list all files\"{Colors.END}              Generate a command")
    print(f"  {Colors.YELLOW}qcmd --execute \"check disk space\"{Colors.END}  Generate and execute command")
    print(f"  {Colors.YELLOW}qcmd --shell{Colors.END}                      Start interactive shell")
    print(f"  {Colors.YELLOW}qcmd --status{Colors.END}                     Show system status")
    
    # Advanced Usage Section
    print(f"\n{Colors.BOLD}{Colors.GREEN}▶ ADVANCED COMMANDS{Colors.END}")
    print(f"  {Colors.YELLOW}qcmd --model llama2:7b \"restart service\"{Colors.END}  Use specific model")
    print(f"  {Colors.YELLOW}qcmd --auto \"find Python files\"{Colors.END}          Auto-execute with error fixing")
    print(f"  {Colors.YELLOW}qcmd --analyze \"find large files\"{Colors.END}        Analyze command errors")
    
    # Log Analysis Section
    print(f"\n{Colors.BOLD}{Colors.GREEN}▶ LOG ANALYSIS{Colors.END}")
    print(f"  {Colors.YELLOW}qcmd --logs{Colors.END}                       Find and analyze logs")
    print(f"  {Colors.YELLOW}qcmd --monitor /var/log/syslog{Colors.END}    Monitor logs with AI")
    print(f"  {Colors.YELLOW}qcmd --watch /var/log/auth.log{Colors.END}    Watch logs without AI")
    
    # UI Customization Section
    print(f"\n{Colors.BOLD}{Colors.GREEN}▶ UI CUSTOMIZATION{Colors.END}")
    print(f"  {Colors.YELLOW}qcmd --banner-font doom{Colors.END}           Use custom banner font")
    print(f"  {Colors.YELLOW}qcmd --no-banner{Colors.END}                  Hide the Iraq banner")
    print(f"  {Colors.YELLOW}qcmd --compact{Colors.END}                    Use compact UI mode")
    
    # Tips Section
    print(f"\n{Colors.BOLD}{Colors.GREEN}▶ TIPS & SHORTCUTS{Colors.END}")
    print(f"  {Colors.CYAN}•{Colors.END} Press {Colors.BOLD}Tab{Colors.END} for command completion in interactive mode")
    print(f"  {Colors.CYAN}•{Colors.END} Use {Colors.BOLD}up/down arrows{Colors.END} to navigate history")
    print(f"  {Colors.CYAN}•{Colors.END} Press {Colors.BOLD}'a'{Colors.END} to toggle AI analysis when monitoring logs")
    print(f"  {Colors.CYAN}•{Colors.END} Edit {Colors.BOLD}~/.qcmd/config.json{Colors.END} to customize defaults")
    
    # Footer
    print(f"\n{Colors.BOLD}╔═══════════════════════════════════════════════════════════════════════════════╗{Colors.END}")
    print(f"{Colors.BOLD}║{Colors.END} {Colors.YELLOW}Use 'qcmd --help' for full documentation and all available options{Colors.END}          {Colors.BOLD}║{Colors.END}")
    print(f"{Colors.BOLD}╚═══════════════════════════════════════════════════════════════════════════════╝{Colors.END}")
    print()

class SimpleCompleter:
    """
    A simple tab completer for readline support in the interactive shell.
    """
    def __init__(self, options):
        self.options = options
        self.matches = []
        
    def complete(self, text, state):
        """
        Complete the current text based on available options.
        
        Args:
            text: The text to complete
            state: The state of the completion
            
        Returns:
            The next possible completion, or None if no more completions
        """
        if state == 0:
            # Build a new list of matches on first call
            if text:
                self.matches = [option for option in self.options if option.startswith(text)]
            else:
                self.matches = self.options[:]
        
        # Return match or None if we have no more matches
        try:
            return self.matches[state]
        except IndexError:
            return None

def start_interactive_shell(auto_mode_enabled: bool = False, current_model: str = DEFAULT_MODEL, current_temperature: float = 0.7, max_attempts: int = 3) -> None:
    """
    Start an interactive shell for generating and executing commands.
    
    Args:
        auto_mode_enabled: Whether auto mode is enabled
        current_model: Current AI model to use
        current_temperature: Temperature for model (creativity level)
        max_attempts: Maximum attempts for auto fix mode
    """
    # Print welcome message
    print(f"\n{Colors.BOLD}╔══════════════════════════════════════════════════════════════════╗{Colors.END}")
    print(f"{Colors.BOLD}║{Colors.END} {Colors.CYAN}Welcome to QCMD Interactive Shell{Colors.END}                          {Colors.BOLD}║{Colors.END}")
    print(f"{Colors.BOLD}╚══════════════════════════════════════════════════════════════════╝{Colors.END}")
    
    print(f"\n{Colors.YELLOW}Using model: {Colors.BOLD}{current_model}{Colors.END}")
    print(f"{Colors.YELLOW}Type {Colors.BOLD}/help{Colors.END}{Colors.YELLOW} for available commands{Colors.END}")
    print(f"\n{Colors.RED}Debug: Interactive shell using the updated code{Colors.END}")
    
    # Create readline completer for better UX
    completer = SimpleCompleter([
        "/help", "/exit", "/quit", "/model", "/temperature", 
        "/auto", "/status", "/logs", "/all-logs", "/monitor", "/watch",
        "/history", "/clear", "/analyze-file", "/config", "/reset"
    ])
    
    # Try to enable readline completion
    try:
        import readline
        readline.set_completer(completer.complete)
        readline.parse_and_bind("tab: complete")
    except (ImportError, AttributeError):
        # Readline not available or not working
        pass
    
    # Loop for interactive shell
    history = []
    history_index = 0
    quit_requested = False
    
    # Track current settings
    current_auto = auto_mode_enabled
    current_analyze = False  # Whether to analyze errors by default
    last_command = ""
    
    while not quit_requested:
        try:
            # Get user input
            prompt = input(f"\n{Colors.GREEN}qcmd ({Colors.BOLD}{current_model}{Colors.END}"
                          f"{Colors.GREEN}) > {Colors.END}").strip()
            
            # Handle empty input
            if not prompt:
                continue
                
            # Handle shell commands
            if prompt.startswith("/"):
                parts = prompt.split(maxsplit=1)
                cmd = parts[0].lower()
                
                if cmd in ("/exit", "/quit"):
                    print(f"{Colors.YELLOW}Exiting qcmd shell...{Colors.END}")
                    quit_requested = True
                    continue
                    
                elif cmd == "/help":
                    # Use our new professional help display function
                    display_help_command(current_model, current_temperature, current_auto, max_attempts)
                    continue
                
                elif cmd == "/model":
                    if len(parts) > 1:
                        current_model = parts[1]
                        print(f"{Colors.GREEN}Switched to model: {Colors.BOLD}{current_model}{Colors.END}")
                    else:
                        print(f"{Colors.YELLOW}Usage: /model <model_name>{Colors.END}")
                        print(f"{Colors.YELLOW}Current model: {Colors.BOLD}{current_model}{Colors.END}")
                        print(f"{Colors.YELLOW}Use /help to see available commands{Colors.END}")
                    continue
                    
                elif cmd == "/temperature":
                    if len(parts) > 1:
                        try:
                            t = float(parts[1])
                            if 0 <= t <= 1:
                                current_temperature = t
                                print(f"{Colors.GREEN}Temperature set to: {Colors.BOLD}{current_temperature}{Colors.END}")
                            else:
                                print(f"{Colors.YELLOW}Temperature must be between 0 and 1{Colors.END}")
                        except ValueError:
                            print(f"{Colors.YELLOW}Invalid temperature value{Colors.END}")
                    else:
                        print(f"{Colors.YELLOW}Usage: /temperature <value>{Colors.END}")
                        print(f"{Colors.YELLOW}Current temperature: {Colors.BOLD}{current_temperature}{Colors.END}")
                    continue
                    
                elif cmd == "/auto":
                    current_auto = True
                    print(f"{Colors.GREEN}Auto mode {Colors.BOLD}enabled{Colors.END}")
                    continue
                    
                elif cmd == "/manual":
                    current_auto = False
                    print(f"{Colors.GREEN}Auto mode {Colors.BOLD}disabled{Colors.END}")
                    continue
                    
                elif cmd == "/analyze":
                    current_analyze = not current_analyze
                    state = "enabled" if current_analyze else "disabled"
                    print(f"{Colors.GREEN}Error analysis {Colors.BOLD}{state}{Colors.END}")
                    continue
                    
                elif cmd == "/status":
                    display_system_status()
                    continue
                    
                elif cmd == "/logs":
                    handle_log_analysis(current_model)
                    continue
                    
                elif cmd == "/all-logs":
                    log_files = find_log_files(include_system=True)
                    if log_files:
                        print(f"{Colors.GREEN}Found {len(log_files)} log files:{Colors.END}")
                        selected_log = display_log_selection(log_files)
                        if selected_log:
                            handle_log_selection(selected_log, current_model)
                    else:
                        print(f"{Colors.YELLOW}No accessible log files found on the system.{Colors.END}")
                    continue
                    
                elif cmd == "/analyze-file":
                    if len(parts) > 1:
                        file_path = parts[1]
                        if os.path.exists(file_path) and os.path.isfile(file_path):
                            analyze_log_file(file_path, current_model, False, True)
                        else:
                            print(f"{Colors.RED}Error: File {file_path} does not exist or is not accessible.{Colors.END}")
                    else:
                        print(f"{Colors.YELLOW}Usage: /analyze-file <file_path>{Colors.END}")
                    continue
                    
                elif cmd == "/monitor":
                    if len(parts) > 1:
                        file_path = parts[1]
                        if not os.path.exists(file_path):
                            try:
                                with open(file_path, 'w') as f:
                                    pass
                                print(f"{Colors.GREEN}Created new log file: {file_path}{Colors.END}")
                            except Exception as e:
                                print(f"{Colors.RED}Error creating file {file_path}: {e}{Colors.END}")
                                continue
                                
                        if os.path.isfile(file_path):
                            analyze_log_file(file_path, current_model, True, True)
                        else:
                            print(f"{Colors.RED}Error: {file_path} is not a regular file.{Colors.END}")
                    else:
                        print(f"{Colors.YELLOW}Usage: /monitor <file_path>{Colors.END}")
                    continue
                    
                elif cmd == "/watch":
                    if len(parts) > 1:
                        file_path = parts[1]
                        if not os.path.exists(file_path):
                            try:
                                with open(file_path, 'w') as f:
                                    pass
                                print(f"{Colors.GREEN}Created new log file: {file_path}{Colors.END}")
                            except Exception as e:
                                print(f"{Colors.RED}Error creating file {file_path}: {e}{Colors.END}")
                                continue
                                
                        if os.path.isfile(file_path):
                            analyze_log_file(file_path, current_model, True, False)
                        else:
                            print(f"{Colors.RED}Error: {file_path} is not a regular file.{Colors.END}")
                    else:
                        print(f"{Colors.YELLOW}Usage: /watch <file_path>{Colors.END}")
                    continue
                    
                elif cmd == "/history":
                    load_history(20)
                    continue
                    
                elif cmd == "/clear":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print(f"{Colors.GREEN}Screen cleared.{Colors.END}")
                    continue
                
                elif cmd == "/config":
                    if len(parts) > 1:
                        handle_config_command(parts[1])
                    else:
                        handle_config_command("")
                    continue
                    
                else:
                    print(f"{Colors.YELLOW}Unknown command: {cmd}{Colors.END}")
                    print(f"{Colors.YELLOW}Type {Colors.BOLD}/help{Colors.END}{Colors.YELLOW} for available commands{Colors.END}")
                    continue

            # Normal command processing - save to history
            save_to_history(prompt)
            
            # Process natural language command
            if current_auto:
                # Auto mode generates, executes, and fixes automatically
                auto_mode(prompt, current_model, max_attempts, current_temperature)
            else:
                # Standard mode - generate a command and ask for confirmation
                print(f"{Colors.GREEN}Generating command for: {Colors.BOLD}{prompt}{Colors.END}")
                command = generate_command(prompt, current_model, current_temperature)
                last_command = command
                
                # Display the generated command
                print(f"\n{Colors.CYAN}Generated Command: {Colors.BOLD}{command}{Colors.END}")
                
                # Ask if user wants to execute
                response = input(f"\n{Colors.GREEN}Do you want to execute this command? (y/n): {Colors.END}").lower()
                if response in ["y", "yes"]:
                    # Execute the command
                    returncode, output = execute_command(command, current_analyze, current_model)
                    
                    # If command failed and analysis is enabled, show analysis
                    if returncode != 0 and current_analyze:
                        print(f"\n{Colors.BLUE}Analyzing error...{Colors.END}")
                        analysis = analyze_error(output, command, current_model)
                        
                        print(f"\n{Colors.YELLOW}{Colors.BOLD}AI Error Analysis:{Colors.END}")
                        print(f"{Colors.CYAN}{analysis}{Colors.END}")
                else:
                    print(f"{Colors.YELLOW}Command execution cancelled.{Colors.END}")
            
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Command interrupted.{Colors.END}")
            continue
        except EOFError:
            print(f"\n{Colors.YELLOW}Exiting qcmd shell...{Colors.END}")
            break
        except Exception as e:
            print(f"\n{Colors.RED}Error: {e}{Colors.END}")
            continue

def fix_command(command: str, error_output: str, model: str = DEFAULT_MODEL) -> str:
    """
    Generate a fixed command based on the error output.
    
    Args:
        command: The original command that failed
        error_output: The error message from the command execution
        model: The model to use for generating the fix
        
    Returns:
        The fixed command
    """
    system_prompt = """You are a command-line expert. A shell command has failed with an error. 
Generate a CORRECTED version of the command that fixes the issue.
Reply with ONLY the fixed command, no explanations, no markdown, and no backticks."""

    formatted_prompt = f"""The following command failed:
```
{command}
```

With this error output:
```
{error_output}
```

Please provide ONLY the corrected command with no formatting:"""
    
    try:
        # Prepare the request payload
        payload = {
            "model": model,
            "prompt": formatted_prompt,
            "system": system_prompt,
            "stream": False,
            "temperature": 0.2,
        }
        
        print(f"{Colors.BLUE}Generating fixed command with {Colors.BOLD}{model}{Colors.END}{Colors.BLUE}...{Colors.END}")
        
        # Make the API request
        response = requests.post(f"{OLLAMA_API}/generate", json=payload)
        response.raise_for_status()
        result = response.json()
        
        # Extract the fixed command from the response
        fixed_command = result.get("response", "").strip()
        
        # Thorough cleanup of the command (remove any markdown formatting)
        # Handle multiline code blocks with language specifier
        if fixed_command.startswith("```") and "\n" in fixed_command:
            lines = fixed_command.split("\n")
            # Check if it's a complete code block
            if lines[0].startswith("```") and lines[-1] == "```":
                # Remove first and last lines
                fixed_command = "\n".join(lines[1:-1]).strip()
            else:
                # Extract content after markdown start
                fixed_command = "\n".join(lines[1:]).strip()
                # If there's still a closing ``` at the end, remove it
                if fixed_command.endswith("```"):
                    fixed_command = fixed_command[:-3].strip()
        # Handle single line code blocks
        elif fixed_command.startswith("```") and fixed_command.endswith("```"):
            fixed_command = fixed_command[3:-3].strip()
        # Handle inline code with backticks
        elif fixed_command.startswith("`") and fixed_command.endswith("`"):
            fixed_command = fixed_command[1:-1].strip()
        # Handle any remaining backticks
        fixed_command = fixed_command.replace("```", "").replace("`", "").strip()
        
        return fixed_command
        
    except requests.exceptions.RequestException as e:
        return command  # Return original command on error
    except Exception as e:
        return command  # Return original command on error

def auto_mode(prompt: str, model: str = DEFAULT_MODEL, max_attempts: int = 3, temperature: float = 0.7) -> None:
    """
    Run in auto mode: generate, execute, and fix the command automatically.
    
    Args:
        prompt: The user's prompt for generating a command
        model: The model to use
        max_attempts: Maximum number of attempts to fix the command
        temperature: The temperature to use for generation
    """
    print(f"{Colors.GREEN}🤖 Auto mode activated for: {Colors.BOLD}{prompt}{Colors.END}")
    
    # Initialize output variable to store command execution output
    output = ""
    command = ""
    
    for attempt in range(1, max_attempts + 1):
        if attempt == 1:
            # First attempt: generate a new command
            command = generate_command(prompt, model, temperature)
        else:
            # Subsequent attempts: fix the previous command
            print(f"\n{Colors.YELLOW}Attempt {attempt}/{max_attempts}: Fixing command...{Colors.END}")
            command = fix_command(command, output, model)
        
        # Clean up the command more thoroughly to remove any markdown formatting
        # This is an extra safeguard beyond what generate_command and fix_command do
        if command.startswith("```") and "\n" in command:
            # Handle multiline code blocks
            lines = command.split("\n")
            if lines[0].startswith("```") and lines[-1] == "```":
                # Remove first and last lines that are just markdown markers
                command = "\n".join(lines[1:-1])
            else:
                # Try to extract content after the markdown start
                command = "\n".join(lines[1:])
        elif command.startswith("```"):
            # Handle ```command``` format
            command = command.replace("```", "").strip()
        elif command.startswith("`") and command.endswith("`"):
            # Handle `command` format
            command = command[1:-1].strip()
        
        print(f"\n{Colors.CYAN}Generated Command: {Colors.BOLD}{command}{Colors.END}")
        
        # Execute the command automatically without asking for confirmation
        print(f"\n{Colors.GREEN}Executing command automatically (auto mode)...{Colors.END}")
        returncode, output = execute_command(command, False, model)
        
        # If command succeeded, we're done
        if returncode == 0:
            print(f"\n{Colors.GREEN}✓ Command executed successfully!{Colors.END}")
            return
        
        # If we've reached the maximum number of attempts, show analysis
        if attempt == max_attempts:
            print(f"\n{Colors.RED}✗ Failed after {max_attempts} attempts.{Colors.END}")
            print(f"\n{Colors.BLUE}Analyzing error...{Colors.END}")
            analysis = analyze_error(output, command, model)
            
            print(f"\n{Colors.YELLOW}{Colors.BOLD}AI Error Analysis:{Colors.END}")
            print(f"{Colors.CYAN}{analysis}{Colors.END}")
            return
        
        print(f"\n{Colors.YELLOW}Command failed. Automatically trying to fix it...{Colors.END}")

def analyze_log_file(log_file: str, model: str = DEFAULT_MODEL, background: bool = False, analyze: bool = True) -> None:
    """
    Analyze a log file continuously or once.
    
    Args:
        log_file: Path to the log file to analyze
        model: The model to use for analysis
        background: Whether to run in background continuously
        analyze: Whether to perform AI analysis on the log content
    """
    if not os.path.exists(log_file):
        print(f"{Colors.RED}Error: Log file {log_file} does not exist.{Colors.END}")
        return
    
    # Register this monitor
    monitor_id = os.path.abspath(log_file)
    
    # Update in-memory copy
    ACTIVE_LOG_MONITORS[monitor_id] = {
        "file": log_file,
        "analyze": analyze,
        "model": model,
        "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "pid": os.getpid()
    }
    
    # Update persistent copy
    monitors = load_monitors()
    monitors[monitor_id] = ACTIVE_LOG_MONITORS[monitor_id]
    save_monitors(monitors)
        
    print(f"{Colors.GREEN}{'Analyzing' if analyze else 'Watching'} log file: {Colors.BOLD}{log_file}{Colors.END}")
    
    # Function for cleanup
    def cleanup():
        # Remove from active monitors
        if monitor_id in ACTIVE_LOG_MONITORS:
            del ACTIVE_LOG_MONITORS[monitor_id]
            
        # Also remove from persistent storage
        monitors = load_monitors()
        if monitor_id in monitors:
            del monitors[monitor_id]
            save_monitors(monitors)
    
    # Get file size for pagination
    file_size = os.path.getsize(log_file)
    
    # For very large files, ask if user wants to analyze only the last part
    if file_size > 10 * 1024 * 1024 and not background:  # 10 MB
        print(f"{Colors.YELLOW}Warning: This log file is very large ({file_size // (1024*1024)} MB).{Colors.END}")
        response = input(f"{Colors.GREEN}Analyze only the last portion? (y/n, default: y): {Colors.END}").lower()
        if not response or response.startswith('y'):
            # Read only the last 1 MB
            try:
                with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                    f.seek(max(0, file_size - 1 * 1024 * 1024))  # Go to last 1 MB
                    # Skip partial line
                    f.readline()
                    log_content = f.read().strip()
                print(f"{Colors.YELLOW}Analyzing only the last 1 MB of the log file.{Colors.END}")
            except UnicodeDecodeError:
                # If UTF-8 fails, try with a more permissive encoding
                try:
                    with open(log_file, 'r', encoding='latin-1') as f:
                        f.seek(max(0, file_size - 1 * 1024 * 1024))  # Go to last 1 MB
                        # Skip partial line
                        f.readline()
                        log_content = f.read().strip()
                    print(f"{Colors.YELLOW}Analyzing only the last 1 MB of the log file.{Colors.END}")
                except Exception as e:
                    print(f"{Colors.RED}Error reading log file: {e}{Colors.END}")
                    
                    # Clean up before exiting
                    cleanup()
                    return
        else:
            # Read with pagination for very large files
            log_content = read_large_file(log_file)
    else:
        # Get initial log content
        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                log_content = f.read().strip()
        except UnicodeDecodeError:
            # If UTF-8 fails, try with a more permissive encoding
            try:
                with open(log_file, 'r', encoding='latin-1') as f:
                    log_content = f.read().strip()
            except Exception as e:
                print(f"{Colors.RED}Error reading log file: {e}{Colors.END}")
                
                # Clean up before exiting
                cleanup()
                return
        except Exception as e:
            print(f"{Colors.RED}Error reading log file: {e}{Colors.END}")
            
            # Clean up before exiting
            cleanup()
            return
    
    # If not running in background, just analyze once
    if not background:
        analyze_log_content(log_content, log_file, model)
        
        # Clean up after single analysis
        cleanup()
        return
        
    # Store last position to track new content
    last_position = os.path.getsize(log_file)
    
    # Detect encoding for continued reading
    encoding = 'utf-8'
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            f.read(10)  # Test read a small portion
    except UnicodeDecodeError:
        encoding = 'latin-1'  # Fallback encoding
    
    # Function for cleanup
    def cleanup():
        # Remove from active monitors
        if monitor_id in ACTIVE_LOG_MONITORS:
            del ACTIVE_LOG_MONITORS[monitor_id]
            
    # Function to run in a separate thread
    def monitor_log():
        nonlocal last_position
        # analyze is already accessible from parent scope, no need for nonlocal
        
        print(f"{Colors.GREEN}Starting continuous log {'monitoring with analysis' if analyze else 'watching'} for {Colors.BOLD}{log_file}{Colors.END}")
        print(f"{Colors.YELLOW}Press Ctrl+C to stop {'monitoring' if analyze else 'watching'}.{Colors.END}")
        print(f"{Colors.YELLOW}Press 'a' to toggle AI analysis (currently {'ON' if analyze else 'OFF'}).{Colors.END}")
        
        try:
            while True:
                # Check if file size has changed
                try:
                    current_size = os.path.getsize(log_file)
                    
                    if current_size > last_position:
                        # Read only the new content
                        with open(log_file, 'r', encoding=encoding, errors='replace' if encoding == 'utf-8' else None) as f:
                            f.seek(last_position)
                            new_content = f.read()
                        
                        if new_content:
                            print(f"\n{Colors.CYAN}New log entries detected at {datetime.now().strftime('%H:%M:%S')}:{Colors.END}")
                            print(f"{Colors.YELLOW}" + "-" * 40 + f"{Colors.END}")
                            print(new_content)
                            print(f"{Colors.YELLOW}" + "-" * 40 + f"{Colors.END}")
                            
                            # Show analysis status
                            status = f"{Colors.GREEN}AI Analysis: {'ON' if analyze else 'OFF'} (Press 'a' to toggle){Colors.END}"
                            print(status)
                            
                            # Analyze the new content only if analyze flag is True
                            if analyze:
                                analyze_log_content(new_content, log_file, model)
                        
                        # Update position
                        last_position = current_size
                except FileNotFoundError:
                    print(f"\n{Colors.RED}Error: Log file {log_file} no longer exists.{Colors.END}")
                    break
                except PermissionError:
                    print(f"\n{Colors.RED}Error: Permission denied when reading {log_file}.{Colors.END}")
                    time.sleep(5)  # Wait longer before retrying on permissions issues
                    continue
                except Exception as e:
                    print(f"\n{Colors.RED}Error reading log file: {e}{Colors.END}")
                    time.sleep(2)
                    continue
                
                # Wait before checking again
                time.sleep(1)
                
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Stopped {'monitoring' if analyze else 'watching'}.{Colors.END}")
            cleanup()
        except Exception as e:
            print(f"\n{Colors.RED}Error {'monitoring' if analyze else 'watching'}: {e}{Colors.END}")
            cleanup()
    
    # Start monitoring in a separate thread
    monitor_thread = threading.Thread(target=monitor_log)
    monitor_thread.daemon = True  # This will make the thread exit when the main program exits
    monitor_thread.start()
    
    # Keep the main thread alive and handle key presses
    try:
        # Set up keystroke detection
        import select
        import sys
        import termios
        import tty
        
        # Save terminal settings
        old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        
        while monitor_thread.is_alive():
            # Check for keypress without blocking
            if select.select([sys.stdin], [], [], 0.5)[0]:
                key = sys.stdin.read(1)
                if key == 'a':  # Toggle analysis
                    analyze = not analyze
                    print(f"\n{Colors.GREEN}AI Analysis {'enabled' if analyze else 'disabled'}.{Colors.END}")
                    
                    # Update persistent storage with new analyze state
                    monitors = load_monitors()
                    if monitor_id in monitors:
                        monitors[monitor_id]["analyze"] = analyze
                        save_monitors(monitors)
                elif key == 'q':  # Quit monitoring
                    print(f"\n{Colors.YELLOW}Stopping {'monitoring' if analyze else 'watching'}...{Colors.END}")
                    break
            
            monitor_thread.join(0.1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Stopped {'monitoring' if analyze else 'watching'}.{Colors.END}")
    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        cleanup()  # Clean up in case of any other exception

def analyze_log_content(log_content: str, log_file: str, model: str = DEFAULT_MODEL) -> None:
    """
    Analyze log content using AI.
    
    Args:
        log_content: The log content to analyze
        log_file: Path to the log file (for context)
        model: The model to use for analysis
    """
    # If content is too large, take the last 1000 lines
    lines = log_content.splitlines()
    if len(lines) > 1000:
        log_content = '\n'.join(lines[-1000:])
        print(f"{Colors.YELLOW}Log content is large. Analyzing only the last 1000 lines.{Colors.END}")
    
    system_prompt = """You are a log analysis expert. Analyze the given log content and provide:
1. A summary of what the log shows
2. Any errors or warnings that should be addressed
3. Patterns or trends in the log

Be concise but thorough. Focus on actionable information."""

    formatted_prompt = f"""Please analyze this log from {log_file}:

```
{log_content}
```

What does this log show? Are there any errors or patterns to be concerned about?"""
    
    # Get available models for fallback
    available_models = []
    try:
        available_models = list_models()
    except:
        pass
        
    # Try with retries for network resilience
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            # Prepare the request payload
            payload = {
                "model": model,
                "prompt": formatted_prompt,
                "system": system_prompt,
                "stream": False,
                "temperature": 0.2,
            }
            
            if attempt > 0:
                print(f"{Colors.YELLOW}Retry attempt {attempt+1}/{max_retries}...{Colors.END}")
            else:
                print(f"{Colors.BLUE}Analyzing logs with {Colors.BOLD}{model}{Colors.END}{Colors.BLUE}...{Colors.END}")
            
            # Make the API request with timeout
            response = requests.post(f"{OLLAMA_API}/generate", json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            result = response.json()
            
            # Extract the analysis from the response
            analysis = result.get("response", "").strip()
            
            print(f"\n{Colors.YELLOW}{Colors.BOLD}AI Log Analysis:{Colors.END}")
            print(f"{Colors.CYAN}{analysis}{Colors.END}")
            
            return  # Success, exit the function
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                print(f"{Colors.YELLOW}Request timed out. Retrying in {retry_delay} seconds...{Colors.END}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                print(f"{Colors.RED}Error: Log analysis timed out after {REQUEST_TIMEOUT} seconds.{Colors.END}")
                
                # Try fallback if the original model isn't available
                if available_models and model != DEFAULT_MODEL and DEFAULT_MODEL in available_models:
                    print(f"{Colors.YELLOW}Trying with fallback model {DEFAULT_MODEL}...{Colors.END}")
                    try:
                        # Use the default model as fallback
                        payload["model"] = DEFAULT_MODEL
                        response = requests.post(f"{OLLAMA_API}/generate", json=payload, timeout=REQUEST_TIMEOUT)
                        response.raise_for_status()
                        result = response.json()
                        analysis = result.get("response", "").strip()
                        if analysis:
                            print(f"{Colors.GREEN}Successfully analyzed logs with fallback model.{Colors.END}")
                            print(f"\n{Colors.YELLOW}{Colors.BOLD}AI Log Analysis:{Colors.END}")
                            print(f"{Colors.CYAN}{analysis}{Colors.END}")
                            return
                    except:
                        # Fallback failed as well
                        pass
                        
                print(f"{Colors.YELLOW}The log file might be too large or complex. Try analyzing a smaller section.{Colors.END}")
                
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                print(f"{Colors.YELLOW}Connection error. Retrying in {retry_delay} seconds...{Colors.END}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                print(f"{Colors.RED}Error: Could not connect to Ollama API after {max_retries} attempts.{Colors.END}")
                print(f"{Colors.YELLOW}Make sure Ollama is running with 'ollama serve'{Colors.END}", file=sys.stderr)
                
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                print(f"{Colors.YELLOW}Request error: {e}. Retrying in {retry_delay} seconds...{Colors.END}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                print(f"{Colors.RED}Error connecting to Ollama API: {e}{Colors.END}")
                
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"{Colors.YELLOW}Unexpected error: {e}. Retrying in {retry_delay} seconds...{Colors.END}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                print(f"{Colors.RED}Error analyzing log content: {e}{Colors.END}")

def read_large_file(file_path: str, chunk_size: int = 1024 * 1024) -> str:
    """
    Read a large file in chunks with user confirmation between chunks.
    
    Args:
        file_path: Path to the file to read
        chunk_size: Size of each chunk in bytes (default: 1 MB)
        
    Returns:
        The content of the file or a portion of it
    """
    file_size = os.path.getsize(file_path)
    chunks = file_size // chunk_size + (1 if file_size % chunk_size > 0 else 0)
    
    if chunks <= 1:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except UnicodeDecodeError:
            # If UTF-8 fails, try with a more permissive encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                print(f"{Colors.RED}Error reading file: {e}{Colors.END}")
                return ""
            
    print(f"{Colors.YELLOW}File is {file_size // (1024*1024)} MB and will be read in {chunks} chunks.{Colors.END}")
    
    # Options for reading
    print(f"\n{Colors.GREEN}How would you like to read this file?{Colors.END}")
    print(f"1. {Colors.BOLD}First chunk{Colors.END} (beginning of file)")
    print(f"2. {Colors.BOLD}Last chunk{Colors.END} (end of file)")
    print(f"3. {Colors.BOLD}Interactive{Colors.END} (navigate through chunks)")
    print(f"4. {Colors.BOLD}Cancel{Colors.END}")
    
    choice = input(f"\n{Colors.GREEN}Enter choice (1-4): {Colors.END}")
    
    if choice == '1':
        # Read first chunk
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read(chunk_size)
        except UnicodeDecodeError:
            # If UTF-8 fails, try with a more permissive encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read(chunk_size)
            except Exception as e:
                print(f"{Colors.RED}Error reading file: {e}{Colors.END}")
                return ""
    elif choice == '2':
        # Read last chunk
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(max(0, file_size - chunk_size))
                # Skip partial line
                f.readline()
                return f.read()
        except UnicodeDecodeError:
            # If UTF-8 fails, try with a more permissive encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    f.seek(max(0, file_size - chunk_size))
                    # Skip partial line
                    f.readline()
                    return f.read()
            except Exception as e:
                print(f"{Colors.RED}Error reading file: {e}{Colors.END}")
                return ""
    elif choice == '3':
        # Interactive mode
        current_chunk = 0
        content = ""
        
        # Determine the encoding to use
        encoding = 'utf-8'
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                f.read(10)  # Test read a small portion
        except UnicodeDecodeError:
            encoding = 'latin-1'  # Fallback encoding
            
        try:
            with open(file_path, 'r', encoding=encoding, errors='replace' if encoding == 'utf-8' else None) as f:
                while True:
                    f.seek(current_chunk * chunk_size)
                    if current_chunk > 0:
                        # Skip partial line
                        f.readline()
                    
                    chunk_content = f.read(chunk_size)
                    if not chunk_content:
                        break
                        
                    print(f"\n{Colors.CYAN}Showing chunk {current_chunk + 1} of {chunks}{Colors.END}")
                    print(f"{Colors.YELLOW}" + "-" * 40 + f"{Colors.END}")
                    
                    # Show a preview
                    lines = chunk_content.splitlines()
                    preview_lines = min(10, len(lines))
                    for i in range(preview_lines):
                        line = lines[i][:120] + ('...' if len(lines[i]) > 120 else '')
                        # Remove or replace control characters that could mess up display
                        line = ''.join(c if c.isprintable() or c.isspace() else '?' for c in line)
                        print(line)
                    if len(lines) > preview_lines:
                        print(f"{Colors.YELLOW}... ({len(lines) - preview_lines} more lines) ...{Colors.END}")
                    
                    print(f"{Colors.YELLOW}" + "-" * 40 + f"{Colors.END}")
                    
                    print(f"\n{Colors.GREEN}Navigation:{Colors.END}")
                    print(f"n: {Colors.BOLD}Next chunk{Colors.END}")
                    print(f"p: {Colors.BOLD}Previous chunk{Colors.END}")
                    print(f"s: {Colors.BOLD}Select this chunk{Colors.END}")
                    print(f"a: {Colors.BOLD}Select all remaining chunks{Colors.END}")
                    print(f"q: {Colors.BOLD}Quit{Colors.END}")
                    
                    nav = input(f"\n{Colors.GREEN}Enter choice: {Colors.END}").lower()
                    
                    if nav == 'n':
                        current_chunk = min(current_chunk + 1, chunks - 1)
                    elif nav == 'p':
                        current_chunk = max(current_chunk - 1, 0)
                    elif nav == 's':
                        content = chunk_content
                        break
                    elif nav == 'a':
                        # Read from current position to end
                        f.seek(current_chunk * chunk_size)
                        if current_chunk > 0:
                            # Skip partial line
                            f.readline()
                        content = f.read()
                        break
                    elif nav == 'q':
                        print(f"{Colors.YELLOW}Operation cancelled.{Colors.END}")
                        return ""
                        
                return content
        except Exception as e:
            print(f"{Colors.RED}Error reading file: {e}{Colors.END}")
            return ""
    else:
        print(f"{Colors.YELLOW}Operation cancelled.{Colors.END}")
        return ""

def find_log_files(include_system: bool = False) -> List[str]:
    """
    Find log files in common locations in the system.
    
    Returns:
        List of paths to log files
    """
    # Check if we have a valid cache
    if os.path.exists(LOG_CACHE_FILE):
        try:
            with open(LOG_CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
                cache_time = cache_data.get('timestamp', 0)
                log_files = cache_data.get('log_files', [])
                
                # If cache is still valid (not expired)
                if time.time() - cache_time < LOG_CACHE_EXPIRY:
                    print(f"{Colors.BLUE}Using cached log file list.{Colors.END}")
                    
                    # Include favorite logs from config (in case they were added after caching)
                    config = load_config()
                    favorite_logs = config.get('favorite_logs', [])
                    for log in favorite_logs:
                        if os.path.exists(log) and os.path.isfile(log) and os.access(log, os.R_OK):
                            if log not in log_files:
                                log_files.append(log)
                                
                    return log_files
        except (json.JSONDecodeError, IOError):
            # Cache file is invalid, continue with normal search
            pass
            
    # Common log locations
    log_locations = [
        "/var/log/",
        "/var/log/syslog",
        "/var/log/auth.log",
        "/var/log/dmesg",
        "/var/log/kern.log",
        "/var/log/apache2/",
        "/var/log/nginx/",
        "/var/log/mysql/",
        "/var/log/postgresql/",
        "~/.local/share/",
        "/opt/",
        "/tmp/",
    ]
    
    log_files = []
    
    # Function to check if a file is a log file
    def is_log_file(filename):
        log_extensions = ['.log', '.logs', '.err', '.error', '.out', '.output', '.debug']
        return (any(filename.endswith(ext) for ext in log_extensions) or 
                'log' in filename.lower() or 
                'debug' in filename.lower() or 
                'error' in filename.lower())
    
    # Expand home directory
    log_locations = [os.path.expanduser(loc) for loc in log_locations]
    
    print(f"{Colors.BLUE}Searching for log files...{Colors.END}")
    
    try:
        # First check specific log files
        for location in log_locations:
            if os.path.isfile(location) and os.access(location, os.R_OK):
                log_files.append(location)
            elif os.path.isdir(location) and os.access(location, os.R_OK):
                # For directories, find log files inside
                for root, dirs, files in os.walk(location, topdown=True, followlinks=False):
                    # Limit depth to avoid searching too deep
                    if root.count(os.sep) - location.count(os.sep) > 2:
                        continue
                        
                    # Add log files
                    for file in files:
                        if is_log_file(file) and os.access(os.path.join(root, file), os.R_OK):
                            log_files.append(os.path.join(root, file))
                            
                    # Limit to max 100 files to avoid overloading
                    if len(log_files) > 100:
                        break
        
        # Add any running service logs from systemd
        systemd_logs = []
        try:
            systemd_logs = subprocess.check_output(["systemctl", "list-units", "--type=service", "--state=running", "--no-pager"], 
                                               stderr=subprocess.DEVNULL,
                                               universal_newlines=True,
                                               timeout=5)  # Add timeout
            
            # Extract service names
            service_names = []
            for line in systemd_logs.splitlines():
                if ".service" in line and "running" in line:
                    parts = line.split()
                    for part in parts:
                        if part.endswith(".service"):
                            service_names.append(part)
            
            # Get journalctl logs for running services
            for service in service_names[:10]:  # Limit to top 10 services
                log_files.append(f"journalctl:{service}")
        except (subprocess.SubprocessError, FileNotFoundError):
            # Systemd might not be available
            pass
        except subprocess.TimeoutExpired:
            print(f"{Colors.YELLOW}Systemd service enumeration timed out, skipping service logs.{Colors.END}")
        
        # Include favorite logs from config
        config = load_config()
        favorite_logs = config.get('favorite_logs', [])
        for log in favorite_logs:
            if os.path.exists(log) and os.path.isfile(log) and os.access(log, os.R_OK):
                if log not in log_files:
                    log_files.append(log)
        
        # Cache the results
        try:
            with open(LOG_CACHE_FILE, 'w') as f:
                json.dump({
                    'timestamp': time.time(),
                    'log_files': sorted(set(log_files))
                }, f)
        except (IOError, OSError) as e:
            print(f"{Colors.YELLOW}Could not cache log file list: {e}{Colors.END}")
        
        return sorted(set(log_files))  # Remove duplicates
        
    except Exception as e:
        print(f"{Colors.RED}Error searching for log files: {e}{Colors.END}")
        return []

def display_log_selection(log_files: List[str]) -> Optional[str]:
    """
    Display a menu of log files and let the user select one.
    
    Args:
        log_files: List of log file paths
        
    Returns:
        Selected log file path or None if cancelled
    """
    if not log_files:
        print(f"{Colors.YELLOW}No log files found.{Colors.END}")
        return None
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}Found {len(log_files)} log files:{Colors.END}")
    
    # Group logs by directory for better organization
    logs_by_dir = {}
    for log_file in log_files:
        if log_file.startswith("journalctl:"):
            dir_name = "Systemd Services"
        else:
            dir_name = os.path.dirname(log_file)
            
        if dir_name not in logs_by_dir:
            logs_by_dir[dir_name] = []
            
        logs_by_dir[dir_name].append(log_file)
    
    # Display logs grouped by directory
    index = 1
    file_indices = {}
    
    for dir_name, files in sorted(logs_by_dir.items()):
        print(f"\n{Colors.CYAN}{dir_name}:{Colors.END}")
        for file in sorted(files):
            base_name = os.path.basename(file) if not file.startswith("journalctl:") else file[11:]
            print(f"  {Colors.BOLD}{index}{Colors.END}. {base_name}")
            file_indices[index] = file
            index += 1
    
    while True:
        try:
            choice = input(f"\n{Colors.GREEN}Enter number to select a log file (or q to cancel): {Colors.END}")
            
            if choice.lower() in ['q', 'quit', 'exit']:
                return None
                
            choice = int(choice)
            if choice in file_indices:
                return file_indices[choice]
            else:
                print(f"{Colors.YELLOW}Invalid selection. Please try again.{Colors.END}")
        except ValueError:
            print(f"{Colors.YELLOW}Please enter a number or 'q' to cancel.{Colors.END}")
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Operation cancelled.{Colors.END}")
            return None

def handle_log_analysis(model: str = DEFAULT_MODEL, file_path: str = None) -> None:
    """
    Main entry point for log analysis feature.
    
    Args:
        model: The model to use for analysis
        file_path: Optional path to a specific file to analyze
    """
    print(f"{Colors.GREEN}Starting log analysis tool...{Colors.END}")
    
    # If a specific file is provided, analyze it directly
    if file_path:
        if os.path.exists(file_path) and os.path.isfile(file_path):
            # Ask if user wants continuous monitoring
            monitor = input(f"{Colors.GREEN}Monitor this file continuously? (y/n): {Colors.END}").lower()
            
            # Analyze the specified file
            analyze_log_file(file_path, model, monitor in ['y', 'yes'])
        else:
            print(f"{Colors.RED}Error: File {file_path} does not exist or is not accessible.{Colors.END}")
        return
    
    # Find log files
    log_files = find_log_files()
    
    if not log_files:
        print(f"{Colors.YELLOW}No accessible log files found on the system.{Colors.END}")
        return
    
    # Let user select a log file
    selected_log = display_log_selection(log_files)
    
    if not selected_log:
        return
        
    # Special handling for journalctl entries
    if selected_log.startswith("journalctl:"):
        service_name = selected_log[11:]
        print(f"{Colors.GREEN}Fetching logs for service: {Colors.BOLD}{service_name}{Colors.END}")
        
        try:
            # Create a temporary file to store the logs
            with tempfile.NamedTemporaryFile(delete=False, mode='w+') as temp_file:
                # Get logs from journalctl
                logs = subprocess.check_output(
                    ["journalctl", "-u", service_name, "--no-pager", "-n", "1000"],
                    stderr=subprocess.DEVNULL,
                    universal_newlines=True
                )
                temp_file.write(logs)
                temp_file_path = temp_file.name
            
            # Ask if user wants continuous monitoring
            monitor = input(f"{Colors.GREEN}Monitor this service log continuously? (y/n): {Colors.END}").lower()
            
            # Analyze the log file
            analyze_log_file(temp_file_path, model, monitor in ['y', 'yes'])
            
            # Clean up temp file if not in continuous mode
            if monitor not in ['y', 'yes']:
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except subprocess.SubprocessError as e:
            print(f"{Colors.RED}Error fetching service logs: {e}{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.END}")
            
    else:
        # Ask if user wants continuous monitoring
        monitor = input(f"{Colors.GREEN}Monitor this log file continuously? (y/n): {Colors.END}").lower()
        
        # Analyze the selected log file
        analyze_log_file(selected_log, model, monitor in ['y', 'yes'])

def handle_log_selection(selected_log: str, model: str) -> None:
    """
    Handle a selected log file from the all-logs menu.
    
    Args:
        selected_log: The selected log file path or journalctl service
        model: The model to use for analysis
    """
    if not selected_log:
        return
        
    # Ask if user wants to analyze, monitor with analysis, or just watch the selected log
    action = input(f"{Colors.GREEN}Do you want to (a)nalyze once, (m)onitor with analysis, or just (w)atch without analysis? (a/m/w): {Colors.END}").lower()
    is_monitor = action.startswith('m')
    is_watch = action.startswith('w')
    analyze = not is_watch  # True for analyze and monitor, False for watch
    background = is_monitor or is_watch  # True for both monitoring options
    
    # Special handling for journalctl entries
    if selected_log.startswith("journalctl:"):
        service_name = selected_log[11:]
        print(f"{Colors.GREEN}Fetching logs for service: {Colors.BOLD}{service_name}{Colors.END}")
        
        try:
            # Create a temporary file to store the logs
            with tempfile.NamedTemporaryFile(delete=False, mode='w+') as temp_file:
                try:
                    # Get logs from journalctl with timeout
                    logs = subprocess.check_output(
                        ["journalctl", "-u", service_name, "--no-pager", "-n", "1000"],
                        stderr=subprocess.DEVNULL,
                        universal_newlines=True,
                        timeout=10  # Add timeout of 10 seconds
                    )
                    temp_file.write(logs)
                    temp_file_path = temp_file.name
                except subprocess.TimeoutExpired:
                    print(f"{Colors.RED}Error: journalctl command timed out.{Colors.END}")
                    print(f"{Colors.YELLOW}The service logs might be too large or the system is busy.{Colors.END}")
                    try:
                        os.unlink(temp_file.name)
                    except:
                        pass
                    return
                except FileNotFoundError:
                    print(f"{Colors.RED}Error: journalctl command not found.{Colors.END}")
                    print(f"{Colors.YELLOW}This system might not use systemd or journalctl isn't installed.{Colors.END}")
                    try:
                        os.unlink(temp_file.name)
                    except:
                        pass
                    return
            
            # Analyze the log file
            analyze_log_file(temp_file_path, model, background, analyze)
            
            # Clean up temp file if not in continuous mode
            if not background:
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except subprocess.SubprocessError as e:
            print(f"{Colors.RED}Error fetching service logs: {e}{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.END}")
    else:
        # Regular file
        if os.path.exists(selected_log) and os.path.isfile(selected_log):
            analyze_log_file(selected_log, model, background, analyze)
        else:
            print(f"{Colors.RED}Error: File {selected_log} does not exist or is not accessible.{Colors.END}")

def load_config() -> Dict:
    """
    Load configuration from file
    
    Returns:
        Dictionary containing configuration values
    """
    config = {
        'model': DEFAULT_MODEL,
        'temperature': 0.7,
        'max_attempts': 3,
        'check_updates': True,
        'ui': {
            'show_iraq_banner': True,
            'show_progress_bar': True,
            'compact_mode': False,
            'banner_font': 'slant',  # New option for pyfiglet font
            'progress_delay': 0.05   # Control speed of progress animation
        },
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

def print_iraq_banner():
    """
    Print a stylized IRAQ banner with colors using pyfiglet.
    """
    config = load_config()
    
    # Check if we should force the banner to display (used by post-install script)
    force_banner = os.environ.get('QCMD_FORCE_BANNER', '').lower() == 'true'
    
    if force_banner or config.get('ui', {}).get('show_iraq_banner', True):
        # Don't waste space in compact mode (unless forced)
        if not force_banner and config.get('ui', {}).get('compact_mode', False):
            print(f"{Colors.GREEN}Welcome to QCMD - Iraqi-powered command generation tool!{Colors.END}")
            return
            
        try:
            # Use pyfiglet for stylized text with font from config
            from pyfiglet import Figlet
            font = config.get('ui', {}).get('banner_font', 'slant')
            figlet = Figlet(font=font)
            iraq_text = figlet.renderText('IRAQ')
            
            # Print the text with green color and added styling
            print(f"{Colors.GREEN}{Colors.BOLD}{iraq_text}{Colors.END}")
        except ImportError:
            # Fallback if pyfiglet is not installed
            print(f"\n{Colors.GREEN}{Colors.BOLD}")
            print(" _____ _____        _____  ")
            print("|_   _|  __ \\      / ____| ")
            print("  | | | |__) |    | |    _ ") 
            print("  | | |  _  /     | |   (_)")
            print(" _| |_| | \\ \\     | |____ _ ")
            print("|_____|_|  \\_\\     \\_____(_)")
            print(f"{Colors.END}")
        
        # Add Iraq flag colors (red, white, black)
        print(f"{Colors.RED}    ████████████████████████████████{Colors.END}")
        print(f"{Colors.WHITE}    ████████████████████████████████{Colors.END}")
        print(f"{Colors.BLACK}    ████████████████████████████████{Colors.END}")
        
        print(f"{Colors.YELLOW}Command Generation Tool - Version: {__version__}{Colors.END}")
        print()

def show_download_progress(total=20, message="Initializing QCMD with Iraqi excellence"):
    """
    Display a loading animation with Iraqi colors
    
    Args:
        total: Total number of steps in the progress bar
        message: Message to display above the progress bar
    """
    config = load_config()
    
    # Skip if progress bar is disabled in config
    if not config.get('ui', {}).get('show_progress_bar', True):
        return
    
    # Use delay from config
    delay = config.get('ui', {}).get('progress_delay', 0.05)
    
    print(f"\n{message}:")
    
    # Determine terminal width
    term_width = shutil.get_terminal_size().columns
    bar_width = min(term_width - 2, 40)  # Ensure it fits in terminal
    
    for i in range(total + 1):
        # Calculate percentage
        percent = i / total
        filled_length = int(bar_width * percent)
        empty_length = bar_width - filled_length
        
        # Use Iraq flag colors for the progress bar
        if filled_length > 0:
            # Divide the filled part into three sections for the three colors
            section_length = max(1, filled_length // 3)
            
            red_length = min(section_length, filled_length)
            filled_length -= red_length
            
            white_length = min(section_length, filled_length)
            filled_length -= white_length
            
            black_length = filled_length  # Remainder goes to black
            
            # Create the colored progress bar with Iraqi flag colors
            bar = f"{Colors.RED}{'█' * red_length}{Colors.WHITE}{'█' * white_length}{Colors.BLACK}{'█' * black_length}{Colors.END}{' ' * empty_length}"
        else:
            bar = ' ' * bar_width
        
        # Print progress bar with percentage
        sys.stdout.write(f"\r[{bar}] {int(percent * 100)}%")
        sys.stdout.flush()
        
        time.sleep(delay)
    
    print("\n")

def handle_config_command(args):
    """Handle configuration subcommands"""
    config = load_config()
    
    # Split the command into parts, handling quoted values correctly
    parts = shlex.split(args) if args else []
    
    if not parts:
        # Display current configuration
        print(f"\n{Colors.BOLD}Current Configuration:{Colors.END}")
        print(f"  {Colors.CYAN}model: {Colors.END}{config.get('model', DEFAULT_MODEL)}")
        print(f"  {Colors.CYAN}temperature: {Colors.END}{config.get('temperature', 0.7)}")
        print(f"  {Colors.CYAN}max_attempts: {Colors.END}{config.get('max_attempts', 3)}")
        print(f"  {Colors.CYAN}check_updates: {Colors.END}{config.get('check_updates', True)}")
        
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

def check_for_updates(force_display: bool = False) -> None:
    """
    Check if there's a newer version of the package available on PyPI
    
    Args:
        force_display: Whether to display a message even if no update is found
    """
    try:
        # Get installed version - use version from module directly
        installed_version = __version__
        
        # Check latest version on PyPI
        response = requests.get("https://pypi.org/pypi/ibrahimiq-qcmd/json", timeout=3)
        if response.status_code == 200:
            latest_version = response.json()["info"]["version"]
            
            # Compare versions
            if installed_version != latest_version:
                print(f"\n{Colors.YELLOW}New version available: {Colors.BOLD}{latest_version}{Colors.END}")
                print(f"{Colors.YELLOW}You have: {installed_version}{Colors.END}")
                print(f"{Colors.YELLOW}Update with: {Colors.BOLD}pip install --upgrade ibrahimiq-qcmd{Colors.END}")
            elif force_display:
                print(f"{Colors.GREEN}You have the latest version: {Colors.BOLD}{installed_version}{Colors.END}")
    except Exception as e:
        if force_display:
            print(f"{Colors.YELLOW}Could not check for updates: {e}{Colors.END}")
        # If update check fails, just skip it silently otherwise

def main():
    """
    Main entry point for the command generator
    """
    # Initialize config directory
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    # Parse command-line arguments
    args = parse_args()
    
    # Load configuration
    config = load_config()
    
    # Set default model from config if not specified
    if args.model is None:
        args.model = config.get('model', DEFAULT_MODEL)
    
    # Clean up stale monitor processes
    cleanup_stale_monitors()
    cleanup_stale_sessions()
    
    # Display the banner
    print_iraq_banner()
    
    # Show loading animation
    show_download_progress()
    
    # Check for updates (unless disabled in config)
    if config.get('check_updates', True):
        check_for_updates()
    
    # Process utility commands first (no prompt required)
    
    # If checking for updates
    if args.check_updates:
        print(f"{Colors.BLUE}Current version: {Colors.BOLD}{__version__}{Colors.END}")
        print(f"{Colors.GREEN}Checking for updates...{Colors.END}")
        check_for_updates(force_display=True)
        return
    
    # If setting configuration via command line
    if args.config:
        parts = args.config.split('=', 1)
        if len(parts) == 2:
            key, value = parts
            handle_config_command(f"set {key} {value}")
        else:
            print(f"{Colors.YELLOW}Usage: --config KEY=VALUE{Colors.END}")
            print(f"{Colors.YELLOW}Example: --config model=llama2{Colors.END}")
        return
        
    # If showing status
    if args.status:
        display_system_status()
        return
        
    # If listing models
    if args.list_models:
        list_models()
        return
    
    # If starting interactive shell
    if args.shell:
        # Create a session ID for this shell
        session_id = f"shell_{int(time.time())}"
        
        # Register the session
        save_session(session_id, {
            "type": "interactive_shell",
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pid": os.getpid()
        })
        
        try:
            # Start the interactive shell
            start_interactive_shell(
                auto_mode_enabled=args.auto,
                current_model=args.model,
                current_temperature=config.get('temperature', 0.7),
                max_attempts=config.get('max_attempts', 3)
            )
        finally:
            # Clean up the session
            end_session(session_id)
            
        return
        
    # Handle log analysis
    if args.logs:
        handle_log_analysis(args.model)
        return
        
    if args.all_logs:
        log_files = find_log_files(include_system=True)
        if log_files:
            print(f"{Colors.GREEN}Found {len(log_files)} log files:{Colors.END}")
            selected_log = display_log_selection(log_files)
            if selected_log:
                handle_log_selection(selected_log, args.model)
        else:
            print(f"{Colors.YELLOW}No accessible log files found on the system.{Colors.END}")
        return
        
    if args.analyze_file:
        if os.path.exists(args.analyze_file) and os.path.isfile(args.analyze_file):
            analyze_log_file(args.analyze_file, args.model, False, True)
        else:
            print(f"{Colors.RED}Error: File {args.analyze_file} does not exist or is not accessible.{Colors.END}")
        return
        
    if args.monitor:
        file_path = os.path.abspath(args.monitor)
        # Create the file if it doesn't exist
        if not os.path.exists(file_path):
            try:
                # Create an empty file
                with open(file_path, 'w') as f:
                    pass
                print(f"{Colors.GREEN}Created new log file: {file_path}{Colors.END}")
            except Exception as e:
                print(f"{Colors.RED}Error creating file {file_path}: {e}{Colors.END}")
                return
        
        if os.path.isfile(file_path):
            analyze_log_file(file_path, args.model, True, True)
        else:
            print(f"{Colors.RED}Error: {file_path} is not a regular file.{Colors.END}")
        return
        
    if args.watch:
        file_path = os.path.abspath(args.watch)
        # Create the file if it doesn't exist
        if not os.path.exists(file_path):
            try:
                # Create an empty file
                with open(file_path, 'w') as f:
                    pass
                print(f"{Colors.GREEN}Created new log file: {file_path}{Colors.END}")
            except Exception as e:
                print(f"{Colors.RED}Error creating file {file_path}: {e}{Colors.END}")
                return
                
        if os.path.isfile(file_path):
            analyze_log_file(file_path, args.model, True, False)
        else:
            print(f"{Colors.RED}Error: {file_path} is not a regular file.{Colors.END}")
        return
    
    # Ensure a prompt is provided for command generation
    if not args.prompt:
        parser = argparse.ArgumentParser()
        parser.print_help()
        print_examples()
        return
    
    # Generate the command
    print(f"Generating command for: {args.prompt}")
    command = generate_command(args.prompt, args.model)
    
    # Save to history
    save_to_history(args.prompt)
    
    # Display the generated command
    print(f"\nGenerated Command: {command}")
    
    # Handle execution based on flags
    if args.dry_run:
        # Just show the command without executing
        print("\nDry run - command not executed")
    elif args.yes:
        # Quick confirmation before execution
        print(f"\nAbout to execute: {command}")
        response = input("Press Enter to continue or Ctrl+C to cancel...")
        execute_command(command, args.analyze, args.model)
    elif args.execute:
        # Execute with confirmation
        response = input("\nDo you want to execute this command? (y/n): ").lower()
        if response in ["y", "yes"]:
            execute_command(command, args.analyze, args.model)
        else:
            print("Command execution cancelled.")
    elif args.auto:
        # Auto mode: generate, execute, and fix
        auto_mode(args.prompt, args.model)
    else:
        # Just ask if user wants to execute
        response = input("\nDo you want to execute this command? (y/n): ").lower()
        if response in ["y", "yes"]:
            execute_command(command, args.analyze, args.model)
        else:
            print("Command execution cancelled.")

def parse_args():
    """
    Parse command line arguments
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Command Generator Tool with AI analysis capabilities")
    parser.add_argument('prompt', nargs='?', 
                        help='Describe the command you want to generate')
    
    # Model selection
    parser.add_argument('--model', type=str, default=None,
                        help=f'Model to use (default: {DEFAULT_MODEL})')
    parser.add_argument('--list-models', action='store_true',
                        help='List available models')
    
    # Execution options
    parser.add_argument('--execute', action='store_true',
                        help='Execute the generated command (with confirmation)')
    parser.add_argument('--yes', action='store_true',
                        help='Execute command without confirmation')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print the command without executing it')
    parser.add_argument('--analyze', action='store_true',
                        help='Analyze command output and provide assistance with errors')
    
    # Special modes
    parser.add_argument('--auto', action='store_true',
                        help='Auto mode: keep fixing errors until command succeeds')
    parser.add_argument('--shell', action='store_true',
                        help='Start interactive shell for multiple commands')
    parser.add_argument('--check-updates', action='store_true',
                        help='Check for package updates')
    
    # Configuration
    parser.add_argument('--config', type=str, metavar='KEY=VALUE',
                        help='Set configuration option (e.g., --config model=llama2)')
    
    # Log analysis
    parser.add_argument('--logs', action='store_true',
                        help='List log files for analysis')
    parser.add_argument('--all-logs', action='store_true',
                        help='List all log files including system logs')
    parser.add_argument('--analyze-file', type=str, metavar='FILE',
                        help='Analyze the specified file')
    parser.add_argument('--monitor', type=str, metavar='FILE',
                        help='Monitor log file for changes and analyze them')
    parser.add_argument('--watch', type=str, metavar='FILE',
                        help='Watch log file for changes without AI analysis')
    
    # System status
    parser.add_argument('--status', action='store_true',
                        help='Show QCMD system status')
                        
    # UI customization options
    parser.add_argument('--no-banner', action='store_true',
                        help='Disable the IRAQ banner display')
    parser.add_argument('--no-progress', action='store_true',
                        help='Disable progress bar animations')
    parser.add_argument('--compact', action='store_true',
                        help='Enable compact mode for minimal output')
    parser.add_argument('--banner-font', type=str,
                        help='Set the font to use for the banner (pyfiglet font name)')
    
    args = parser.parse_args()
    
    # Load config
    config = load_config()
    
    # Apply UI customization options to config
    if args.no_banner:
        config['ui']['show_iraq_banner'] = False
    if args.no_progress:
        config['ui']['show_progress_bar'] = False
    if args.compact:
        config['ui']['compact_mode'] = True
    if args.banner_font:
        config['ui']['banner_font'] = args.banner_font
        
    # Save config if UI options were changed
    if args.no_banner or args.no_progress or args.compact or args.banner_font:
        save_config(config)
    
    return args

def is_dangerous_command(command: str) -> bool:
    """
    Check if a command contains potentially dangerous patterns.
    
    Args:
        command: The command to check
        
    Returns:
        True if the command is potentially dangerous, False otherwise
    """
    command_lower = command.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in command_lower:
            return True
    return False

def get_system_status():
    """
    Get system status information, suitable for JSON output
    
    Returns:
        Dictionary with system status information
    """
    status = {
        "os": os.name,
        "python_version": sys.version.split()[0],
        "qcmd_version": __version__,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    
    # Check if Ollama service is running
    try:
        response = requests.get(f"{OLLAMA_API}/tags", timeout=2)
        status["ollama"] = {
            "status": "running" if response.status_code == 200 else "error",
            "api_url": OLLAMA_API,
        }
        # Get available models
        if response.status_code == 200:
            try:
                models = response.json().get("models", [])
                status["ollama"]["models"] = [model["name"] for model in models]
            except:
                status["ollama"]["models"] = []
    except:
        status["ollama"] = {
            "status": "not running",
            "api_url": OLLAMA_API,
        }
    
    # Clean up stale monitors first
    active_monitors = cleanup_stale_monitors()
    
    # Get active log monitors from persistent storage
    status["active_monitors"] = list(active_monitors.keys())
    
    # Clean up stale sessions
    active_sessions = cleanup_stale_sessions()
    
    # Get active sessions from persistent storage
    status["active_sessions"] = list(active_sessions.keys())
    status["sessions_info"] = active_sessions
    
    # Check disk space where logs are stored
    log_dir = "/var/log"
    if os.path.exists(log_dir):
        try:
            total, used, free = shutil.disk_usage(log_dir)
            status["disk"] = {
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2),
                "percent_used": round((used / total) * 100, 2),
            }
        except:
            pass
    
    return status

def check_ollama_status():
    """
    Check if Ollama service is running and get available models.
    
    Returns:
        Tuple of (status_string, api_url, model_list)
    """
    status = "Not running"
    api_url = OLLAMA_API
    models = []
    
    try:
        # Try to connect to Ollama API with a short timeout
        response = requests.get(f"{OLLAMA_API}/tags", timeout=2)
        
        if response.status_code == 200:
            status = "Running"
            # Get available models if successful
            try:
                models_data = response.json().get("models", [])
                models = [model["name"] for model in models_data]
            except (KeyError, json.JSONDecodeError):
                # If we can't parse the models, just leave the list empty
                pass
    except requests.exceptions.RequestException:
        # Any request exception means Ollama is not running or not accessible
        pass
        
    return status, api_url, models

def display_system_status():
    """
    Display system and qcmd status information
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    config = load_config()
    
    # System information header
    print(f"\n{Colors.BOLD}╔══════════════════════════════════════ QCMD SYSTEM STATUS ══════════════════════════════════════╗{Colors.END}")
    
    # System information section
    print(f"\n{Colors.CYAN}{Colors.BOLD}► SYSTEM INFORMATION{Colors.END}")
    print(f"  {Colors.BOLD}•{Colors.END} OS: {Colors.YELLOW}{os.name}{Colors.END}")
    print(f"  {Colors.BOLD}•{Colors.END} Python Version: {Colors.YELLOW}{platform.python_version()}{Colors.END}")
    print(f"  {Colors.BOLD}•{Colors.END} QCMD Version: {Colors.YELLOW}{__version__}{Colors.END}")
    print(f"  {Colors.BOLD}•{Colors.END} Current Time: {Colors.YELLOW}{current_time}{Colors.END}")
    
    # Ollama status section
    print(f"\n{Colors.CYAN}{Colors.BOLD}► OLLAMA STATUS{Colors.END}")
    ollama_status, api_url, models = check_ollama_status()
    print(f"  {Colors.BOLD}•{Colors.END} Status: {Colors.GREEN if ollama_status else Colors.RED}{ollama_status}{Colors.END}")
    print(f"  {Colors.BOLD}•{Colors.END} API URL: {Colors.YELLOW}{api_url}{Colors.END}")
    if models:
        models_str = ", ".join(models)
        print(f"  {Colors.BOLD}•{Colors.END} Available Models: {Colors.YELLOW}{models_str}{Colors.END}")
    else:
        print(f"  {Colors.BOLD}•{Colors.END} Available Models: {Colors.RED}None found{Colors.END}")
    
    # Log monitors section
    print(f"\n{Colors.CYAN}{Colors.BOLD}► ACTIVE LOG MONITORS{Colors.END}")
    active_monitors = cleanup_stale_monitors()
    if active_monitors:
        for monitor_id, info in active_monitors.items():
            file_path = info.get("file_path", "Unknown")
            pid = info.get("pid", "Unknown")
            analyze = info.get("analyze", False)
            mode = "AI Analysis" if analyze else "Watch Only"
            print(f"  {Colors.BOLD}•{Colors.END} Monitor {Colors.YELLOW}{monitor_id}{Colors.END}: {file_path} ({Colors.GREEN}{mode}{Colors.END}, PID: {pid})")
    else:
        print(f"  {Colors.YELLOW}No active log monitors.{Colors.END}")
    
    # Active sessions section
    print(f"\n{Colors.CYAN}{Colors.BOLD}► ACTIVE SESSIONS{Colors.END}")
    active_sessions = cleanup_stale_sessions()
    if active_sessions:
        for session_id, info in active_sessions.items():
            session_type = info.get("type", "Unknown")
            start_time = info.get("start_time", "Unknown")
            pid = info.get("pid", "Unknown")
            print(f"  {Colors.BOLD}•{Colors.END} Session {Colors.YELLOW}{session_id}{Colors.END}: {session_type} (Started: {start_time}, PID: {pid})")
    else:
        print(f"  {Colors.YELLOW}No active sessions.{Colors.END}")
    
    # Disk space section
    print(f"\n{Colors.CYAN}{Colors.BOLD}► DISK SPACE (LOG DIRECTORY){Colors.END}")
    if os.path.exists(CONFIG_DIR):
        total, used, free = shutil.disk_usage(CONFIG_DIR)
        total_gb = total / (1024**3)
        used_gb = used / (1024**3)
        free_gb = free / (1024**3)
        percent = used / total * 100
        
        # Progress bar for disk usage
        bar_width = 30
        filled_length = int(bar_width * percent / 100)
        bar = f"{Colors.GREEN}{'█' * filled_length}{Colors.YELLOW}{'░' * (bar_width - filled_length)}{Colors.END}"
        
        print(f"  {Colors.BOLD}•{Colors.END} Total: {Colors.YELLOW}{total_gb:.2f} GB{Colors.END}")
        print(f"  {Colors.BOLD}•{Colors.END} Used: {Colors.YELLOW}{used_gb:.2f} GB{Colors.END} ({percent:.2f}%)")
        print(f"  {Colors.BOLD}•{Colors.END} Free: {Colors.YELLOW}{free_gb:.2f} GB{Colors.END}")
        print(f"  {Colors.BOLD}•{Colors.END} Usage: [{bar}]")
    else:
        print(f"  {Colors.RED}Cannot determine disk usage.{Colors.END}")
    
    # Configuration section
    print(f"\n{Colors.CYAN}{Colors.BOLD}► CONFIGURATION{Colors.END}")
    print(f"  {Colors.BOLD}•{Colors.END} Default Model: {Colors.YELLOW}{config.get('model', DEFAULT_MODEL)}{Colors.END}")
    print(f"  {Colors.BOLD}•{Colors.END} Temperature: {Colors.YELLOW}{config.get('temperature', 0.7)}{Colors.END}")
    print(f"  {Colors.BOLD}•{Colors.END} Max Attempts: {Colors.YELLOW}{config.get('max_attempts', 3)}{Colors.END}")
    print(f"  {Colors.BOLD}•{Colors.END} Banner Font: {Colors.YELLOW}{config.get('ui', {}).get('banner_font', 'slant')}{Colors.END}")
    print(f"  {Colors.BOLD}•{Colors.END} Show Banner: {Colors.GREEN if config.get('ui', {}).get('show_iraq_banner', True) else Colors.RED}{config.get('ui', {}).get('show_iraq_banner', True)}{Colors.END}")
    print(f"  {Colors.BOLD}•{Colors.END} Compact Mode: {Colors.GREEN if config.get('ui', {}).get('compact_mode', False) else Colors.RED}{config.get('ui', {}).get('compact_mode', False)}{Colors.END}")
    
    # Status footer
    print(f"\n{Colors.BOLD}╚═════════════════════════════════════════════════════════════════════════════════════════════════╝{Colors.END}")
    print()

def save_session(session_id, session_info):
    """
    Save session information to persistent storage.
    """
    try:
        # Create config directory if it doesn't exist
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR, exist_ok=True)
        
        # Load existing sessions
        sessions = {}
        if os.path.exists(SESSIONS_FILE):
            with open(SESSIONS_FILE, 'r') as f:
                try:
                    sessions = json.load(f)
                except json.JSONDecodeError:
                    pass
        
        # Update with new session
        sessions[session_id] = session_info
        
        # Write back to file
        with open(SESSIONS_FILE, 'w') as f:
            json.dump(sessions, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving session: {e}", file=sys.stderr)
        return False

def load_sessions():
    """
    Load sessions from persistent storage.
    """
    sessions = {}
    try:
        if os.path.exists(SESSIONS_FILE):
            with open(SESSIONS_FILE, 'r') as f:
                try:
                    sessions = json.load(f)
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        print(f"Error loading sessions: {e}", file=sys.stderr)
    
    return sessions

def cleanup_stale_sessions():
    """
    Remove sessions for processes that are no longer running.
    """
    sessions = load_sessions()
    active_sessions = {}
    
    for session_id, session_info in sessions.items():
        pid = session_info.get('pid')
        if pid and is_process_running(pid):
            active_sessions[session_id] = session_info
    
    # Write cleaned sessions back to file
    try:
        with open(SESSIONS_FILE, 'w') as f:
            json.dump(active_sessions, f, indent=2)
    except Exception as e:
        print(f"Error saving cleaned sessions: {e}", file=sys.stderr)
    
    return active_sessions

def end_session(session_id):
    """
    Remove a specific session.
    """
    try:
        sessions = load_sessions()
        if session_id in sessions:
            del sessions[session_id]
            
            with open(SESSIONS_FILE, 'w') as f:
                json.dump(sessions, f, indent=2)
        
        # Also remove from in-memory cache
        if session_id in ACTIVE_SESSIONS:
            del ACTIVE_SESSIONS[session_id]
            
        return True
    except Exception as e:
        print(f"Error ending session: {e}", file=sys.stderr)
        return False

def is_process_running(pid):
    """
    Check if a process with the given PID is running.
    
    Args:
        pid: Process ID to check
        
    Returns:
        True if process is running, False otherwise
    """
    try:
        pid = int(pid)  # Ensure pid is an integer
        # For Unix/Linux/MacOS
        if os.name == 'posix':
            # A simple check using kill with signal 0
            # which doesn't actually send a signal
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False
        # For Windows
        elif os.name == 'nt':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            SYNCHRONIZE = 0x00100000
            process = kernel32.OpenProcess(SYNCHRONIZE, 0, pid)
            if process != 0:
                kernel32.CloseHandle(process)
                return True
            else:
                return False
        else:
            # Unknown OS
            return False
    except (ValueError, TypeError):
        return False

def display_help_command(current_model: str, current_temperature: float, auto_mode_enabled: bool, max_attempts: int) -> None:
    """
    Display a professional help message for the interactive shell
    
    Args:
        current_model: Current AI model in use
        current_temperature: Current temperature setting
        auto_mode_enabled: Whether auto mode is enabled
        max_attempts: Maximum attempts for auto fix mode
    """
    # Display a professional help message with organized sections
    print(f"\n{Colors.BOLD}╔══════════════════════════════════════════════════════════════════╗{Colors.END}")
    print(f"{Colors.BOLD}║{Colors.END} {Colors.CYAN}QCMD Interactive Shell - Command Reference{Colors.END}                {Colors.BOLD}║{Colors.END}")
    print(f"{Colors.BOLD}╚══════════════════════════════════════════════════════════════════╝{Colors.END}")
    
    # Command Generation section
    print(f"\n{Colors.CYAN}{Colors.BOLD}Command Generation:{Colors.END}")
    print(f"  {Colors.BOLD}/auto{Colors.END}                Enable auto mode (auto-execute & fix errors)")
    print(f"  {Colors.BOLD}/model <name>{Colors.END}        Switch to a different AI model")
    print(f"  {Colors.BOLD}/temperature <value>{Colors.END} Set temperature (0.0-1.0) for generation")
    
    # Log Analysis section
    print(f"\n{Colors.CYAN}{Colors.BOLD}Log Analysis:{Colors.END}")
    print(f"  {Colors.BOLD}/logs{Colors.END}                Find and analyze logs")
    print(f"  {Colors.BOLD}/all-logs{Colors.END}            Show all accessible log files")
    print(f"  {Colors.BOLD}/analyze-file <path>{Colors.END} Analyze a specific file")
    print(f"  {Colors.BOLD}/monitor <path>{Colors.END}      Monitor file with AI analysis")
    print(f"  {Colors.BOLD}/watch <path>{Colors.END}        Watch file without AI analysis")
    
    # System & Configuration section
    print(f"\n{Colors.CYAN}{Colors.BOLD}System & Configuration:{Colors.END}")
    print(f"  {Colors.BOLD}/status{Colors.END}              Display system status and active monitors")
    print(f"  {Colors.BOLD}/config{Colors.END}              Show or modify configuration")
    print(f"  {Colors.BOLD}/config set <key> <value>{Colors.END} Set a configuration value")
    print(f"  {Colors.BOLD}/config reset{Colors.END}        Reset configuration to defaults")
    
    # Utility Commands
    print(f"\n{Colors.CYAN}{Colors.BOLD}Utility Commands:{Colors.END}")
    print(f"  {Colors.BOLD}/history{Colors.END}             Show command history")
    print(f"  {Colors.BOLD}/clear{Colors.END}               Clear the screen")
    print(f"  {Colors.BOLD}/exit{Colors.END}, {Colors.BOLD}/quit{Colors.END}     Exit the shell")
    
    # Tips & Shortcuts section
    print(f"\n{Colors.CYAN}{Colors.BOLD}Tips & Shortcuts:{Colors.END}")
    print(f"  • Use {Colors.BOLD}Tab{Colors.END} for command completion")
    print(f"  • Type commands in natural language (e.g., \"list all files\")")
    print(f"  • Enable auto mode with {Colors.BOLD}/auto{Colors.END} for automatic error fixing")
    print(f"  • Customize colors and UI with {Colors.BOLD}/config{Colors.END} command")
    
    # Display current settings
    print(f"\n{Colors.YELLOW}{Colors.BOLD}Current Settings:{Colors.END}")
    print(f"  Model: {Colors.BOLD}{current_model}{Colors.END}")
    print(f"  Temperature: {Colors.BOLD}{current_temperature}{Colors.END}")
    print(f"  Auto mode: {Colors.BOLD}{'Enabled' if auto_mode_enabled else 'Disabled'}{Colors.END}")
    print(f"  Max fix attempts: {Colors.BOLD}{max_attempts}{Colors.END}")

if __name__ == "__main__":
    main() 