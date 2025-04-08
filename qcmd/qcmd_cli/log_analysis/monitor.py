#!/usr/bin/env python3
"""
Log monitoring functionality for QCMD.

This module provides functionality for monitoring log files in real-time.
It includes features for continuous monitoring, background operation, and
integration with the log analysis system.

Example usage:
    >>> from qcmd_cli.log_analysis.monitor import monitor_log
    >>> # Monitor a log file with analysis:
    >>> monitor_log("/var/log/syslog", analyze=True)
    >>> # Monitor in background:
    >>> monitor_log("/var/log/auth.log", background=True)
"""
import os
import time
import json
import signal
import threading
import sys
import subprocess
import logging
from typing import Dict, List, Any, Optional, Union

from ..ui.display import Colors
from ..config.settings import CONFIG_DIR
from .analyzer import analyze_log_content

logger = logging.getLogger(__name__)

# File path for storing monitor info
MONITORS_FILE = os.path.join(CONFIG_DIR, "active_monitors.json")

def save_monitors(monitors: Dict[str, Dict[str, Any]]) -> None:
    """
    Save active log monitors to persistent storage.
    
    This function saves the current state of active log monitors to a JSON file.
    The saved information includes monitor IDs, process IDs, and configuration.
    
    Args:
        monitors: Dictionary containing monitor information to save
        
    Returns:
        None
        
    Raises:
        IOError: If the monitors file cannot be written
        Exception: For other unexpected errors during file operations
        
    Example:
        >>> monitors = {
        ...     "monitor_1": {
        ...         "log_file": "/var/log/syslog",
        ...         "pid": 1234,
        ...         "started_at": "2024-01-01 12:00:00"
        ...     }
        ... }
        >>> save_monitors(monitors)
    """
    monitors_file = os.path.join(CONFIG_DIR, "active_monitors.json")
    os.makedirs(os.path.dirname(monitors_file), exist_ok=True)
    try:
        with open(monitors_file, 'w') as f:
            json.dump(monitors, f)
        logger.debug(f"Successfully saved active monitors to {monitors_file}")
    except Exception as e:
        logger.error(f"Could not save active monitors: {e}")
        print(f"{Colors.YELLOW}Could not save active monitors: {e}{Colors.END}", file=sys.stderr)

def load_monitors():
    """
    Load saved monitors from persistent storage.
    
    Returns:
        Dictionary of saved monitor information
    """
    monitors_file = os.path.join(CONFIG_DIR, "active_monitors.json")
    if os.path.exists(monitors_file):
        try:
            with open(monitors_file, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def cleanup_stale_monitors():
    """
    Clean up monitors that are no longer active.
    """
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

def monitor_log(log_file: str, background: bool = False, analyze: bool = True, model: str = "llama3:latest") -> None:
    """
    Monitor a log file for changes and analyze new content.
    """
    logger.info(f"Starting log monitoring for {log_file}")
    
    # Check if file exists
    if not os.path.exists(log_file):
        logger.error(f"Log file {log_file} does not exist")
        print(f"{Colors.RED}Error: Log file '{log_file}' does not exist.{Colors.END}")
        return
        
    # Check if path is a file
    if not os.path.isfile(log_file):
        logger.error(f"Path {log_file} is not a file")
        print(f"{Colors.RED}Error: '{log_file}' is not a file.{Colors.END}")
        return
        
    # Get initial file size
    try:
        last_position = os.path.getsize(log_file)
        logger.debug(f"Initial file size: {last_position} bytes")
    except Exception as e:
        logger.error(f"Error getting file size: {e}")
        print(f"{Colors.RED}Error: Could not get file size: {e}{Colors.END}")
        return

    if not background:
        print(f"{Colors.GREEN}Monitoring {Colors.BOLD}{log_file}{Colors.END}")
        print(f"{Colors.GREEN}Press Ctrl+C to stop.{Colors.END}")

    def monitor():
        nonlocal last_position
        logger.info(f"Starting log monitor thread for {log_file}")
        
        try:
            # Initial read and analysis
            try:
                with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                    initial_content = f.read()
                if initial_content and analyze:
                    logger.info("Analyzing initial log content")
                    analyze_log_content(initial_content, log_file, model)
                last_position = os.path.getsize(log_file)
            except Exception as e:
                logger.error(f"Error reading initial content: {e}")
                print(f"\n{Colors.RED}Error reading initial content: {e}{Colors.END}")
                return

            while True:
                try:
                    current_size = os.path.getsize(log_file)
                    
                    if current_size > last_position:
                        logger.debug(f"New content detected in {log_file}")
                        # Read only the new content
                        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                            f.seek(last_position)
                            new_content = f.read()
                        
                        if new_content:
                            logger.info(f"New log entries detected at {time.strftime('%H:%M:%S')}")
                            print(f"\n{Colors.CYAN}New log entries detected at {time.strftime('%H:%M:%S')}:{Colors.END}")
                            print(f"{Colors.YELLOW}" + "-" * 40 + f"{Colors.END}")
                            print(new_content)
                            print(f"{Colors.YELLOW}" + "-" * 40 + f"{Colors.END}")
                            
                            # Analyze the new content
                            if analyze:
                                logger.info("Analyzing new log content")
                                analyze_log_content(new_content, log_file, model)
                        
                        # Update position
                        last_position = current_size
                except FileNotFoundError:
                    logger.error(f"Log file {log_file} no longer exists")
                    print(f"\n{Colors.RED}Error: Log file {log_file} no longer exists.{Colors.END}")
                    break
                except PermissionError:
                    logger.error(f"Permission denied when reading {log_file}")
                    print(f"\n{Colors.RED}Error: Permission denied when reading {log_file}.{Colors.END}")
                    break
                except Exception as e:
                    logger.error(f"Error reading log file: {e}")
                    print(f"\n{Colors.RED}Error reading log file: {e}{Colors.END}")
                    break
                
                time.sleep(1)  # Prevent excessive CPU usage
                
        except Exception as e:
            logger.error(f"Monitor thread error: {e}")
            if not background:  # Only print in foreground mode
                print(f"\n{Colors.RED}Monitor thread error: {e}{Colors.END}")
        finally:
            if background:
                cleanup_stale_monitors()

    if background:
        # Fork a child process for background monitoring
        try:
            pid = os.fork()
            if pid > 0:  # Parent process
                # Save monitor info
                monitors = load_monitors()
                monitor_id = f"monitor_{int(time.time())}"
                monitors[monitor_id] = {
                    "log_file": log_file,
                    "pid": pid,
                    "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "model": model,
                    "analyze": analyze
                }
                save_monitors(monitors)
                print(f"{Colors.GREEN}Started monitoring {log_file} in background (PID: {pid}).{Colors.END}")
                return
            else:  # Child process
                try:
                    # Detach from parent session
                    os.setsid()
                    # Close file descriptors
                    os.close(0)
                    os.close(1)
                    os.close(2)
                    # Start monitoring
                    monitor()
                except Exception as e:
                    logger.error(f"Error in child process: {e}")
                finally:
                    os._exit(0)
        except OSError as e:
            logger.error(f"Fork failed: {e}")
            print(f"{Colors.RED}Error: Could not start background monitoring: {e}{Colors.END}")
            return
    else:
        try:
            monitor()
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Monitoring stopped.{Colors.END}")
        except Exception as e:
            logger.error(f"Error during monitoring: {e}")
            print(f"{Colors.RED}Error during monitoring: {e}{Colors.END}") 