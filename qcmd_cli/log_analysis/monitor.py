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
    Also ends associated sessions for stale monitors.
    
    Returns:
        Dict of monitors that are still active
    """
    # Import here to avoid circular imports
    from ..utils.session import end_session
    
    monitors = load_monitors()
    updated = {}
    stale_session_ids = []
    
    for monitor_id, info in monitors.items():
        pid = info.get("pid")
        if pid is None:
            continue
            
        # Check if process is still running
        if is_process_running(pid):
            # Process exists, keep the monitor
            updated[monitor_id] = info
        else:
            # Process doesn't exist, discard the monitor
            # Also track the session ID for cleanup
            session_id = info.get("session_id")
            if session_id:
                stale_session_ids.append(session_id)
    
    # End all stale sessions
    for session_id in stale_session_ids:
        try:
            end_session(session_id)
        except Exception as e:
            print(f"Error ending session {session_id}: {e}", file=sys.stderr)
    
    # Save updated monitors
    save_monitors(updated)
    return updated

# Helper function to check if a process is running
def is_process_running(pid):
    """
    Check if a process with the given PID is running.
    
    Args:
        pid: Process ID to check
        
    Returns:
        True if the process is running, False otherwise
    """
    try:
        os.kill(int(pid), 0)  # Signal 0 doesn't kill the process, just checks if it exists
        return True
    except (OSError, ValueError):
        return False

def monitor_log(log_file, background=False, analyze=True, model="qwen2.5-coder:0.5b", show_analysis_only=False):
    """
    Start monitoring a log file for changes.
    
    Args:
        log_file: Path to the log file to monitor
        background: Whether to run in background mode
        analyze: Whether to analyze the log content
        model: Model to use for analysis
        show_analysis_only: If True, only shows analysis summaries, not raw log lines
    """
    log_file = os.path.abspath(log_file)
    
    if not os.path.exists(log_file):
        print(f"{Colors.RED}Error: Log file '{log_file}' does not exist.{Colors.END}")
        return
    
    if not os.path.isfile(log_file):
        print(f"{Colors.RED}Error: '{log_file}' is not a file.{Colors.END}")
        return
    
    # Import session management functions
    from ..utils.session import create_log_monitor_session, end_session, update_session_activity
    
    # If running in background mode, fork a new process
    if background:
        try:
            # Fork a child process
            pid = os.fork()
            
            if pid > 0:
                # Parent process
                print(f"{Colors.GREEN}Started monitoring {log_file} in background (PID: {pid}).{Colors.END}")
                print(f"{Colors.YELLOW}Analysis results will be displayed in the terminal where the monitor is running.{Colors.END}")
                
                # Create a session for this monitor
                session_id = create_log_monitor_session(log_file, model, analyze)
                
                # Save the monitor information
                monitors = load_monitors()
                
                # Generate a unique ID for this monitor
                monitor_id = f"monitor_{int(time.time())}_{pid}"
                
                monitors[monitor_id] = {
                    "log_file": log_file,
                    "pid": pid,
                    "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "model": model,
                    "analyze": analyze,
                    "session_id": session_id  # Store the session ID
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
    
    # Create a session for the foreground monitor as well
    session_id = create_log_monitor_session(log_file, model, analyze)
        
    def cleanup():
        # Remove from active monitors and end the session
        try:
            if background:
                monitors = load_monitors()
                # Find and remove the monitor for this process
                for monitor_id, info in list(monitors.items()):
                    if info.get("pid") == os.getpid():
                        # End the session
                        if "session_id" in info:
                            end_session(info["session_id"])
                        # Remove the monitor
                        del monitors[monitor_id]
                        save_monitors(monitors)
                        break
            else:
                # End the session for foreground monitors too
                end_session(session_id)
        except:
            # Ignore errors during cleanup
            pass
    
    # Set up signal handlers
    signal.signal(signal.SIGTERM, lambda signum, frame: cleanup() or sys.exit(0))
    signal.signal(signal.SIGINT, lambda signum, frame: cleanup() or sys.exit(0))
    
    try:
        print(f"{Colors.GREEN}Monitoring {Colors.BOLD}{log_file}{Colors.END}")
        
        # Display mode information
        if analyze:
            if show_analysis_only:
                print(f"{Colors.YELLOW}Mode: Analysis only (log lines hidden){Colors.END}")
            else:
                print(f"{Colors.YELLOW}Mode: Full monitoring with analysis{Colors.END}")
        else:
            print(f"{Colors.YELLOW}Mode: Watch only (no analysis){Colors.END}")
        
        print(f"{Colors.GREEN}Press Ctrl+C to stop or 'm' to toggle display mode.{Colors.END}")
        
        # Set up nonblocking input for mode switching
        import select
        import termios
        import tty
        
        # Save original terminal settings
        old_settings = termios.tcgetattr(sys.stdin)
        
        # Get the initial file size
        file_size = os.path.getsize(log_file)
        
        # Set up a time for session activity updates
        last_activity_update = time.time()
        activity_update_interval = 60  # Update activity every 60 seconds
        
        # Track current display mode
        current_show_analysis_only = show_analysis_only
        
        # Do initial analysis if requested
        if analyze:
            with open(log_file, 'r', errors='replace') as f:
                content = f.read()
                if content.strip():
                    print(f"{Colors.CYAN}Analyzing existing log content...{Colors.END}")
                    if not current_show_analysis_only:
                        print(f"\n{Colors.YELLOW}--- Existing Log Content ---{Colors.END}")
                        print(content)
                        print(f"{Colors.YELLOW}--- End of Existing Content ---{Colors.END}\n")
                    
                    print(f"{Colors.CYAN}--- Analysis Results ---{Colors.END}")
                    analyze_log_content(content, log_file, model)
                    print(f"{Colors.CYAN}--- End of Analysis ---{Colors.END}\n")
        
        # Main monitoring loop
        print(f"\n{Colors.YELLOW}Waiting for new log entries...{Colors.END}")
        
        # Set terminal to raw mode for detecting keypress
        tty.setraw(sys.stdin.fileno())
        
        while True:
            # Update session activity periodically
            current_time = time.time()
            if current_time - last_activity_update > activity_update_interval:
                update_session_activity(session_id)
                last_activity_update = current_time
                
            # Check if the file has been updated
            current_size = os.path.getsize(log_file)
            
            if current_size > file_size:
                # File has grown
                with open(log_file, 'r', errors='replace') as f:
                    # Seek to where we left off
                    f.seek(file_size)
                    
                    # Read new content
                    new_content = f.read()
                    
                    # Get current time for timestamp
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Print the new content
                    if not analyze:
                        print(f"\n{Colors.CYAN}[{timestamp}] New log entries:{Colors.END}")
                        print(new_content)
                    else:
                        if not current_show_analysis_only:
                            print(f"\n{Colors.CYAN}[{timestamp}] New log entries:{Colors.END}")
                            print(f"{Colors.YELLOW}--- Begin New Log Content ---{Colors.END}")
                            print(new_content)
                            print(f"{Colors.YELLOW}--- End New Log Content ---{Colors.END}")
                        
                        print(f"\n{Colors.GREEN}[{timestamp}] Log Analysis:{Colors.END}")
                        print(f"{Colors.CYAN}--- Begin Analysis Results ---{Colors.END}")
                        analyze_log_content(new_content, log_file, model)
                        print(f"{Colors.CYAN}--- End Analysis Results ---{Colors.END}")
                        
                # Update file size
                file_size = current_size
                
                # Update session activity after processing new content
                update_session_activity(session_id)
                last_activity_update = time.time()
            
            # Check for keypress to toggle modes
            if select.select([sys.stdin], [], [], 0.1)[0]:
                key = sys.stdin.read(1)
                if key.lower() == 'm':
                    current_show_analysis_only = not current_show_analysis_only
                    # Restore terminal settings temporarily to print mode change
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                    if current_show_analysis_only:
                        print(f"\n{Colors.GREEN}Switched to analysis-only mode (log lines hidden){Colors.END}")
                    else:
                        print(f"\n{Colors.GREEN}Switched to full mode (showing both log lines and analysis){Colors.END}")
                    # Return to raw mode
                    tty.setraw(sys.stdin.fileno())
            
            # Sleep for a bit to avoid high CPU usage
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Monitoring stopped.{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error monitoring log file: {e}{Colors.END}")
    finally:
        # Restore terminal settings
        try:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        except:
            pass
        cleanup() 