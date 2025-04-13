#!/usr/bin/env python3
"""
Demo script for QCMD log monitoring functionality.

This script demonstrates the various ways to use the log monitoring features:
1. Analyze a log file once
2. Monitor a log file with analysis
3. Monitor a log file without analysis (just watch)
4. List active monitors
5. View a monitor
6. Stop a monitor
"""

import os
import time
import subprocess
import signal
import sys
import tempfile
import threading

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import needed modules
from qcmd_cli.log_analysis.log_files import (
    analyze_log_file, handle_log_analysis, handle_log_selection,
    list_active_log_monitors, stop_log_monitor, view_monitor
)
from qcmd_cli.log_analysis.monitor import monitor_log
from qcmd_cli.ui.display import Colors


def generate_log_entries(log_file, count=5, interval=2):
    """Generate log entries to a file at specified intervals."""
    print(f"\n{Colors.GREEN}Starting log generator thread...{Colors.END}")
    for i in range(count):
        log_entry = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Demo log entry #{i+1}"
        if i % 3 == 0:
            log_entry += " - ERROR: This is a sample error message"
        
        with open(log_file, 'a') as f:
            f.write(log_entry + "\n")
        
        print(f"{Colors.BLUE}Added log entry #{i+1} to {log_file}{Colors.END}")
        time.sleep(interval)
    
    print(f"{Colors.GREEN}Log generator thread finished.{Colors.END}")


def demo_analyze_once():
    """Demo analyzing a log file once."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}DEMO 1: Analyze Log File Once{Colors.END}")
    
    # Create a temporary log file
    fd, temp_log = tempfile.mkstemp(suffix='.log')
    os.close(fd)
    
    # Write some content to the log
    with open(temp_log, 'w') as f:
        f.write("[2025-04-13 10:00:00] Starting application...\n")
        f.write("[2025-04-13 10:00:01] Initializing modules...\n")
        f.write("[2025-04-13 10:00:02] ERROR: Failed to load config.json\n")
        f.write("[2025-04-13 10:00:03] Using default configuration\n")
        f.write("[2025-04-13 10:00:04] Application started successfully\n")
    
    print(f"{Colors.GREEN}Created test log file: {temp_log}{Colors.END}")
    print(f"{Colors.GREEN}Analyzing log file once...{Colors.END}")
    
    # Analyze the log file
    try:
        analyze_log_file(temp_log, "qwen2.5-coder:0.5b")
    except KeyboardInterrupt:
        pass
    
    print(f"{Colors.GREEN}Demo 1 completed.{Colors.END}")
    
    # Clean up
    try:
        os.unlink(temp_log)
    except:
        pass
    
    return temp_log


def demo_monitor_analyze():
    """Demo monitoring a log file with analysis."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}DEMO 2: Monitor Log File with Analysis{Colors.END}")
    
    # Create a temporary log file
    fd, temp_log = tempfile.mkstemp(suffix='.log')
    os.close(fd)
    
    # Write initial content
    with open(temp_log, 'w') as f:
        f.write("[2025-04-13 10:15:00] Starting service...\n")
    
    print(f"{Colors.GREEN}Created test log file: {temp_log}{Colors.END}")
    print(f"{Colors.GREEN}Starting log monitoring with analysis...{Colors.END}")
    
    # Start a thread to generate log entries
    log_thread = threading.Thread(target=generate_log_entries, args=(temp_log,))
    log_thread.daemon = True
    
    # Start monitoring in background
    try:
        monitor_log(temp_log, background=True, analyze=True)
        log_thread.start()
        time.sleep(10)  # Let it run for a bit
    except KeyboardInterrupt:
        pass
    
    print(f"{Colors.GREEN}Demo 2 completed.{Colors.END}")
    
    return temp_log


def demo_monitor_watch():
    """Demo monitoring a log file without analysis (just watching)."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}DEMO 3: Watch Log File without Analysis{Colors.END}")
    
    # Create a temporary log file
    fd, temp_log = tempfile.mkstemp(suffix='.log')
    os.close(fd)
    
    # Write initial content
    with open(temp_log, 'w') as f:
        f.write("[2025-04-13 10:30:00] Starting watch demo...\n")
    
    print(f"{Colors.GREEN}Created test log file: {temp_log}{Colors.END}")
    print(f"{Colors.GREEN}Starting log monitoring without analysis (just watching)...{Colors.END}")
    
    # Start a thread to generate log entries
    log_thread = threading.Thread(target=generate_log_entries, args=(temp_log,))
    log_thread.daemon = True
    
    # Start monitoring in background
    try:
        monitor_log(temp_log, background=True, analyze=False)
        log_thread.start()
        time.sleep(10)  # Let it run for a bit
    except KeyboardInterrupt:
        pass
    
    print(f"{Colors.GREEN}Demo 3 completed.{Colors.END}")
    
    return temp_log


def demo_list_monitors():
    """Demo listing active monitors."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}DEMO 4: List Active Monitors{Colors.END}")
    
    print(f"{Colors.GREEN}Listing active monitors...{Colors.END}")
    
    # List active monitors (but don't ask for interactive options)
    # This would show the monitors we created in previous demos
    try:
        if hasattr(list_active_log_monitors, '__wrapped__'):
            # Use the original function if wrapped
            list_active_log_monitors.__wrapped__()
        else:
            # Otherwise, we just print what we would do
            print(f"{Colors.YELLOW}In a real execution, we would list all active monitors here.{Colors.END}")
    except KeyboardInterrupt:
        pass
    
    print(f"{Colors.GREEN}Demo 4 completed.{Colors.END}")


def demo_view_monitor():
    """Demo viewing a monitor."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}DEMO 5: View a Log Monitor{Colors.END}")
    
    # This would normally require user interaction to select a monitor ID
    # For demo purposes, we'll just print instructions
    print(f"{Colors.YELLOW}To view a monitor, you would use one of these commands:{Colors.END}")
    print(f"{Colors.BLUE}qcmd --view-monitor SESSION_ID{Colors.END}")
    print(f"{Colors.BLUE}or select a monitor number when running qcmd --list-monitors{Colors.END}")
    
    print(f"{Colors.GREEN}Demo 5 completed.{Colors.END}")


def demo_stop_monitor():
    """Demo stopping a monitor."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}DEMO 6: Stop a Log Monitor{Colors.END}")
    
    # This would normally require user interaction to select a monitor ID
    # For demo purposes, we'll just print instructions
    print(f"{Colors.YELLOW}To stop a monitor, you would use one of these commands:{Colors.END}")
    print(f"{Colors.BLUE}qcmd --stop-monitor SESSION_ID{Colors.END}")
    print(f"{Colors.BLUE}or select a monitor number when running qcmd --list-monitors{Colors.END}")
    
    print(f"{Colors.GREEN}Demo 6 completed.{Colors.END}")


def demo_command_line():
    """Show command line usage examples."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}COMMAND LINE USAGE EXAMPLES{Colors.END}")
    
    print(f"{Colors.YELLOW}Here are some command line examples:{Colors.END}")
    print(f"{Colors.BLUE}# Analyze a log file once without monitoring{Colors.END}")
    print(f"{Colors.BLUE}qcmd --logs --log-file /var/log/syslog --analyze-once{Colors.END}")
    print()
    
    print(f"{Colors.BLUE}# Monitor a log file with analysis{Colors.END}")
    print(f"{Colors.BLUE}qcmd --logs --log-file /var/log/syslog --monitor-analyze{Colors.END}")
    print()
    
    print(f"{Colors.BLUE}# Monitor a log file without analysis (just watch){Colors.END}")
    print(f"{Colors.BLUE}qcmd --logs --log-file /var/log/syslog --monitor-watch{Colors.END}")
    print()
    
    print(f"{Colors.BLUE}# List active monitors{Colors.END}")
    print(f"{Colors.BLUE}qcmd --list-monitors{Colors.END}")
    print()
    
    print(f"{Colors.BLUE}# View a monitor{Colors.END}")
    print(f"{Colors.BLUE}qcmd --view-monitor SESSION_ID{Colors.END}")
    print()
    
    print(f"{Colors.BLUE}# Stop a monitor{Colors.END}")
    print(f"{Colors.BLUE}qcmd --stop-monitor SESSION_ID{Colors.END}")
    print()


def cleanup(log_files):
    """Clean up log files and stop any active monitors."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}CLEANING UP{Colors.END}")
    
    # Remove log files
    for log_file in log_files:
        try:
            os.unlink(log_file)
            print(f"{Colors.GREEN}Removed log file: {log_file}{Colors.END}")
        except:
            pass


def main():
    """Run all the demos."""
    print(f"{Colors.CYAN}{Colors.BOLD}QCMD LOG MONITORING DEMOS{Colors.END}")
    
    try:
        log_files = []
        
        # Demo 1: Analyze once
        log_files.append(demo_analyze_once())
        
        # Demo 2: Monitor with analysis
        log_files.append(demo_monitor_analyze())
        
        # Demo 3: Monitor without analysis
        log_files.append(demo_monitor_watch())
        
        # Demo 4: List monitors
        demo_list_monitors()
        
        # Demo 5: View monitor
        demo_view_monitor()
        
        # Demo 6: Stop monitor
        demo_stop_monitor()
        
        # Show command line examples
        demo_command_line()
        
        # Clean up
        cleanup(log_files)
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}All demos completed successfully!{Colors.END}")
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Demo interrupted by user.{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Error in demo: {e}{Colors.END}")


if __name__ == "__main__":
    main() 