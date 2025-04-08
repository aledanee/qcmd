#!/usr/bin/env python3
"""
Post-installation script for qcmd.
Shows the Iraq banner and installation success message.
"""

import os
import sys
from . import __version__
from .qcmd import print_iraq_banner, Colors

def main():
    """Display the installation success message with the Iraq banner."""
    # Force banner to display regardless of config settings
    os.environ['QCMD_FORCE_BANNER'] = 'true'
    
    # Display the banner
    print_iraq_banner()
    
    # Show installation success message
    print(f"{Colors.GREEN}Thank you for installing QCMD version {__version__}!{Colors.END}")
    print(f"{Colors.CYAN}Run 'qcmd --help' to see available commands.{Colors.END}")
    print(f"{Colors.YELLOW}Run 'qcmd --shell' to start an interactive shell.{Colors.END}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 