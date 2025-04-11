#!/usr/bin/env python3
"""
UI display functionality for QCMD.
"""
import os
import sys
import time
import re
import shutil
from typing import Dict, List, Optional, Any

class Colors:
    """
    Color codes for terminal output.
    """
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
        """
        Load color settings from configuration.
        
        Args:
            config: Configuration dictionary containing color settings
        """
        if 'colors' in config:
            for color_name, color_value in config['colors'].items():
                if hasattr(cls, color_name.upper()) and color_value:
                    setattr(cls, color_name.upper(), color_value)
        
    @classmethod
    def reset_to_defaults(cls):
        """
        Reset all colors to their default values.
        """
        for color_name, color_value in cls._DEFAULTS.items():
            setattr(cls, color_name, color_value)
        
    @classmethod
    def get_all_colors(cls):
        """
        Get all current color values as a dictionary.
        
        Returns:
            Dictionary of color names and their current values
        """
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

def print_cool_header():
    """
    Print the cool ASCII art header for QCMD.
    """
    header = """
    ██████╗  ██████╗███╗   ███╗██████╗ 
   ██╔═══██╗██╔════╝████╗ ████║██╔══██╗
   ██║   ██║██║     ██╔████╔██║██║  ██║
   ██║▄▄ ██║██║     ██║╚██╔╝██║██║  ██║
   ╚██████╔╝╚██████╗██║ ╚═╝ ██║██████╔╝
    ╚══▀▀═╝  ╚═════╝╚═╝     ╚═╝╚═════╝ 
    """
    
    subtitle = "Iraqi Excellence in Command Generation"
    
    print(f"{Colors.GREEN}{header}{Colors.END}")
    print(f"{Colors.YELLOW}{Colors.BOLD}{subtitle.center(50)}{Colors.END}\n")

def print_examples():
    """
    Print example commands that can be used with QCMD.
    """
    examples = [
        ("qcmd 'list files sorted by size'", "Generate a command to list files by size"),
        ("qcmd --auto 'find text in files'", "Generate and auto-fix command to find text"),
        ("qcmd logs", "Analyze log files with AI"),
        ("qcmd --model llama3 'backup files'", "Use a specific model"),
        ("qcmd --shell", "Start interactive shell mode"),
        ("qcmd --status", "Display system status"),
        ("qcmd --history", "Show command history"),
        ("qcmd --update-check", "Check for updates")
    ]
    
    print(f"{Colors.CYAN}{Colors.BOLD}Example commands:{Colors.END}")
    print("-" * 80)
    for cmd, desc in examples:
        print(f"{Colors.GREEN}{cmd.ljust(40)}{Colors.END} {desc}")
    print("-" * 80 + "\n")

def print_iraq_banner():
    """
    Print Iraqi-themed banner.
    """
    # Iraqi flag colors in ASCII
    red = f"{Colors.RED}█{Colors.END}"
    white = f"{Colors.WHITE}█{Colors.END}"
    black = f"{Colors.BLACK}█{Colors.END}"
    
    # Print a mini version of the Iraqi flag
    print("\nIraqi-Powered Command Generation")
    print(f"{red * 20}")
    print(f"{white * 20}")
    print(f"{black * 20}\n")

def show_download_progress(total=20, message="Initializing QCMD with Iraqi excellence"):
    """
    Display a progress bar with Iraqi flag colors.
    
    Args:
        total: Total number of steps
        message: Message to display with the progress bar
    """
    # Iraqi flag colors
    colors = [Colors.RED, Colors.WHITE, Colors.BLACK]
    
    print(f"\n{message}")
    
    # Get terminal width
    term_width = shutil.get_terminal_size().columns
    bar_width = min(term_width - 10, 50)
    
    for i in range(total + 1):
        progress = i / total
        bar_length = int(bar_width * progress)
        
        # Create the progress bar with Iraqi flag colors
        bar = ""
        for j in range(bar_width):
            if j < bar_length:
                # Cycle through the colors
                color_idx = (j // 3) % len(colors)
                bar += f"{colors[color_idx]}█{Colors.END}"
            else:
                bar += " "
                
        # Calculate percentage
        percent = progress * 100
        
        # Print the progress bar
        sys.stdout.write(f"\r[{bar}] {percent:.1f}%")
        sys.stdout.flush()
        
        time.sleep(0.1)
        
    # End with a newline
    print("\n")

def display_help_command(current_model: str, current_temperature: float, auto_mode_enabled: bool, max_attempts: int) -> None:
    """
    Display help information for the interactive shell.
    
    Args:
        current_model: Currently selected model
        current_temperature: Current temperature setting
        auto_mode_enabled: Whether auto mode is enabled
        max_attempts: Maximum number of auto-correction attempts
    """
    help_text = f"""
{Colors.GREEN}{Colors.BOLD}QCMD Interactive Shell Help{Colors.END}
{'-' * 50}

{Colors.CYAN}{Colors.BOLD}Current Settings:{Colors.END}
- Model: {Colors.YELLOW}{current_model}{Colors.END}
- Temperature: {Colors.YELLOW}{current_temperature}{Colors.END}
- Auto-correction: {Colors.YELLOW}{'Enabled' if auto_mode_enabled else 'Disabled'}{Colors.END}
- Max auto attempts: {Colors.YELLOW}{max_attempts}{Colors.END}

{Colors.CYAN}{Colors.BOLD}Available Commands:{Colors.END}
{Colors.YELLOW}!help{Colors.END}          - Show this help message
{Colors.YELLOW}!exit{Colors.END}, {Colors.YELLOW}!quit{Colors.END}    - Exit the shell
{Colors.YELLOW}!history{Colors.END}       - Show command history
{Colors.YELLOW}!search{Colors.END} term   - Search command history
{Colors.YELLOW}!clear{Colors.END}         - Clear the screen
{Colors.YELLOW}!status{Colors.END}        - Show system status
{Colors.YELLOW}!models{Colors.END}        - List available models
{Colors.YELLOW}!model{Colors.END} name    - Change the model
{Colors.YELLOW}!temp{Colors.END} value    - Set temperature (0.0-1.0)
{Colors.YELLOW}!auto{Colors.END} on/off   - Enable/disable auto-correction
{Colors.YELLOW}!max{Colors.END} value     - Set max auto-correction attempts
{Colors.YELLOW}!update{Colors.END}        - Check for updates
{Colors.YELLOW}!logs{Colors.END}          - Analyze log files
{Colors.YELLOW}!!{Colors.END}             - Repeat last command

{Colors.CYAN}{Colors.BOLD}Usage:{Colors.END}
- Type a natural language description of what you want to do
- The AI will generate a command for you
- The command will be displayed but not executed automatically
- Type 'y' to execute, 'n' to reject, or edit the command
- Use !exit or Ctrl+D to quit
"""
    print(help_text)

def clear_screen():
    """
    Clear the terminal screen.
    """
    # Clear command based on OS
    if os.name == 'nt':  # For Windows
        os.system('cls')
    else:  # For Linux/Mac
        os.system('clear')

def display_system_status(status: Dict[str, Any]) -> None:
    """
    Display detailed system status information.
    
    Args:
        status: Dictionary with system status information
    """
    # Print divider line
    print(f"\n{Colors.CYAN}{'-' * 80}{Colors.END}")
    
    # System information
    print(f"\n{Colors.RED}{Colors.BOLD}System Information:{Colors.END}")
    print(f"  {Colors.BLUE}OS:{Colors.END} {status.get('os', 'Unknown')}")
    print(f"  {Colors.BLUE}Python Version:{Colors.END} {status.get('python_version', 'Unknown')}")
    print(f"  {Colors.BLUE}QCMD Version:{Colors.END} {status.get('qcmd_version', 'Unknown')}")
    print(f"  {Colors.BLUE}Current Time:{Colors.END} {status.get('time', 'Unknown')}")
    
    # Ollama information
    if 'ollama' in status:
        ollama = status['ollama']
        print(f"\n{Colors.RED}{Colors.BOLD}Ollama Status:{Colors.END}")
        
        # Check if Ollama is running
        if ollama.get('status', '') == 'running':
            print(f"  {Colors.BLUE}Status:{Colors.END} {Colors.GREEN}Running{Colors.END}")
        else:
            print(f"  {Colors.BLUE}Status:{Colors.END} {Colors.RED}Not Running{Colors.END}")
            if 'error' in ollama:
                print(f"  {Colors.BLUE}Error:{Colors.END} {ollama['error']}")
        
        print(f"  {Colors.BLUE}API URL:{Colors.END} {ollama.get('api_url', 'Unknown')}")
        
        # List available models
        if 'models' in ollama and ollama['models']:
            print(f"  {Colors.BLUE}Available Models:{Colors.END}")
            for model in ollama['models']:
                print(f"    - {model}")
        elif ollama.get('status', '') == 'running':
            print(f"  {Colors.BLUE}Available Models:{Colors.END} No models found")
    
    # Active monitors
    if 'active_monitors' in status and status['active_monitors']:
        print(f"\n{Colors.RED}{Colors.BOLD}Active Log Monitors:{Colors.END}")
        for monitor in status['active_monitors']:
            print(f"  - {monitor}")
    
    # Active sessions
    if 'active_sessions' in status and status['active_sessions']:
        print(f"\n{Colors.RED}{Colors.BOLD}Active Sessions:{Colors.END}")
        for session in status['active_sessions']:
            print(f"  - {session}")
    
    # Disk space
    if 'disk' in status:
        disk = status['disk']
        print(f"\n{Colors.RED}{Colors.BOLD}Disk Space:{Colors.END}")
        print(f"  {Colors.BLUE}Total:{Colors.END} {disk.get('total_gb', 'Unknown')} GB")
        print(f"  {Colors.BLUE}Used:{Colors.END} {disk.get('used_gb', 'Unknown')} GB ({disk.get('percent_used', 'Unknown')}%)")
        print(f"  {Colors.BLUE}Free:{Colors.END} {disk.get('free_gb', 'Unknown')} GB")
    
    print(f"\n{Colors.CYAN}{'-' * 80}{Colors.END}") 