#!/usr/bin/env python3
"""
Setup script for qcmd.
"""

import os
import sys
import subprocess
from setuptools import setup

# Use pyproject.toml for package configuration
if __name__ == "__main__":
    setup()
    
    # Run post-installation script
    try:
        subprocess.call([sys.executable, "-m", "qcmd_cli.post_install"])
    except Exception:
        # Don't fail installation if post-install script fails
        pass 