#!/usr/bin/env python3
"""
Log monitoring functionality for QCMD.
"""
import os
import time
import json
import signal
import threading
import sys
import subprocess
from typing import Dict, List, Any, Optional

from ..ui.display import Colors
from ..config.settings import CONFIG_DIR
from .analyzer import analyze_log_content

# File path for storing monitor info
MONITORS_FILE = os.path.join(CONFIG_DIR, "active_monitors.json")

def save_monitors(monitors):
    """
    Save active log monitors to persistent storage.
    
    Args:
        monitors: Dictionary of active monitor information
    """
    monitors_file = os.path.join(CONFIG_DIR, "active_monitors.json")
    os.makedirs(os.path.dirname(monitors_file), exist_ok=True)
    try:
        with open(monitors_file, 'w') as f:
            json.dump(monitors, f)
    except Exception as e:
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

def monitor_log(log_file, background=False, analyze=True, model="llama3:latest"):
    """
    Start monitoring a log file for changes.
    
    Args:
        log_file: Path to the log file to monitor
        background: Whether to run in background mode
        analyze: Whether to analyze the log content
        model: Model to use for analysis
    """
    log_file = os.path.abspath(log_file)
    
    if not os.path.exists(log_file):
        print(f"{Colors.RED}Error: Log file '{log_file}' does not exist.{Colors.END}")
        return
    
    if not os.path.isfile(log_file):
        print(f"{Colors.RED}Error: '{log_file}' is not a file.{Colors.END}")
        return
    
    # If running in background mode, fork a new process
    if background:
        try:
            # Fork a child process
            pid = os.fork()
            
            if pid > 0:
                # Parent process
                print(f"{Colors.GREEN}Started monitoring {log_file} in background (PID: {pid}).{Colors.END}")
                print(f"{Colors.YELLOW}Analysis results will be displayed in the terminal where the monitor is running.{Colors.END}")
                
                # Save the monitor information
                monitors = load_monitors()
                
                # Generate a unique ID for this monitor
                monitor_id = f"monitor_{int(time.time())}_{pid}"
                
                monitors[monitor_id] = {
                    "log_file": log_file,
                    "pid": pid,
                    "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "model": model,
                    "analyze": analyze
                }
                
                save_monitors(monitors)
                
                return
            
            # Child process continues
            try:
                # Redirect stdout and stderr to /dev/null in background mode
                devnull = open(os.devnull, 'w')
                sys.stdout = devnull
                sys.stderr = devnull
            except:
                # If redirection fails, just continue
                pass
        except OSError as e:
            print(f"{Colors.RED}Error: Could not create background process: {e}{Colors.END}")
            return
        
    def cleanup():
        # Remove from active monitors
        try:
            if background:
                monitors = load_monitors()
                # Find and remove the monitor for this process
                for monitor_id, info in list(monitors.items()):
                    if info.get("pid") == os.getpid():
                        del monitors[monitor_id]
                        save_monitors(monitors)
                        break
        except:
            # Ignore errors during cleanup
            pass
    
    # Set up signal handlers
    signal.signal(signal.SIGTERM, lambda signum, frame: cleanup() or sys.exit(0))
    signal.signal(signal.SIGINT, lambda signum, frame: cleanup() or sys.exit(0))
    
    try:
        print(f"{Colors.GREEN}Monitoring {Colors.BOLD}{log_file}{Colors.END}")
        print(f"{Colors.GREEN}Press Ctrl+C to stop.{Colors.END}")
        
        # Get the initial file size
        file_size = os.path.getsize(log_file)
        
        # Do initial analysis if requested
        if analyze:
            with open(log_file, 'r', errors='replace') as f:
                content = f.read()
                if content.strip():
                    print(f"{Colors.CYAN}Analyzing existing log content...{Colors.END}")
                    analyze_log_content(content, log_file, model)
        
        # Main monitoring loop
        print(f"\n{Colors.YELLOW}Waiting for new log entries...{Colors.END}")
        
        while True:
            # Check if the file has been updated
            current_size = os.path.getsize(log_file)
            
            if current_size > file_size:
                # File has grown
                with open(log_file, 'r', errors='replace') as f:
                    # Seek to where we left off
                    f.seek(file_size)
                    
                    # Read new content
                    new_content = f.read()
                    
                    # Print the new content
                    if not analyze:
                        print(f"{Colors.CYAN}New log entries:{Colors.END}")
                        print(new_content)
                    else:
                        print(f"{Colors.CYAN}Analyzing new log entries...{Colors.END}")
                        analyze_log_content(new_content, log_file, model)
                        
                # Update file size
                file_size = current_size
            
            # Sleep for a bit to avoid high CPU usage
            time.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Monitoring stopped.{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error monitoring log file: {e}{Colors.END}")
    finally:
        cleanup() 