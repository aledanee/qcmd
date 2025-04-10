#!/usr/bin/env python3
"""
UI display module for formatting terminal output in QCMD.
"""

import os
import sys
import textwrap
import time
from typing import List, Dict, Any
from datetime import datetime

# Import Colors from dedicated module
from qcmd_cli.ui.colors import Colors

def print_cool_header():
    """Print a cool header for the application."""
    from qcmd_cli import __version__
    
    # Get terminal width
    try:
        term_width = os.get_terminal_size().columns
    except (AttributeError, OSError):
        term_width = 80
    
    # Adjust based on available width
    if term_width < 60:
        # Simplified header for narrow terminals
        print(f"\n{Colors.CYAN}===== QCMD v{__version__} ====={Colors.END}")
        return
    
    header = f"""
{Colors.CYAN}╔═════════════════════════════════════════════════════════════╗
║                                                             ║
║   {Colors.BOLD}  ██████╗  ██████╗███╗   ███╗██████╗    {Colors.CYAN}               ║
║   {Colors.BOLD} ██╔═══██╗██╔════╝████╗ ████║██╔══██╗   {Colors.CYAN}               ║
║   {Colors.BOLD} ██║   ██║██║     ██╔████╔██║██║  ██║   {Colors.CYAN}               ║
║   {Colors.BOLD} ██║▄▄ ██║██║     ██║╚██╔╝██║██║  ██║   {Colors.CYAN}               ║
║   {Colors.BOLD} ╚██████╔╝╚██████╗██║ ╚═╝ ██║██████╔╝   {Colors.CYAN}               ║
║   {Colors.BOLD}  ╚══▀▀═╝  ╚═════╝╚═╝     ╚═╝╚═════╝    {Colors.CYAN}               ║
║                                              v{__version__}        ║
║                                                             ║
╚═════════════════════════════════════════════════════════════╝{Colors.END}"""

    print(header)

def format_command_output(output: str, compact: bool = False) -> str:
    """
    Format command output for display.
    
    Args:
        output: Command output to format
        compact: Whether to use compact mode (shorter output)
        
    Returns:
        Formatted output
    """
    # Truncate long output in compact mode
    if compact and len(output) > 2000:
        first_part = output[:1000]
        last_part = output[-1000:]
        return f"{first_part}\n\n[...output truncated...]\n\n{last_part}"
    
    return output

def format_command_for_display(command: str) -> str:
    """
    Format a command for display with proper coloring.
    
    Args:
        command: Command to format
        
    Returns:
        Formatted command for display
    """
    return f"{Colors.GREEN}{command}{Colors.END}"

def print_command_analysis(analysis: str):
    """
    Print command analysis with nice formatting.
    
    Args:
        analysis: Analysis text to print
    """
    try:
        term_width = os.get_terminal_size().columns - 4
    except (AttributeError, OSError):
        term_width = 76
    
    print(f"\n{Colors.CYAN}Analysis:{Colors.END}")
    
    # Format with word wrap
    wrapped_text = textwrap.fill(analysis, width=term_width)
    
    # Print with left padding
    for line in wrapped_text.split('\n'):
        print(f"  {line}")

def display_log_files(log_files: List[str], favorite_logs: List[str] = None) -> None:
    """
    Display a list of log files for selection.
    
    Args:
        log_files: List of log file paths
        favorite_logs: List of favorite log file paths
    """
    if not log_files:
        print(f"{Colors.YELLOW}No log files found.{Colors.END}")
        return
    
    favorite_logs = favorite_logs or []
    
    print(f"\n{Colors.CYAN}Found {len(log_files)} log files:{Colors.END}")
    
    # Group logs by directory
    logs_by_dir = {}
    for log_file in log_files:
        directory = os.path.dirname(log_file)
        if directory not in logs_by_dir:
            logs_by_dir[directory] = []
        logs_by_dir[directory].append(log_file)
    
    # Display grouped logs
    index = 1
    all_indices = {}
    
    for directory, logs in sorted(logs_by_dir.items()):
        print(f"\n{Colors.BLUE}{directory}/{Colors.END}")
        
        for log_file in sorted(logs):
            # Mark favorites
            star = f"{Colors.YELLOW}★{Colors.END} " if log_file in favorite_logs else "  "
            
            # Format the filename
            filename = os.path.basename(log_file)
            
            # Try to show file size
            try:
                size = os.path.getsize(log_file)
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                elif size < 1024 * 1024 * 1024:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                else:
                    size_str = f"{size / (1024 * 1024 * 1024):.1f} GB"
                
                # Last modified time
                mtime = os.path.getmtime(log_file)
                mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
                
                # Print the log entry
                print(f"{star}{Colors.GREEN}{index:3d}{Colors.END}. {filename} ({size_str}, {mtime_str})")
            except (OSError, IOError):
                # If we can't access file details
                print(f"{star}{Colors.GREEN}{index:3d}{Colors.END}. {filename}")
                
            all_indices[index] = log_file
            index += 1
    
    return all_indices

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
    print(f"  {Colors.BLUE}Kernel:{Colors.END} {status.get('kernel', 'Unknown')}")
    print(f"  {Colors.BLUE}Python Version:{Colors.END} {status.get('python_version', 'Unknown')}")
    print(f"  {Colors.BLUE}QCMD Version:{Colors.END} {status.get('qcmd_version', 'Unknown')}")
    print(f"  {Colors.BLUE}Hostname:{Colors.END} {status.get('hostname', 'Unknown')}")
    print(f"  {Colors.BLUE}Current Time:{Colors.END} {status.get('current_time', 'Unknown')}")
    print(f"  {Colors.BLUE}Uptime:{Colors.END} {status.get('uptime', 'Unknown')}")
    
    # CPU information
    print(f"\n{Colors.RED}{Colors.BOLD}CPU:{Colors.END}")
    print(f"  {Colors.BLUE}Load Average:{Colors.END} {status.get('load_avg', 'Unknown')}")
    print(f"  {Colors.BLUE}CPU Usage:{Colors.END} {status.get('cpu_percent', 'Unknown')}%")
    
    # Memory information
    print(f"\n{Colors.RED}{Colors.BOLD}Memory:{Colors.END}")
    print(f"  {Colors.BLUE}Total:{Colors.END} {status.get('mem_total', 'Unknown')}")
    print(f"  {Colors.BLUE}Used:{Colors.END} {status.get('mem_used', 'Unknown')} ({status.get('mem_percent', 'Unknown')}%)")
    print(f"  {Colors.BLUE}Free:{Colors.END} {status.get('mem_free', 'Unknown')}")
    
    # Disk information
    print(f"\n{Colors.RED}{Colors.BOLD}Disk Usage:{Colors.END}")
    if 'disks' in status:
        for disk in status['disks']:
            print(f"  {Colors.BLUE}{disk['mount']}:{Colors.END} {disk['used']}/{disk['total']} ({disk['percent']}%)")
    else:
        print(f"  {Colors.YELLOW}Disk information not available{Colors.END}")
    
    # Log directory space
    if 'log_dir_space' in status:
        log_space = status['log_dir_space']
        if 'error' not in log_space:
            print(f"\n{Colors.RED}{Colors.BOLD}Disk Space (Log Directory):{Colors.END}")
            print(f"  {Colors.BLUE}Path:{Colors.END} {log_space.get('path', 'Unknown')}")
            print(f"  {Colors.BLUE}Total:{Colors.END} {log_space.get('total', 'Unknown')}")
            print(f"  {Colors.BLUE}Used:{Colors.END} {log_space.get('used', 'Unknown')} ({log_space.get('percent', 'Unknown')}%)")
            print(f"  {Colors.BLUE}Free:{Colors.END} {log_space.get('free', 'Unknown')}")
    
    # Ollama status
    if 'ollama' in status:
        ollama = status['ollama']
        print(f"\n{Colors.RED}{Colors.BOLD}Ollama Status:{Colors.END}")
        
        # Check if Ollama is running
        if ollama.get('running', False):
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
        elif ollama.get('running', False):
            print(f"  {Colors.BLUE}Available Models:{Colors.END} No models found")
    
    # QCMD Processes
    print(f"\n{Colors.RED}{Colors.BOLD}QCMD Processes:{Colors.END}")
    if 'qcmd_processes' in status:
        if isinstance(status['qcmd_processes'], list):
            if status['qcmd_processes']:
                print(f"  {Colors.BLUE}Active Processes:{Colors.END} {len(status['qcmd_processes'])}")
                for i, proc in enumerate(status['qcmd_processes'], 1):
                    print(f"  {i}. {Colors.GREEN}PID:{Colors.END} {proc.get('pid', 'Unknown')}")
                    print(f"     {Colors.BLUE}Type:{Colors.END} {proc.get('type', 'Unknown')}")
                    print(f"     {Colors.BLUE}Started:{Colors.END} {proc.get('start_time', 'Unknown')}")
                    print(f"     {Colors.BLUE}Status:{Colors.END} {proc.get('status', 'Unknown')}")
                    if 'command' in proc:
                        cmd = proc['command']
                        # Truncate command if too long
                        if len(cmd) > 70:
                            cmd = cmd[:67] + "..."
                        print(f"     {Colors.BLUE}Command:{Colors.END} {cmd}")
                    print()
            else:
                print(f"  {Colors.YELLOW}No active QCMD processes found{Colors.END}")
        else:
            print(f"  {Colors.YELLOW}{status['qcmd_processes']}{Colors.END}")
    
    # Active Log Monitors
    print(f"\n{Colors.RED}{Colors.BOLD}Active Log Monitors:{Colors.END}")
    if 'active_monitors' in status and status['active_monitors']:
        for i, monitor in enumerate(status['active_monitors'], 1):
            print(f"  {i}. {Colors.GREEN}{monitor.get('log_file', 'Unknown')}{Colors.END}")
            print(f"     {Colors.BLUE}PID:{Colors.END} {monitor.get('pid', 'Unknown')}")
            print(f"     {Colors.BLUE}Status:{Colors.END} {monitor.get('status', 'Running')}")
            if 'start_time' in monitor:
                print(f"     {Colors.BLUE}Started:{Colors.END} {monitor['start_time']}")
            print()
    else:
        print(f"  {Colors.YELLOW}No active log monitors{Colors.END}")
    
    # Active Sessions
    print(f"\n{Colors.RED}{Colors.BOLD}Active Sessions:{Colors.END}")
    if 'active_sessions' in status and status['active_sessions']:
        for i, session in enumerate(status['active_sessions'], 1):
            session_id = session.get('session_id', 'Unknown')[:8]  # Show first 8 chars of UUID
            print(f"  {i}. {Colors.GREEN}ID:{Colors.END} {session_id}...")
            print(f"     {Colors.BLUE}Type:{Colors.END} {session.get('type', 'Unknown')}")
            print(f"     {Colors.BLUE}PID:{Colors.END} {session.get('pid', 'Unknown')}")
            
            # Format timestamp nicely if it exists
            if 'created_at' in session:
                created_time = datetime.fromtimestamp(session['created_at']).strftime('%Y-%m-%d %H:%M:%S')
                print(f"     {Colors.BLUE}Created:{Colors.END} {created_time}")
            elif 'start_time' in session:
                print(f"     {Colors.BLUE}Started:{Colors.END} {session['start_time']}")
            
            print()
    else:
        print(f"  {Colors.YELLOW}No active sessions{Colors.END}")
    
    # Network information
    if 'network' in status and status['network']:
        print(f"\n{Colors.RED}{Colors.BOLD}Network:{Colors.END}")
        for nic, stats in status['network'].items():
            print(f"  {Colors.BLUE}{nic}:{Colors.END} {stats}")
    
    # Top processes
    if 'top_processes' in status and status['top_processes']:
        print(f"\n{Colors.RED}{Colors.BOLD}Top Processes:{Colors.END}")
        print(f"  {Colors.BLUE}{'PID':<8}{'USER':<12}{'CPU%':<8}{'MEM%':<8}COMMAND{Colors.END}")
        for proc in status['top_processes']:
            print(f"  {proc.get('pid', 'N/A'):<8}{proc.get('user', 'N/A'):<12}"
                  f"{proc.get('cpu', 'N/A'):<8}{proc.get('mem', 'N/A'):<8}{proc.get('command', 'N/A')}")
    
    # Print divider line
    print(f"\n{Colors.CYAN}{'-' * 80}{Colors.END}\n")

def print_examples():
    """Print detailed usage examples."""
    examples = """
{CYAN}Basic Command Generation{END}
{GREEN}qcmd "list all files in the current directory"{END}
{GREEN}qcmd "find large log files"{END}

{CYAN}Auto-Execute Commands{END}
{GREEN}qcmd -e "check disk space usage"{END}
{GREEN}qcmd --execute "show current directory"{END}

{CYAN}Using Different Models{END}
{GREEN}qcmd -m llama2:7b "restart the nginx service"{END}
{GREEN}qcmd --model deepseek-coder "create a backup of config files"{END}

{CYAN}Adjusting Creativity{END}
{GREEN}qcmd -t 0.7 "find all JPG images"{END}
{GREEN}qcmd --temperature 0.9 "monitor network traffic"{END}

{CYAN}AI Error Analysis{END}
{GREEN}qcmd --analyze "find files larger than 1GB"{END}
{GREEN}qcmd -a -m llama2:7b "create a tar archive of logs"{END}

{CYAN}Auto Mode (Auto-Execute with Error Fixing){END}
{GREEN}qcmd --auto "find Python files modified today"{END}
{GREEN}qcmd -A "search logs for errors"{END}
{GREEN}qcmd -A -m llama2:7b "get system information"{END}

{CYAN}Log Analysis{END}
{GREEN}qcmd --logs{END}
{GREEN}qcmd --logs -m llama2:7b{END}
{GREEN}qcmd --all-logs{END}
{GREEN}qcmd --analyze-file /var/log/syslog{END}
{GREEN}qcmd --monitor /var/log/auth.log{END}
""".format(
        CYAN=Colors.CYAN,
        GREEN=Colors.GREEN,
        END=Colors.END
    )
    
    print(examples)

def clear_screen():
    """Clear the terminal screen."""
    if os.name == 'nt':  # For Windows
        os.system('cls')
    else:  # For Unix/Linux/Mac
        os.system('clear')

# Human readable size formatter
def get_human_readable_size(size_bytes):
    """
    Convert bytes to human readable format (KB, MB, GB).
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        str: Human readable size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    # Return formatted size
    if i == 0:
        return f"{size_bytes:.0f} {size_names[i]}"
    else:
        return f"{size_bytes:.1f} {size_names[i]}" 