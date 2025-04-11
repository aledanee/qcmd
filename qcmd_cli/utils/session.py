#!/usr/bin/env python3
"""
Session management functionality for QCMD.
"""
import os
import json
import time
import signal
import sys
import uuid
from typing import Dict, List, Optional, Any

from ..config.settings import CONFIG_DIR

# File path for storing session info
SESSIONS_FILE = os.path.join(CONFIG_DIR, "sessions.json")

def create_session(session_info: Dict[str, Any]) -> str:
    """
    Create a new session and save it to persistent storage.
    
    Args:
        session_info: Dictionary with session information
        
    Returns:
        Session ID as a string
    """
    # Generate a unique session ID
    session_id = str(uuid.uuid4())
    
    # Add metadata
    session_info['pid'] = os.getpid()
    session_info['created_at'] = time.time()
    session_info['last_activity'] = time.time()
    
    # Save to storage
    save_session(session_id, session_info)
    
    return session_id

def update_session_activity(session_id: str) -> bool:
    """
    Update the last activity timestamp for a session.
    
    Args:
        session_id: ID of the session to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        sessions = load_sessions()
        if session_id in sessions:
            sessions[session_id]['last_activity'] = time.time()
            
            with open(SESSIONS_FILE, 'w') as f:
                json.dump(sessions, f, indent=2)
            
            return True
        return False
    except Exception as e:
        print(f"Error updating session activity: {e}", file=sys.stderr)
        return False

def save_session(session_id, session_info):
    """
    Save session information to persistent storage.
    
    Args:
        session_id: Unique identifier for the session
        session_info: Dictionary with session information
    """
    try:
        # Create config directory if it doesn't exist
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR, exist_ok=True)
        
        # Load existing sessions
        sessions = {}
        if os.path.exists(SESSIONS_FILE):
            with open(SESSIONS_FILE, 'r') as f:
                try:
                    sessions = json.load(f)
                except json.JSONDecodeError:
                    pass
        
        # Update with new session
        sessions[session_id] = session_info
        
        # Write back to file
        with open(SESSIONS_FILE, 'w') as f:
            json.dump(sessions, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving session: {e}", file=sys.stderr)
        return False

def load_sessions():
    """
    Load all saved sessions.
    
    Returns:
        Dictionary of session IDs to session information
    """
    sessions = {}
    try:
        if os.path.exists(SESSIONS_FILE):
            with open(SESSIONS_FILE, 'r') as f:
                try:
                    sessions = json.load(f)
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        print(f"Error loading sessions: {e}", file=sys.stderr)
    
    return sessions

def cleanup_stale_sessions():
    """
    Remove sessions that are no longer valid.
    """
    sessions = load_sessions()
    active_sessions = {}
    
    for session_id, session_info in sessions.items():
        pid = session_info.get('pid')
        if pid and is_process_running(pid):
            active_sessions[session_id] = session_info
    
    # Write cleaned sessions back to file
    try:
        with open(SESSIONS_FILE, 'w') as f:
            json.dump(active_sessions, f, indent=2)
    except Exception as e:
        print(f"Error saving cleaned sessions: {e}", file=sys.stderr)
    
    return active_sessions

def end_session(session_id):
    """
    End a specific session.
    
    Args:
        session_id: ID of the session to end
    """
    try:
        sessions = load_sessions()
        if session_id in sessions:
            del sessions[session_id]
            
            with open(SESSIONS_FILE, 'w') as f:
                json.dump(sessions, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error ending session: {e}", file=sys.stderr)
        return False

def is_process_running(pid):
    """
    Check if a process with the given PID is running.
    
    Args:
        pid: Process ID to check
        
    Returns:
        True if the process is running, False otherwise
    """
    try:
        pid = int(pid)  # Ensure pid is an integer
        # For Unix/Linux/MacOS
        if os.name == 'posix':
            # A simple check using kill with signal 0
            # which doesn't actually send a signal
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False
        # For Windows
        elif os.name == 'nt':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            SYNCHRONIZE = 0x00100000
            process = kernel32.OpenProcess(SYNCHRONIZE, 0, pid)
            if process != 0:
                kernel32.CloseHandle(process)
                return True
            else:
                return False
        else:
            # Unknown OS
            return False
    except (ValueError, TypeError):
        return False 