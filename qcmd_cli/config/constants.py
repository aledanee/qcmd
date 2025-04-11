"""
Constants and configuration settings for QCMD.
"""

import os

# Paths
HOME_DIR = os.path.expanduser("~")
CONFIG_DIR = os.path.join(HOME_DIR, ".qcmd")
LOG_DIR = os.path.join(CONFIG_DIR, "logs")
SESSIONS_FILE = os.path.join(CONFIG_DIR, "sessions.json")

# API URLs
OLLAMA_API = os.environ.get("OLLAMA_API", "http://127.0.0.1:11434/api")

# Version
VERSION = "1.0.16"

# System prompt template for command generation
SYSTEM_PROMPT_TEMPLATE = """You are QCMD, an AI assistant specialized in Linux system administration, log analysis, and command generation. 
Your goal is to provide accurate, secure, and helpful commands based on user requests.

- Generate shell commands that are valid for Linux systems.
- Prioritize safety and security in your suggestions.
- Explain complex commands when necessary.
- Always verify that commands won't harm the system.
- Suggest alternatives when relevant.

Current system context:
- User shell: {user_shell}
- OS: {os_info}
- Working directory: {cwd}

Respond only with the command(s) that would accomplish the task. Do not include explanations or markdown formatting."""

# Default number of log lines to show
DEFAULT_LOG_LINES = 100 