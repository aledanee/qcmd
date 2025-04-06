#!/usr/bin/env python3
"""
Log file discovery and selection functionality for QCMD CLI.
"""
import os
import json
import time
import tempfile
import subprocess
from typing import List, Optional, Dict, Any

from ..config.settings import DEFAULT_MODEL, CONFIG_DIR
from ..ui.display import Colors
from .analyzer import analyze_log_file, analyze_log_content, read_large_file

# Cache settings
LOG_CACHE_FILE = os.path.join(CONFIG_DIR, "log_cache.json")
LOG_CACHE_EXPIRY = 3600  # Cache expires after 1 hour (in seconds)

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
                    from ..config.settings import load_config
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
        from ..config.settings import load_config
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

def is_log_file(filename: str) -> bool:
    """
    Check if a file is likely a log file based on its name.
    
    Args:
        filename: Name of the file to check
        
    Returns:
        True if the file is likely a log file, False otherwise
    """
    log_extensions = ['.log', '.logs', '.err', '.error', '.out', '.output', '.debug']
    return (any(filename.endswith(ext) for ext in log_extensions) or 
            'log' in filename.lower() or 
            'debug' in filename.lower() or 
            'error' in filename.lower())

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