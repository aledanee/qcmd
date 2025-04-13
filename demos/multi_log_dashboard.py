#!/usr/bin/env python3
"""
Multi-log Dashboard Demo for QCMD.

This script demonstrates how to set up monitoring for multiple log files
and create a simple dashboard to view their status.
"""

import os
import sys
import time
import tempfile
import threading
import subprocess
import random

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import needed modules
from qcmd_cli.log_analysis.monitor import monitor_log
from qcmd_cli.ui.display import Colors
from qcmd_cli.log_analysis.log_files import list_active_log_monitors


def create_test_log(name, initial_entries=3):
    """Create a test log file with initial entries."""
    fd, log_path = tempfile.mkstemp(prefix=f"qcmd_demo_{name}_", suffix='.log')
    os.close(fd)
    
    log_types = ["INFO", "WARNING", "ERROR", "DEBUG"]
    services = ["WebServer", "Database", "Authentication", "API", "Frontend"]
    
    with open(log_path, 'w') as f:
        # Add header
        f.write(f"# {name} Log File\n")
        f.write("#" + "=" * 40 + "\n\n")
        
        # Add initial entries
        for i in range(initial_entries):
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log_type = random.choice(log_types)
            service = random.choice(services)
            
            if log_type == "ERROR":
                message = f"Failed to {random.choice(['connect', 'process', 'authenticate', 'validate'])} - {random.randint(1000, 9999)}"
            elif log_type == "WARNING":
                message = f"Unusual {random.choice(['activity', 'latency', 'usage', 'pattern'])} detected"
            else:
                message = f"Operation {random.choice(['completed', 'started', 'processed', 'queued'])} successfully"
                
            log_entry = f"[{timestamp}] [{service}] {log_type}: {message}\n"
            f.write(log_entry)
    
    return log_path


def generate_log_entries(log_path, interval=2, count=10, name=""):
    """Generate random log entries for a log file."""
    log_types = ["INFO", "WARNING", "ERROR", "DEBUG"]
    weights = [0.6, 0.2, 0.15, 0.05]  # More common to have INFO entries
    services = ["WebServer", "Database", "Authentication", "API", "Frontend"]
    
    for i in range(count):
        try:
            # Sleep randomly between updates
            time.sleep(random.uniform(interval * 0.5, interval * 1.5))
            
            # Generate a random log entry
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log_type = random.choices(log_types, weights=weights)[0]
            service = random.choice(services)
            
            if log_type == "ERROR":
                message = f"Failed to {random.choice(['connect', 'process', 'authenticate', 'validate'])} - {random.randint(1000, 9999)}"
            elif log_type == "WARNING":
                message = f"Unusual {random.choice(['activity', 'latency', 'usage', 'pattern'])} detected"
            else:
                message = f"Operation {random.choice(['completed', 'started', 'processed', 'queued'])} successfully"
                
            log_entry = f"[{timestamp}] [{service}] {log_type}: {message}\n"
            
            # Append to the log file
            with open(log_path, 'a') as f:
                f.write(log_entry)
                
            print(f"{Colors.BLUE}Added entry to {name} log: {log_type}{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}Error adding to {name} log: {e}{Colors.END}")


def setup_multi_log_dashboard():
    """Set up monitoring for multiple log files."""
    print(f"{Colors.CYAN}{Colors.BOLD}QCMD Multi-Log Dashboard Demo{Colors.END}")
    print(f"{Colors.CYAN}This demo will create multiple log files and monitor them simultaneously.{Colors.END}")
    
    # Create test log files
    print(f"\n{Colors.GREEN}Creating test log files...{Colors.END}")
    app_log = create_test_log("Application", 5)
    db_log = create_test_log("Database", 3)
    auth_log = create_test_log("Authentication", 4)
    
    print(f"{Colors.GREEN}Created log files:{Colors.END}")
    print(f"  - Application Log: {app_log}")
    print(f"  - Database Log: {db_log}")
    print(f"  - Authentication Log: {auth_log}")
    
    # Start monitoring all logs
    print(f"\n{Colors.GREEN}Starting monitors for all logs...{Colors.END}")
    
    # Monitor app log with analysis
    print(f"{Colors.BLUE}Starting monitor for Application Log (with analysis)...{Colors.END}")
    monitor_log(app_log, background=True, analyze=True, model="qwen2.5-coder:0.5b")
    
    # Monitor DB log with analysis
    print(f"{Colors.BLUE}Starting monitor for Database Log (with analysis)...{Colors.END}")
    monitor_log(db_log, background=True, analyze=True, model="qwen2.5-coder:0.5b")
    
    # Monitor Auth log without analysis (just watching)
    print(f"{Colors.BLUE}Starting monitor for Authentication Log (watching only)...{Colors.END}")
    monitor_log(auth_log, background=True, analyze=False)
    
    # Start threads to generate logs
    print(f"\n{Colors.GREEN}Starting log generators...{Colors.END}")
    
    # Start a thread for each log file
    app_thread = threading.Thread(
        target=generate_log_entries, 
        args=(app_log, 3, 20, "Application")
    )
    db_thread = threading.Thread(
        target=generate_log_entries, 
        args=(db_log, 4, 15, "Database")
    )
    auth_thread = threading.Thread(
        target=generate_log_entries, 
        args=(auth_log, 5, 12, "Authentication")
    )
    
    app_thread.daemon = True
    db_thread.daemon = True
    auth_thread.daemon = True
    
    app_thread.start()
    db_thread.start()
    auth_thread.start()
    
    # Give time for some log entries to generate
    print(f"\n{Colors.YELLOW}Generating log entries for 10 seconds...{Colors.END}")
    time.sleep(10)
    
    # List active monitors (our dashboard)
    print(f"\n{Colors.GREEN}{Colors.BOLD}Multi-Log Dashboard{Colors.END}")
    list_active_log_monitors()
    
    # Instructions for the user
    print(f"\n{Colors.GREEN}{Colors.BOLD}Demo completed!{Colors.END}")
    print(f"{Colors.CYAN}You now have multiple log monitors running in the background.{Colors.END}")
    print(f"{Colors.CYAN}You can:{Colors.END}")
    print(f"  1. View any monitor: {Colors.BLUE}qcmd --list-monitors{Colors.END} then select 'v' and the monitor number")
    print(f"  2. Stop any monitor: {Colors.BLUE}qcmd --list-monitors{Colors.END} then select 's' and the monitor number")
    print(f"  3. Add more log entries manually:")
    print(f"     {Colors.BLUE}echo \"[$(date)] [Service] ERROR: New test error\" >> {app_log}{Colors.END}")
    
    # For cleaner demo, return the log files for potential cleanup
    return [app_log, db_log, auth_log]


def main():
    """Run the multi-log dashboard demo."""
    try:
        # Setup dashboard and get log file paths
        log_files = setup_multi_log_dashboard()
        
        # Keep the main thread running to allow the demo to continue
        print(f"\n{Colors.YELLOW}Press Ctrl+C to exit the demo...{Colors.END}")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Demo interrupted by user.{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Error in demo: {e}{Colors.END}")
    
    # Note: We intentionally don't clean up the log files or stop the monitors
    # so the user can continue to interact with them after the demo


if __name__ == "__main__":
    main() 