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
    ██████╗   ██████╗ ███╗   ███╗██████╗ 
    ██╔═══██╗██╔════╝ ████╗ ████║██╔══██╗
    ██║   ██║██║      ██╔████╔██║██║  ██║
    ██║▄▄ ██║██║      ██║╚██╔╝██║██║  ██║
    ╚██████╔╝╚██████╗ ██║ ╚═╝ ██║██████╔╝
     ╚══▀▀═╝  ╚═════╝ ╚═╝     ╚═╝╚═════╝ 
    """
    
    subtitle = "AI-Powered Command Generator"
    
    print(f"{Colors.GREEN}{header}{Colors.END}")
    print(f"{Colors.YELLOW}{Colors.BOLD}{subtitle.center(55)}{Colors.END}\n")

def print_examples():
    """
    Print example commands that can be used with QCMD.
    """
    examples = [
        ("qcmd 'list files by size'", "List files sorted by size"),
        ("qcmd --auto 'find text'", "Auto-fix search command"),
        ("qcmd --shell", "Interactive shell mode"),
        ("qcmd --model llama3", "Use specific model")
    ]
    
    print(f"{Colors.CYAN}Quick Examples:{Colors.END}")
    print(f"{Colors.BLUE}{'─' * 60}{Colors.END}")
    for cmd, desc in examples:
        print(f"{Colors.GREEN}{cmd.ljust(30)}{Colors.END} {desc}")
    print(f"{Colors.BLUE}{'─' * 60}{Colors.END}\n")

def print_iraq_banner():
    """
    Print minimalist banner.
    """
    # Print just a minimal indicator
    print(f"\n{Colors.BOLD}Initializing QCMD...{Colors.END}\n")

def show_download_progress(total=10, message="Loading QCMD..."):
    """
    Display a progress bar with a simple design.
    
    Args:
        total: Total number of steps
        message: Message to display with the progress bar
    """
    # Get terminal width
    term_width = shutil.get_terminal_size().columns
    bar_width = min(term_width - 10, 40)
    
    for i in range(total + 1):
        progress = i / total
        bar_length = int(bar_width * progress)
        
        # Create a simple progress bar
        bar = f"{Colors.GREEN}{'█' * bar_length}{' ' * (bar_width - bar_length)}{Colors.END}"
                
        # Calculate percentage
        percent = progress * 100
        
        # Print the progress bar
        sys.stdout.write(f"\r{message} [{bar}] {percent:.0f}%")
        sys.stdout.flush()
        
        # Shorter delay for better user experience
        time.sleep(0.05)
        
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
{Colors.GREEN}QCMD Interactive Shell{Colors.END}
{Colors.BLUE}{'─' * 50}{Colors.END}

{Colors.CYAN}Settings:{Colors.END}
• Model: {Colors.YELLOW}{current_model}{Colors.END}
• Temp: {Colors.YELLOW}{current_temperature}{Colors.END}
• Auto: {Colors.YELLOW}{'On' if auto_mode_enabled else 'Off'}{Colors.END}

{Colors.CYAN}Commands:{Colors.END}
{Colors.YELLOW}!help{Colors.END}      Show help
{Colors.YELLOW}!exit{Colors.END}      Exit shell
{Colors.YELLOW}!history{Colors.END}   Command history
{Colors.YELLOW}!clear{Colors.END}     Clear screen
{Colors.YELLOW}!model{Colors.END} X   Change model
{Colors.YELLOW}!temp{Colors.END} X    Set temperature
{Colors.YELLOW}!auto{Colors.END} X    Toggle auto mode
{Colors.YELLOW}!update{Colors.END}    Check updates
{Colors.YELLOW}!!{Colors.END}         Repeat last command

{Colors.CYAN}Usage:{Colors.END} Type a command description and press Enter
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