#!/usr/bin/env python3
"""
Demo script to show the expected behavior of the log file selection with improved error messaging.
This demonstrates the fix for issue #9.
"""
import os
import sys

# Add the parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from qcmd_cli.ui.display import Colors

def simulate_display_log_selection():
    """
    Simulate the log file selection process with our enhanced error messaging.
    """
    # Mock log files
    log_files = [
        '/var/log/syslog',
        '/var/log/auth.log',
        '/var/log/kern.log'
    ]
    
    # Display log file options
    print(f"\n{Colors.GREEN}{Colors.BOLD}Found {len(log_files)} log files:{Colors.END}")
    
    # Group logs by directory (simplified for demo)
    dir_name = "/var/log"
    
    # Display logs
    print(f"\n{Colors.CYAN}{dir_name}:{Colors.END}")
    
    # Create file indices
    file_indices = {}
    for idx, file in enumerate(log_files, start=1):
        base_name = os.path.basename(file)
        print(f"  {Colors.BOLD}{idx}{Colors.END}. {base_name}")
        file_indices[idx] = file
    
    # Demonstrate scenarios
    
    # Scenario 1: User selects a valid option
    print("\n--- Scenario 1: Valid selection ---")
    choice = 2
    print(f"{Colors.GREEN}User enters: {choice}{Colors.END}")
    if choice in file_indices:
        print(f"Selected file: {file_indices[choice]}")
    
    # Scenario 2: User selects an invalid option
    print("\n--- Scenario 2: Invalid selection (before fix) ---")
    choice = 5  # Beyond the valid range
    print(f"{Colors.GREEN}User enters: {choice}{Colors.END}")
    if choice in file_indices:
        print(f"Selected file: {file_indices[choice]}")
    else:
        print(f"{Colors.YELLOW}Invalid selection. Please try again.{Colors.END}")
        # In the old implementation, the function would exit here without retry
        print("Function would exit without retrying - causing issue #9")
    
    # Scenario 3: User selects an invalid option with our fix
    print("\n--- Scenario 3: Invalid selection (with our fix) ---")
    choice = 5  # Beyond the valid range
    print(f"{Colors.GREEN}User enters: {choice}{Colors.END}")
    if choice in file_indices:
        print(f"Selected file: {file_indices[choice]}")
    else:
        print(f"{Colors.YELLOW}Invalid selection '{choice}'. Please enter a number between 1 and {len(file_indices)}.{Colors.END}")
        # With the while loop, the function would loop back to ask for input again
        print("Function would loop back for retry (due to while True loop)")
        print(f"{Colors.GREEN}User enters: 2{Colors.END} (on the second try)")
        print(f"Selected file: {file_indices[2]}")

if __name__ == "__main__":
    simulate_display_log_selection() 