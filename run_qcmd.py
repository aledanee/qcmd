#!/usr/bin/env python3
"""
Run script for QCMD using the modular architecture.
This script is useful for development and testing without installing the package.
"""

import sys
import os

# Add the parent directory to the path for direct execution
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the main entry point from the modular structure
from qcmd_cli.commands.handler import main

if __name__ == "__main__":
    # Pass command line arguments to the main function
    sys.exit(main()) 