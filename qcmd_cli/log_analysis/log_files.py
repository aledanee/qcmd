#!/usr/bin/env python3
"""
Log file discovery and selection functionality for QCMD CLI.
"""
import os
import json
import time
import tempfile
import subprocess
import signal
from typing import List, Optional, Dict, Any

from ..config.settings import DEFAULT_MODEL, CONFIG_DIR
from ..ui.display import Colors
from .analyzer import analyze_log_file, analyze_log_content, read_large_file
from .monitor import load_monitors, save_monitors, cleanup_stale_monitors
from ..utils.session import get_active_log_monitors, end_session, load_sessions

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
                print(f"{Colors.YELLOW}Invalid selection '{choice}'. Please enter a number between 1 and {len(file_indices)}.{Colors.END}")
        except ValueError:
            print(f"{Colors.YELLOW}Please enter a number or 'q' to cancel.{Colors.END}")
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Operation cancelled.{Colors.END}")
            return None

def handle_log_analysis(model: str = DEFAULT_MODEL, file_path: str = None, 
                       analyze_once: bool = False, monitor_analyze: bool = False,
                       monitor_watch: bool = False, auto_continue: bool = False) -> None:
    """
    Main entry point for log analysis functionality.
    
    Args:
        model: The model to use for analysis
        file_path: Optional path to a specific log file to analyze
        analyze_once: Analyze the log file once without monitoring
        monitor_analyze: Monitor the log file with analysis
        monitor_watch: Monitor the log file without analysis (just watch)
        auto_continue: Automatically continue without asking in test mode
    """
    # Import here to avoid circular imports
    from .analyzer import analyze_log_file
    from .monitor import monitor_log
    
    print("Starting log analysis tool...")
    
    # If a log file was specified, analyze it directly
    if file_path:
        if os.path.exists(file_path) and os.path.isfile(file_path):
            if analyze_once:
                analyze_log_file(file_path, model)
            elif monitor_analyze:
                monitor_log(file_path, background=True, analyze=True, model=model)
            elif monitor_watch:
                monitor_log(file_path, background=True, analyze=False, model=model)
            else:
                handle_log_selection(file_path, model, analyze_once, monitor_analyze, monitor_watch)
            return
        elif file_path.startswith("journalctl:"):
            # For journalctl service logs
            service_name = file_path.split(':', 1)[1]
            
            try:
                # Create a temp file for the journal output
                with tempfile.NamedTemporaryFile(delete=False, mode='w+t', suffix='.log') as temp_file:
                    temp_path = temp_file.name
                    
                    # Get the journal output
                    journal_output = subprocess.check_output(
                        ["journalctl", "-u", service_name], 
                        universal_newlines=True
                    )
                    
                    # Write to temp file
                    temp_file.write(journal_output)
                
                print(f"{Colors.GREEN}Retrieved logs for service {service_name}.{Colors.END}")
                
                # Analyze the temp file
                if analyze_once:
                    analyze_log_file(temp_path, model)
                elif monitor_analyze:
                    monitor_log(temp_path, background=True, analyze=True, model=model)
                elif monitor_watch:
                    monitor_log(temp_path, background=True, analyze=False, model=model)
                else:
                    handle_log_selection(temp_path, model, analyze_once, monitor_analyze, monitor_watch)
                
                # Clean up
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
            except subprocess.SubprocessError as e:
                print(f"{Colors.RED}Error fetching service logs: {e}{Colors.END}")
            except Exception as e:
                print(f"{Colors.RED}Error: {e}{Colors.END}")
        else:
            # Regular file
            if os.path.exists(file_path) and os.path.isfile(file_path):
                if analyze_once:
                    analyze_log_file(file_path, model)
                elif monitor_analyze:
                    monitor_log(file_path, background=True, analyze=True, model=model)
                elif monitor_watch:
                    monitor_log(file_path, background=True, analyze=False, model=model)
                else:
                    handle_log_selection(file_path, model, analyze_once, monitor_analyze, monitor_watch)
            else:
                print(f"{Colors.RED}Error: File {file_path} does not exist or is not accessible.{Colors.END}")
            return
    
    # First, show active log monitors
    has_monitors = list_active_log_monitors()
    
    # If we want to manage monitors
    if has_monitors:
        if auto_continue:
            monitor_action = 'c'  # Automatically continue in test mode
        else:
            monitor_action = input(f"{Colors.GREEN}Do you want to (s)top a monitor, (v)iew logs, or (c)ontinue to analyze new logs? [s/v/c]: {Colors.END}").lower()
    else:
        monitor_action = 'c'  # Default to continue if no monitors
    
    if monitor_action == 's':
        # Get active log monitor sessions and legacy monitors
        log_monitors = get_active_log_monitors()
        legacy_monitors = load_monitors()
        
        # Combine both types into a single dictionary for easier handling
        all_monitors = {}
        
        # Add session-based monitors
        for i, (session_id, info) in enumerate(log_monitors.items(), 1):
            log_file = info.get('log_file', 'Unknown')
            all_monitors[i] = {
                'id': session_id,
                'type': 'session',
                'name': os.path.basename(log_file)
            }
        
        # Add legacy monitors
        offset = len(log_monitors)
        for i, (monitor_id, info) in enumerate(legacy_monitors.items(), offset + 1):
            log_file = info.get('log_file', 'Unknown')
            all_monitors[i] = {
                'id': monitor_id,
                'type': 'legacy',
                'name': os.path.basename(log_file)
            }
        
        if not all_monitors:
            print(f"{Colors.YELLOW}No active log monitors to stop.{Colors.END}")
        else:
            # Display monitors with numbers
            for i, info in all_monitors.items():
                monitor_id = info['id']
                name = info['name']
                id_type = info['type']
                print(f"{i}. {name} ({monitor_id[:8]}... - {id_type})")
            
            # Ask which one to stop
            try:
                choice = int(input(f"{Colors.GREEN}Enter number to stop (or 0 to cancel): {Colors.END}"))
                if choice > 0 and choice in all_monitors:
                    monitor_info = all_monitors[choice]
                    stop_log_monitor(monitor_info['id'])
                elif choice != 0:
                    print(f"{Colors.YELLOW}Invalid selection.{Colors.END}")
            except (ValueError, IndexError):
                print(f"{Colors.YELLOW}Invalid selection.{Colors.END}")
        
        # Return to main menu or continue with analysis
        continue_analysis = input(f"{Colors.GREEN}Do you want to analyze logs now? (y/n): {Colors.END}").lower()
        if continue_analysis != 'y':
            return
    
    # Find log files
    log_files = find_log_files()
    
    if not log_files:
        print(f"{Colors.YELLOW}No accessible log files found on the system.{Colors.END}")
        return
    
    # Let user select a log file
    selected_log = display_log_selection(log_files)
    
    if selected_log:
        handle_log_selection(selected_log, model, analyze_once, monitor_analyze, monitor_watch)

def handle_log_selection(selected_log: str, model: str,
                       analyze_once: bool = False, 
                       monitor_analyze: bool = False,
                       monitor_watch: bool = False) -> None:
    """
    Handle log file selection and analysis options.
    
    Args:
        selected_log: Path to the selected log file
        model: The model to use for analysis
        analyze_once: Analyze the log file once without monitoring
        monitor_analyze: Monitor the log file with analysis
        monitor_watch: Monitor the log file without analysis (just watch)
    """
    # Import here to avoid circular imports
    from .analyzer import analyze_log_file
    from .monitor import monitor_log

    # Check if the log is a journalctl service
    if selected_log.startswith("journalctl:"):
        service_name = selected_log.split(':', 1)[1]
        
        try:
            # Create a temp file for the journal output
            with tempfile.NamedTemporaryFile(delete=False, mode='w+t', suffix='.log') as temp_file:
                temp_path = temp_file.name
                
                # Get the journal output
                journal_output = subprocess.check_output(
                    ["journalctl", "-u", service_name], 
                    universal_newlines=True
                )
                
                # Write to temp file
                temp_file.write(journal_output)
            
            print(f"{Colors.GREEN}Retrieved logs for service {service_name}.{Colors.END}")
            
            # Based on the automatic options or user choice
            if analyze_once:
                action = 'a'  # Analyze once
            elif monitor_analyze:
                action = 'm'  # Monitor with analysis
            elif monitor_watch:
                action = 'w'  # Watch without analysis
            else:
                # Ask user what they want to do
                action = input(f"{Colors.GREEN}Do you want to (a)nalyze once, (m)onitor with analysis, or just (w)atch without analysis? (a/m/w): {Colors.END}").lower()
            
            if action == 'a':
                # Analyze once
                analyze_log_file(temp_path, model)
            elif action == 'm':
                # Monitor with analysis
                monitor_log(temp_path, background=True, analyze=True, model=model)
            elif action == 'w':
                # Watch without analysis
                monitor_log(temp_path, background=True, analyze=False, model=model)
            else:
                print(f"{Colors.YELLOW}Invalid choice. Analyzing once.{Colors.END}")
                analyze_log_file(temp_path, model)
            
            # Clean up
            try:
                os.unlink(temp_path)
            except:
                pass
                    
        except subprocess.SubprocessError as e:
            print(f"{Colors.RED}Error fetching service logs: {e}{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.END}")
    else:
        # Regular file
        if os.path.exists(selected_log) and os.path.isfile(selected_log):
            # Based on the automatic options or user choice
            if analyze_once:
                action = 'a'  # Analyze once
            elif monitor_analyze:
                action = 'm'  # Monitor with analysis
            elif monitor_watch:
                action = 'w'  # Watch without analysis
            else:
                # Ask user what they want to do
                action = input(f"{Colors.GREEN}Do you want to (a)nalyze once, (m)onitor with analysis, or just (w)atch without analysis? (a/m/w): {Colors.END}").lower()
            
            if action == 'a':
                # Analyze once
                analyze_log_file(selected_log, model)
            elif action == 'm':
                # Monitor with analysis
                monitor_log(selected_log, background=True, analyze=True, model=model)
            elif action == 'w':
                # Watch without analysis
                monitor_log(selected_log, background=True, analyze=False, model=model)
            else:
                print(f"{Colors.YELLOW}Invalid choice. Analyzing once.{Colors.END}")
                analyze_log_file(selected_log, model)
        else:
            print(f"{Colors.RED}Error: File {selected_log} does not exist or is not accessible.{Colors.END}") 

def list_active_log_monitors(non_interactive=False):
    """
    Display a list of currently active log monitors.
    
    Args:
        non_interactive: If True, don't prompt for user action
        
    Returns:
        False if no monitors found, True otherwise
    """
    # Get active log monitor sessions
    log_monitors = get_active_log_monitors()
    
    # Also check legacy monitors for backward compatibility
    legacy_monitors = cleanup_stale_monitors()
    legacy_count = len(legacy_monitors)
    
    total_count = len(log_monitors) + legacy_count
    
    if total_count == 0:
        print(f"{Colors.YELLOW}No active log monitors found.{Colors.END}")
        return False
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}Active Log Monitors ({total_count}):{Colors.END}")
    
    # Create a mapping of display index to session/monitor ID
    index_to_id = {}
    
    # Display session-based monitors
    for i, (session_id, info) in enumerate(log_monitors.items(), 1):
        log_file = info.get('log_file', 'Unknown')
        started_at = info.get('start_time', 'Unknown')
        model = info.get('model', 'Unknown')
        analyze = "with analysis" if info.get('analyze', True) else "without analysis"
        
        print(f"{i}. {Colors.CYAN}{os.path.basename(log_file)}{Colors.END}")
        print(f"   {Colors.BLUE}Path:{Colors.END} {log_file}")
        print(f"   {Colors.BLUE}Started:{Colors.END} {started_at}")
        print(f"   {Colors.BLUE}Model:{Colors.END} {model}")
        print(f"   {Colors.BLUE}Mode:{Colors.END} {analyze}")
        print(f"   {Colors.BLUE}Session ID:{Colors.END} {session_id[:8]}...")
        print()
        
        # Store the mapping
        index_to_id[i] = session_id
    
    # Display legacy monitors if any
    if legacy_count > 0:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}Legacy Monitors (Pre-Session System):{Colors.END}")
        offset = len(log_monitors)
        for i, (monitor_id, info) in enumerate(legacy_monitors.items(), offset + 1):
            log_file = info.get('log_file', 'Unknown')
            pid = info.get('pid', 'Unknown')
            started_at = info.get('started_at', 'Unknown')
            
            print(f"{i}. {Colors.CYAN}{os.path.basename(log_file)}{Colors.END}")
            print(f"   {Colors.BLUE}Path:{Colors.END} {log_file}")
            print(f"   {Colors.BLUE}Started:{Colors.END} {started_at}")
            print(f"   {Colors.BLUE}PID:{Colors.END} {pid}")
            print(f"   {Colors.BLUE}Monitor ID:{Colors.END} {monitor_id}")
            print()
            
            # Store the mapping
            index_to_id[i] = monitor_id
    
    # Skip interactive prompts if non_interactive is True
    if non_interactive:
        return True
        
    # Ask user if they want to take action
    try:
        print(f"{Colors.CYAN}=== Monitor Options ==={Colors.END}")
        print(f"  {Colors.GREEN}v{Colors.END} - View a monitor (connect to see live log entries and analysis)")
        print(f"  {Colors.GREEN}s{Colors.END} - Stop a monitor")
        print(f"  {Colors.GREEN}c{Colors.END} - Continue to analyze new logs")
        print(f"  {Colors.GREEN}f{Colors.END} - Full display mode (show both log entries and analysis)")
        print(f"  {Colors.GREEN}a{Colors.END} - Analysis-only mode (hide raw log entries)")
        action = input(f"{Colors.GREEN}What would you like to do? [v/s/c/f/a]: {Colors.END}").lower()
        
        if action == 's':
            # Stop a monitor
            try:
                monitor_num = int(input(f"{Colors.GREEN}Enter monitor number to stop: {Colors.END}"))
                if monitor_num in index_to_id:
                    stop_log_monitor(index_to_id[monitor_num])
                else:
                    print(f"{Colors.RED}Invalid monitor number.{Colors.END}")
            except ValueError:
                print(f"{Colors.RED}Invalid input. Please enter a number.{Colors.END}")
        elif action == 'v' or action == 'f' or action == 'a':
            # View monitor with specific display mode
            try:
                monitor_num = int(input(f"{Colors.GREEN}Enter monitor number to view: {Colors.END}"))
                if monitor_num in index_to_id:
                    # Default to normal view mode for 'v', analysis only for 'a', full display for 'f'
                    show_analysis_only = (action == 'a')
                    if show_analysis_only:
                        print(f"{Colors.GREEN}Viewing in analysis-only mode (log lines hidden){Colors.END}")
                    else:
                        print(f"{Colors.GREEN}Viewing in full display mode (showing log lines and analysis){Colors.END}")
                    view_monitor(index_to_id[monitor_num], show_analysis_only=show_analysis_only)
                else:
                    print(f"{Colors.RED}Invalid monitor number.{Colors.END}")
            except ValueError:
                print(f"{Colors.RED}Invalid input. Please enter a number.{Colors.END}")
    except KeyboardInterrupt:
        print("\nCancelled.")
    
    return True

def stop_log_monitor(session_id):
    """
    Stop a log monitor by its session ID or monitor ID.
    
    Args:
        session_id: ID of the session or monitor to stop
        
    Returns:
        True if the monitor was stopped, False otherwise
    """
    # First check session-based monitors
    sessions = load_sessions()
    
    if session_id in sessions:
        info = sessions[session_id]
        
        if info.get('type') != 'log_monitor':
            print(f"{Colors.RED}Error: Not a log monitor session.{Colors.END}")
            return False
        
        # Get the process ID
        pid = info.get('pid')
        
        if pid:
            try:
                # Send termination signal to the process
                os.kill(pid, signal.SIGTERM)
                print(f"{Colors.GREEN}Sent termination signal to log monitor process.{Colors.END}")
            except OSError:
                # Process might not exist anymore
                pass
        
        # End the session in any case
        end_session(session_id)
        print(f"{Colors.GREEN}Log monitor session ended.{Colors.END}")
        return True
    
    # If not found in sessions, check legacy monitors
    monitors = load_monitors()
    
    if session_id in monitors:
        info = monitors[session_id]
        
        # Get the process ID
        pid = info.get('pid')
        
        if pid:
            try:
                # Send termination signal to the process
                os.kill(pid, signal.SIGTERM)
                print(f"{Colors.GREEN}Sent termination signal to legacy monitor process.{Colors.END}")
            except OSError:
                # Process might not exist anymore
                pass
        
        # Remove from monitors
        del monitors[session_id]
        save_monitors(monitors)
        
        # Also end associated session if it exists
        if 'session_id' in info:
            try:
                end_session(info['session_id'])
            except:
                pass
        
        print(f"{Colors.GREEN}Legacy monitor ended.{Colors.END}")
        return True
    
    print(f"{Colors.RED}Error: No monitor found with ID {session_id}.{Colors.END}")
    return False

def view_monitor(session_id, show_analysis_only=False):
    """
    View the output of a running monitor by connecting to it.
    
    Args:
        session_id: ID of the session or monitor to view
        show_analysis_only: If True, only show analysis without raw log lines
        
    Returns:
        True if the monitor was found and connected to, False otherwise
    """
    # First check session-based monitors
    sessions = load_sessions()
    
    if session_id in sessions:
        info = sessions[session_id]
        
        if info.get('type') != 'log_monitor':
            print(f"{Colors.RED}Error: Not a log monitor session.{Colors.END}")
            return False
        
        # Get the log file
        log_file = info.get('log_file')
        model = info.get('model', 'qwen2.5-coder:0.5b')
        analyze = info.get('analyze', True)
        
        if not log_file or not os.path.exists(log_file):
            print(f"{Colors.RED}Error: Log file no longer exists.{Colors.END}")
            return False
        
        print(f"{Colors.GREEN}Connecting to monitor for {log_file}...{Colors.END}")
        from .monitor import monitor_log
        
        # Start monitoring in foreground mode (will show output)
        monitor_log(log_file, background=False, analyze=analyze, model=model, 
                   show_analysis_only=show_analysis_only)
        return True
    
    # If not found in sessions, check legacy monitors
    monitors = load_monitors()
    
    if session_id in monitors:
        info = monitors[session_id]
        
        # Get the log file
        log_file = info.get('log_file')
        model = info.get('model', 'qwen2.5-coder:0.5b')
        analyze = info.get('analyze', True)
        
        if not log_file or not os.path.exists(log_file):
            print(f"{Colors.RED}Error: Log file no longer exists.{Colors.END}")
            return False
        
        print(f"{Colors.GREEN}Connecting to legacy monitor for {log_file}...{Colors.END}")
        from .monitor import monitor_log
        
        # Start monitoring in foreground mode (will show output)
        monitor_log(log_file, background=False, analyze=analyze, model=model,
                   show_analysis_only=show_analysis_only)
        return True
    
    print(f"{Colors.RED}Error: No monitor found with ID {session_id}.{Colors.END}")
    return False

def open_session_monitor(session_id=None, show_analysis_only=False):
    """
    Open and connect to a specific log monitor session.
    
    Args:
        session_id: Optional session ID to connect to. If not provided, will prompt user to select
        show_analysis_only: If True, only show analysis without raw log lines
        
    Returns:
        True if successfully connected to a monitor, False otherwise
    """
    if not session_id:
        # Display active monitors first
        has_monitors = list_active_log_monitors(non_interactive=True)
        
        if not has_monitors:
            print(f"{Colors.YELLOW}No active monitors found to connect to.{Colors.END}")
            return False
        
        # Ask the user to select a monitor
        try:
            session_num = int(input(f"{Colors.GREEN}Enter monitor number to connect to (or 0 to cancel): {Colors.END}"))
            if session_num <= 0:
                print(f"{Colors.YELLOW}Operation cancelled.{Colors.END}")
                return False
                
            # Get the mapping of indices to session IDs
            log_monitors = get_active_log_monitors()
            legacy_monitors = load_monitors()
            
            index_to_id = {}
            
            # Map session-based monitors
            for i, sid in enumerate(log_monitors.keys(), 1):
                index_to_id[i] = sid
                
            # Map legacy monitors
            offset = len(log_monitors)
            for i, mid in enumerate(legacy_monitors.keys(), offset + 1):
                index_to_id[i] = mid
                
            if session_num not in index_to_id:
                print(f"{Colors.RED}Invalid monitor number.{Colors.END}")
                return False
                
            session_id = index_to_id[session_num]
        except ValueError:
            print(f"{Colors.RED}Invalid input. Please enter a number.{Colors.END}")
            return False
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return False
    
    # Connect to the selected monitor
    return view_monitor(session_id, show_analysis_only) 