#!/usr/bin/env python3
"""
QCMD - A command-line tool that generates shell commands using Qwen2.5-Coder via Ollama.
This is the main entry point for the modular architecture.
"""

from qcmd_cli.commands.handler import main

if __name__ == "__main__":
    main() 