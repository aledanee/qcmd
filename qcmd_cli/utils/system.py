#!/usr/bin/env python3
"""
System utilities for QCMD.
"""
import os
import sys
import subprocess
import platform
import requests
import json
import shutil
import time
import re
from datetime import datetime
from typing import Dict, Any, Tuple, List, Optional

from ..ui.display import Colors
from ..config.settings import CONFIG_DIR, load_config, DEFAULT_MODEL
from ..log_analysis.monitor import cleanup_stale_monitors
from ..utils.session import cleanup_stale_sessions

# Ollama API settings
OLLAMA_API = "http://127.0.0.1:11434/api"
REQUEST_TIMEOUT = 30  # Timeout for API requests in seconds

# Get version
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
    print(f"  {Colors.BOLD}•{Colors.END} Status: {Colors.GREEN if ollama_status == 'Running' else Colors.RED}{ollama_status}{Colors.END}")
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
            log_file = info.get("log_file", "Unknown")
            pid = info.get("pid", "Unknown")
            analyze = info.get("analyze", False)
            mode = "AI Analysis" if analyze else "Watch Only"
            print(f"  {Colors.BOLD}•{Colors.END} Monitor {Colors.YELLOW}{monitor_id}{Colors.END}: {log_file} ({Colors.GREEN}{mode}{Colors.END}, PID: {pid})")
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
        
        print(f"  {Colors.BOLD}•{Colors.END} Space on {Colors.YELLOW}{CONFIG_DIR}{Colors.END}:")
        print(f"  {Colors.BOLD}•{Colors.END} Used: {Colors.YELLOW}{used_gb:.2f} GB{Colors.END} / Free: {Colors.YELLOW}{free_gb:.2f} GB{Colors.END} / Total: {Colors.YELLOW}{total_gb:.2f} GB{Colors.END}")
        print(f"  {Colors.BOLD}•{Colors.END} Usage: {Colors.YELLOW}{percent:.1f}%{Colors.END}")
        print(f"  {bar}")
    else:
        print(f"  {Colors.YELLOW}Configuration directory not found.{Colors.END}")
    
    # Add update status
    print(f"\n{Colors.CYAN}{Colors.BOLD}► UPDATE STATUS{Colors.END}")
    update_info = check_for_updates(False)
    if update_info:
        current_version = update_info.get('current_version', 'Unknown')
        latest_version = update_info.get('latest_version', 'Unknown')
        update_available = update_info.get('update_available', False)
        
        if update_available:
            print(f"  {Colors.BOLD}•{Colors.END} Update Available: {Colors.GREEN}Yes{Colors.END}")
            print(f"  {Colors.BOLD}•{Colors.END} Current Version: {Colors.YELLOW}{current_version}{Colors.END}")
            print(f"  {Colors.BOLD}•{Colors.END} Latest Version: {Colors.GREEN}{latest_version}{Colors.END}")
            print(f"  {Colors.BOLD}•{Colors.END} Update Command: {Colors.GREEN}pip install --upgrade ibrahimiq-qcmd{Colors.END}")
        else:
            print(f"  {Colors.BOLD}•{Colors.END} Status: {Colors.GREEN}Up to date{Colors.END}")
            print(f"  {Colors.BOLD}•{Colors.END} Version: {Colors.YELLOW}{current_version}{Colors.END}")
    else:
        print(f"  {Colors.YELLOW}Could not check for updates.{Colors.END}")
    
    # Footer
    print(f"\n{Colors.BOLD}╚════════════════════════════════════════════════════════════════════════════════════════════════╝{Colors.END}\n")

def check_for_updates(force_display: bool = False) -> Optional[Dict[str, Any]]:
    """
    Check for QCMD updates by querying PyPI.
    
    Args:
        force_display: Whether to force displaying the update status
        
    Returns:
        Dictionary with update information or None if check fails
    """
    # Get current version
    current_version = __version__
    
    # Load config to check if updates are disabled
    config = load_config()
    if not force_display and config.get('disable_update_check', False):
        return None
    
    # Try to get the latest version from PyPI
    latest_version = None
    try:
        response = requests.get("https://pypi.org/pypi/ibrahimiq-qcmd/json", timeout=5)
        if response.status_code == 200:
            data = response.json()
            latest_version = data['info']['version']
    except Exception:
        # If we can't connect to PyPI, just return None
        return None
    
    # If we couldn't get the latest version, return None
    if not latest_version:
        return None
    
    # Compare versions
    current_parts = current_version.split('.')
    latest_parts = latest_version.split('.')
    
    update_available = False
    
    # Compare major, minor, patch versions
    for c, l in zip(current_parts, latest_parts):
        if int(l) > int(c):
            update_available = True
            break
        elif int(l) < int(c):
            # Current is newer (development version)
            break
    
    # If different number of parts and no decision yet,
    # the one with more parts is considered newer
    if not update_available and len(latest_parts) > len(current_parts):
        update_available = True
    
    result = {
        'current_version': current_version,
        'latest_version': latest_version,
        'update_available': update_available
    }
    
    # Display the info if requested
    if force_display:
        if update_available:
            print(f"\n{Colors.YELLOW}Update available!{Colors.END}")
            print(f"Current version: {Colors.RED}{current_version}{Colors.END}")
            print(f"Latest version: {Colors.GREEN}{latest_version}{Colors.END}")
            print(f"To update, run: {Colors.GREEN}pip install --upgrade ibrahimiq-qcmd{Colors.END}")
        else:
            print(f"\n{Colors.GREEN}QCMD is up to date!{Colors.END}")
            print(f"Current version: {Colors.GREEN}{current_version}{Colors.END}")
    
    return result

def display_update_status() -> None:
    """
    Display the update status with improved formatting.
    """
    # Load config to check if updates are disabled
    config = load_config()
    if config.get('disable_update_check', False):
        return
    
    update_info = check_for_updates(False)
    if update_info and update_info.get('update_available', False):
        current_version = update_info.get('current_version', 'Unknown')
        latest_version = update_info.get('latest_version', 'Unknown')
        
        # Create a nice-looking update message
        print(f"\n{Colors.YELLOW}╔═══════════════════════════════════════════════════════════════╗{Colors.END}")
        print(f"{Colors.YELLOW}║  {Colors.BOLD}UPDATE AVAILABLE{Colors.END}{Colors.YELLOW}                                             ║{Colors.END}")
        print(f"{Colors.YELLOW}║                                                               ║{Colors.END}")
        print(f"{Colors.YELLOW}║  Current version: {Colors.RED}{current_version.ljust(10)}{Colors.YELLOW}                                  ║{Colors.END}")
        print(f"{Colors.YELLOW}║  Latest version:  {Colors.GREEN}{latest_version.ljust(10)}{Colors.YELLOW}                                  ║{Colors.END}")
        print(f"{Colors.YELLOW}║                                                               ║{Colors.END}")
        print(f"{Colors.YELLOW}║  To update, run:                                              ║{Colors.END}")
        print(f"{Colors.YELLOW}║  {Colors.GREEN}pip install --upgrade ibrahimiq-qcmd{Colors.YELLOW}                      ║{Colors.END}")
        print(f"{Colors.YELLOW}╚═══════════════════════════════════════════════════════════════╝{Colors.END}\n")

def execute_command(command: str, analyze_errors: bool = False, model: str = None) -> Tuple[int, str]:
    """
    Execute a shell command and return the exit code and output.
    
    Args:
        command: The command to execute
        analyze_errors: Whether to analyze errors if the command fails
        model: Model to use for error analysis
        
    Returns:
        Tuple of (exit_code, output)
    """
    print(f"\n{Colors.CYAN}Executing:{Colors.END} {Colors.GREEN}{command}{Colors.END}")
        
    try:
        # Run the command and capture output
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        output_lines = []
        for line in process.stdout:
            print(line, end='')
            output_lines.append(line)
            
        process.wait()
        exit_code = process.returncode
        output = ''.join(output_lines)
            
        return exit_code, output
        
    except Exception as e:
        error_msg = f"Error executing command: {str(e)}"
        print(f"{Colors.RED}{error_msg}{Colors.END}")
        return 1, error_msg
        
def format_bytes(bytes_value):
    """
    Format byte values to human-readable format.
    
    Args:
        bytes_value: Number of bytes
        
    Returns:
        Human-readable string representation
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB" 