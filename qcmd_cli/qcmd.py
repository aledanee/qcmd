#!/usr/bin/env python3
"""
qcmd - A simple command-line tool that generates shell commands using Qwen2.5-Coder via Ollama.

Version: 1.0.0
Copyright (c) 2024
License: MIT

This file is maintained for backward compatibility with the previous single-file structure.
All functionality has been moved to a more modular structure.
"""

# Import all functionality from the new modular structure
from qcmd_cli.commands.handler import main, parse_args
from qcmd_cli.core.command_generator import (
    generate_command, analyze_error, fix_command, list_models, 
    execute_command, is_dangerous_command, DANGEROUS_PATTERNS
)
from qcmd_cli.core.interactive_shell import start_interactive_shell, auto_mode, SimpleCompleter
from qcmd_cli.log_analysis.analyzer import analyze_log_file, analyze_log_content, read_large_file
from qcmd_cli.log_analysis.log_files import (
    find_log_files, is_log_file, display_log_selection,
    handle_log_analysis, handle_log_selection
)
from qcmd_cli.log_analysis.monitor import save_monitors, load_monitors, cleanup_stale_monitors, monitor_log
from qcmd_cli.utils.history import save_to_history, load_history, show_history
from qcmd_cli.utils.session import save_session, load_sessions, cleanup_stale_sessions, end_session, is_process_running
from qcmd_cli.utils.system import get_system_status, check_ollama_status, display_system_status, check_for_updates
from qcmd_cli.config.settings import (
    load_config, save_config, handle_config_command, get_config_path,
    DEFAULT_MODEL, DEFAULT_TEMPERATURE, DEFAULT_MAX_ATTEMPTS, DEFAULT_CHECK_UPDATES, DEFAULT_UI_SETTINGS
)
from qcmd_cli.ui.display import (
    Colors, print_cool_header, print_examples, print_iraq_banner,
    show_download_progress, display_help_command
)

# These functions are now imported from modules, but kept for backwards compatibility

if __name__ == "__main__":
    main() 