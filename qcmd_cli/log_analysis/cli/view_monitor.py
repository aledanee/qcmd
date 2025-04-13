#!/usr/bin/env python3
"""
Command-line tool for viewing active log monitors.
This allows users to easily connect to any active log monitor session
to see real-time log entries and analysis.
"""
import os
import sys
import argparse
from typing import List, Dict, Optional, Any

# Add the parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from qcmd_cli.log_analysis.log_files import open_session_monitor, list_active_log_monitors
from qcmd_cli.ui.display import Colors, print_cool_header

def parse_args():
    """
    Parse command-line arguments.
    
    Returns:
        The parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description='View and connect to active log monitors',
    )
    
    parser.add_argument('-l', '--list', action='store_true',
                       help='Only list active monitors without connecting')
    parser.add_argument('-s', '--session-id', type=str,
                       help='Directly connect to a specific session ID')
    parser.add_argument('-a', '--analysis-only', action='store_true',
                       help='Only show analysis results without raw log lines')
    parser.add_argument('-f', '--full-display', action='store_true',
                       help='Show both raw log lines and analysis (default)')
    
    return parser.parse_args()

def main():
    """
    Main entry point for the log monitor viewer.
    """
    args = parse_args()
    
    # Print a simple header
    print_cool_header("QCMD Log Monitor Viewer")
    
    # Determine display mode
    show_analysis_only = args.analysis_only
    if args.full_display:
        show_analysis_only = False
    
    # If session ID is provided, connect directly to that monitor
    if args.session_id:
        print(f"{Colors.CYAN}Connecting to monitor session: {args.session_id}{Colors.END}")
        if show_analysis_only:
            print(f"{Colors.YELLOW}Display mode: Analysis only (log lines hidden){Colors.END}")
        else:
            print(f"{Colors.YELLOW}Display mode: Full (showing log lines and analysis){Colors.END}")
        open_session_monitor(args.session_id, show_analysis_only)
        return
    
    # If only listing is requested, show the list and exit
    if args.list:
        print(f"{Colors.CYAN}Listing active log monitors:{Colors.END}")
        list_active_log_monitors(non_interactive=True)
        return
    
    # Otherwise, show the interactive list of monitors
    print(f"{Colors.CYAN}Select a monitor to connect to:{Colors.END}")
    if show_analysis_only:
        print(f"{Colors.YELLOW}Display mode: Analysis only (log lines hidden){Colors.END}")
    else:
        print(f"{Colors.YELLOW}Display mode: Full (showing log lines and analysis){Colors.END}")
    print(f"{Colors.GREEN}Note: Press 'm' while viewing to toggle between display modes.{Colors.END}")
    open_session_monitor(show_analysis_only=show_analysis_only)

if __name__ == "__main__":
    main() 