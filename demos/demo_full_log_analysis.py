#!/usr/bin/env python3
"""
Full demonstration of log file selection and analysis workflow.
This script shows how the log selection works with our fix for issue #9,
and includes the subsequent log analysis.
"""
import os
import sys
import time
from typing import List, Dict, Optional

# Add the parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from qcmd_cli.ui.display import Colors

def simulate_log_analysis_workflow():
    """
    Simulate the entire log analysis workflow, from selection to analysis.
    """
    print(f"{Colors.GREEN}Starting log analysis tool...{Colors.END}")
    
    # Step 1: Find log files (mocked for the demo)
    print(f"{Colors.BLUE}Searching for log files...{Colors.END}")
    time.sleep(1)  # Simulate short search time
    
    log_files = [
        '/var/log/syslog',
        '/var/log/auth.log', 
        '/var/log/kern.log',
        '/var/log/nginx/access.log',
        '/var/log/nginx/error.log'
    ]
    
    # Step 2: Display log selection UI
    print(f"\n{Colors.GREEN}{Colors.BOLD}Found {len(log_files)} log files:{Colors.END}")
    
    # Group logs by directory for better organization
    logs_by_dir = {
        "/var/log": ['/var/log/syslog', '/var/log/auth.log', '/var/log/kern.log'],
        "/var/log/nginx": ['/var/log/nginx/access.log', '/var/log/nginx/error.log']
    }
    
    # Display logs grouped by directory
    index = 1
    file_indices = {}
    
    for dir_name, files in sorted(logs_by_dir.items()):
        print(f"\n{Colors.CYAN}{dir_name}:{Colors.END}")
        for file in sorted(files):
            base_name = os.path.basename(file)
            print(f"  {Colors.BOLD}{index}{Colors.END}. {base_name}")
            file_indices[index] = file
            index += 1
    
    # Step 3: Simulate user selection with errors
    
    # First, demonstrate invalid selection that triggers our improved error message
    print("\n--- Demonstration of improved error handling ---")
    print(f"\n{Colors.GREEN}Enter number to select a log file (or q to cancel): {Colors.END}7")
    print(f"{Colors.YELLOW}Invalid selection '7'. Please enter a number between 1 and 5.{Colors.END}")
    
    # User tries again with a valid selection
    print(f"\n{Colors.GREEN}Enter number to select a log file (or q to cancel): {Colors.END}2")
    selected_log = file_indices[2]
    print(f"Selected: {selected_log}")
    
    # Step 4: Ask if user wants to analyze or monitor
    print(f"\n{Colors.GREEN}Do you want to (a)nalyze once, (m)onitor with analysis, or just (w)atch without analysis? (a/m/w): {Colors.END}a")
    
    # Step 5: Simulate log analysis
    print(f"\n{Colors.CYAN}Analyzing log file: {selected_log}{Colors.END}")
    time.sleep(1)  # Simulate analysis time
    
    # Mock log content for auth.log
    log_content = """
May 10 10:15:22 server sshd[12345]: Accepted publickey for user1 from 192.168.1.10 port 55123
May 10 10:16:30 server sudo: user1 : TTY=pts/0 ; PWD=/home/user1 ; USER=root ; COMMAND=/usr/bin/apt update
May 10 10:20:15 server sshd[12346]: Failed password for invalid user admin from 203.0.113.42 port 22345
May 10 10:20:17 server sshd[12346]: Failed password for invalid user admin from 203.0.113.42 port 22347
May 10 10:20:19 server sshd[12346]: Failed password for invalid user admin from 203.0.113.42 port 22349
May 10 10:22:05 server sshd[12346]: Failed password for root from 203.0.113.42 port 22351
May 10 10:25:33 server sshd[12350]: Accepted publickey for user2 from 192.168.1.20 port 55456
May 10 10:30:45 server sudo: user2 : command not allowed ; TTY=pts/1 ; PWD=/var/www ; USER=root ; COMMAND=/usr/bin/vim /etc/shadow
    """
    
    # Step 6: Display analysis results
    print(f"\n{Colors.GREEN}Log Analysis Results:{Colors.END}")
    print(f"File: {selected_log}")
    print(f"Size: {len(log_content)} bytes")
    
    # Count lines and errors
    lines = log_content.splitlines()
    error_count = sum(1 for line in lines if "Failed" in line or "not allowed" in line)
    
    print(f"Total lines: {len(lines)}")
    print(f"Potential errors/exceptions: {error_count}")
    
    # Step 7: Provide more detailed analysis (simulated AI output)
    print(f"\n{Colors.CYAN}Detailed Analysis:{Colors.END}")
    print("""
Summary:
This log shows SSH login attempts and sudo command executions.

Issues Detected:
1. Multiple failed login attempts for 'admin' user from IP 203.0.113.42
2. Failed root login attempt from the same IP address
3. User 'user2' attempted to access a sensitive file (/etc/shadow) which was blocked

Recommendations:
1. Consider blocking IP 203.0.113.42 or implementing fail2ban
2. Review sudo permissions for user2
3. Continue monitoring for further suspicious activity
    """)

if __name__ == "__main__":
    simulate_log_analysis_workflow() 