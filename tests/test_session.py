#!/usr/bin/env python3
"""
Tests for session management functionality.
"""

import unittest
import os
import sys
import json
import tempfile
import time
from unittest.mock import patch, MagicMock

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import functions to test
from qcmd_cli.utils.session import (
    save_session, load_sessions, create_session, update_session_activity,
    end_session, cleanup_stale_sessions, is_process_running
)
from qcmd_cli.config.settings import CONFIG_DIR


class TestSessionManagement(unittest.TestCase):
    """Test the session management functionality."""
    
    def setUp(self):
        """Set up a temporary sessions file for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sessions_file = os.path.join(self.temp_dir.name, "sessions.json")
        self.sessions_patch = patch('qcmd_cli.utils.session.SESSIONS_FILE', self.sessions_file)
        self.sessions_patch.start()
        
    def tearDown(self):
        """Clean up temporary files and patches."""
        self.sessions_patch.stop()
        self.temp_dir.cleanup()
    
    def test_save_and_load_session(self):
        """Test that a session can be saved and loaded."""
        test_session = {
            "type": "test_session",
            "model": "test-model",
            "start_time": "2023-01-01 12:00:00",
            "pid": 12345
        }
        
        # Test saving
        result = save_session("test-session-id", test_session)
        self.assertTrue(result)
        
        # Verify file was created
        self.assertTrue(os.path.exists(self.sessions_file))
        
        # Test loading
        sessions = load_sessions()
        self.assertIn("test-session-id", sessions)
        self.assertEqual(sessions["test-session-id"]["type"], "test_session")
        self.assertEqual(sessions["test-session-id"]["model"], "test-model")
    
    def test_create_session(self):
        """Test creating a new session."""
        session_info = {
            "type": "interactive_shell",
            "model": "llama3"
        }
        
        with patch('os.getpid', return_value=54321):
            session_id = create_session(session_info)
        
        # Verify session ID format (should be a UUID)
        self.assertTrue(len(session_id) > 30)
        
        # Verify session was saved
        sessions = load_sessions()
        self.assertIn(session_id, sessions)
        
        # Verify metadata was added
        saved_session = sessions[session_id]
        self.assertEqual(saved_session["type"], "interactive_shell")
        self.assertEqual(saved_session["model"], "llama3")
        self.assertEqual(saved_session["pid"], 54321)
        self.assertIn("created_at", saved_session)
        self.assertIn("last_activity", saved_session)
    
    def test_update_session_activity(self):
        """Test updating session activity timestamp."""
        # Create a session
        test_session = {
            "type": "test_session",
            "last_activity": time.time() - 1000  # Set this to the past
        }
        save_session("activity-test-id", test_session)
        
        # Update activity
        old_time = test_session["last_activity"]
        result = update_session_activity("activity-test-id")
        
        # Verify result
        self.assertTrue(result)
        
        # Verify timestamp was updated
        sessions = load_sessions()
        new_time = sessions["activity-test-id"]["last_activity"]
        self.assertGreater(new_time, old_time)
    
    def test_end_session(self):
        """Test ending a session."""
        # Create two sessions
        save_session("session-to-end", {"type": "test"})
        save_session("session-to-keep", {"type": "test"})
        
        # End one session
        result = end_session("session-to-end")
        
        # Verify result
        self.assertTrue(result)
        
        # Verify session was removed
        sessions = load_sessions()
        self.assertNotIn("session-to-end", sessions)
        self.assertIn("session-to-keep", sessions)
    
    def test_cleanup_stale_sessions(self):
        """Test cleaning up stale sessions."""
        # Create sessions with different PIDs
        save_session("active-session", {"pid": os.getpid()})
        save_session("stale-session", {"pid": 99999})  # Unlikely to exist
        
        # Mock is_process_running for testing
        original_is_process_running = is_process_running
        try:
            # Replace with mock implementation
            def mock_is_process_running(pid):
                return pid == os.getpid()
                
            # Monkey patch the function
            globals()['is_process_running'] = mock_is_process_running
            
            # Call cleanup
            active_sessions = cleanup_stale_sessions()
            
            # Verify only active session remains
            self.assertIn("active-session", active_sessions)
            self.assertNotIn("stale-session", active_sessions)
            
            # Verify file was updated
            sessions = load_sessions()
            self.assertIn("active-session", sessions)
            self.assertNotIn("stale-session", sessions)
            
        finally:
            # Restore original function
            globals()['is_process_running'] = original_is_process_running
    

if __name__ == '__main__':
    unittest.main() 