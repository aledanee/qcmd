"""
QCMD CLI - A command-line tool that generates shell commands using Qwen2.5-Coder via Ollama.
"""

__version__ = "1.0.15"

# Don't import modules here to avoid circular dependencies

# Import main functionality from submodules
from .commands.handler import main
from .core.command_generator import generate_command, execute_command, list_models
from .core.interactive_shell import start_interactive_shell, auto_mode
from .log_analysis.analyzer import analyze_log_file, analyze_log_content
from .log_analysis.log_files import find_log_files, handle_log_analysis
from .log_analysis.monitor import save_monitors, load_monitors, cleanup_stale_monitors
from .utils.history import save_to_history, load_history, show_history
from .utils.session import save_session, load_sessions, cleanup_stale_sessions, end_session
from .utils.system import check_for_updates, display_system_status
from .config.settings import load_config, save_config, handle_config_command
from .ui.display import Colors, print_cool_header, print_examples, print_iraq_banner

# Also keep direct import available for backward compatibility
from . import qcmd, post_install 