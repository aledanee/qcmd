"""
Utility modules for QCMD CLI.
"""

# Import key modules
try:
    from .env_loader import get_version, get_env, get_ollama_api_url, get_request_timeout
except ImportError:
    # Placeholder if env_loader is not available
    pass

# For backward compatibility
from .history import save_to_history, load_history, show_history
from .session import save_session, load_sessions, cleanup_stale_sessions, end_session
from .system import check_for_updates, display_system_status
