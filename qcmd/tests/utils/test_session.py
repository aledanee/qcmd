#!/usr/bin/env python3
"""
Tests for the session management functionality.
"""
import unittest
import os
import sys
import json
import tempfile
import time
from unittest.mock import patch, mock_open, MagicMock, PropertyMock

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test
from qcmd_cli.utils.session import (
    save_session, load_sessions, cleanup_stale_sessions,
    end_session, is_process_running, SESSIONS_FILE
)


class TestSessionManagement(unittest.TestCase):
    """Test the session management functions."""
    
    def setUp(self):
        """Set up temporary files for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_sessions_file = os.path.join(self.temp_dir.name, 'sessions.json')
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    @patch('qcmd_cli.utils.session.os.makedirs')
    @patch('qcmd_cli.utils.session.os.path.exists')
    def test_save_session(self, mock_exists, mock_makedirs):
        """Test saving session information."""
        # Set up mock to make os.path.exists return False for CONFIG_DIR
        mock_exists.return_value = False
        
        # Patch the SESSIONS_FILE constant
        with patch('qcmd_cli.utils.session.SESSIONS_FILE', self.temp_sessions_file):
            with patch('qcmd_cli.utils.session.CONFIG_DIR', self.temp_dir.name):
                # Test with empty sessions file (not yet exists)
                session_id = "test-session-1"
                session_info = {"pid": 12345, "start_time": 1617717600, "cmd": "test_command"}
                
                # Save the session
                result = save_session(session_id, session_info)
                
                # Check that the function returns success
                self.assertTrue(result)
                
                # Verify that directory is created
                mock_makedirs.assert_called_once_with(self.temp_dir.name, exist_ok=True)
                
                # Set mock exists to True for the second part of the test
                mock_exists.return_value = True
                
                # Set up file for the second test
                with open(self.temp_sessions_file, 'w') as f:
                    f.write("{}")
                
                # Test saving session again
                session_id = "test-session-2"
                session_info = {"pid": 67890, "start_time": 1617717700, "cmd": "other_command"}
                
                result = save_session(session_id, session_info)
                
                # Verify file was written with correct content
                with open(self.temp_sessions_file, 'r') as f:
                    sessions = json.load(f)
                    self.assertIn(session_id, sessions)
                    self.assertEqual(sessions[session_id]["pid"], 67890)
    
    def test_load_sessions(self):
        """Test loading sessions from file."""
        # Patch the SESSIONS_FILE constant
        with patch('qcmd_cli.utils.session.SESSIONS_FILE', self.temp_sessions_file):
            # Create test sessions data
            test_sessions = {
                "session1": {"pid": 12345, "start_time": 1617717600, "cmd": "test_command"},
                "session2": {"pid": 67890, "start_time": 1617717700, "cmd": "other_command"}
            }
            
            # Write test data to file
            os.makedirs(os.path.dirname(self.temp_sessions_file), exist_ok=True)
            with open(self.temp_sessions_file, 'w') as f:
                json.dump(test_sessions, f)
            
            # Test loading sessions
            sessions = load_sessions()
            
            # Verify correct sessions were loaded
            self.assertEqual(len(sessions), 2)
            self.assertIn("session1", sessions)
            self.assertIn("session2", sessions)
            self.assertEqual(sessions["session1"]["pid"], 12345)
            self.assertEqual(sessions["session2"]["pid"], 67890)
    
    @patch('qcmd_cli.utils.session.is_process_running')
    def test_cleanup_stale_sessions(self, mock_is_process_running):
        """Test cleaning up stale sessions."""
        # Setup test sessions data
        test_sessions = {
            "active-session": {"pid": 12345, "start_time": int(time.time()), "cmd": "active_command"},
            "stale-session": {"pid": 67890, "start_time": int(time.time()) - 86400, "cmd": "stale_command"}
        }
        
        # Configure mock to make only the first session appear active
        def is_process_running_side_effect(pid):
            return pid == 12345  # Only the active session is running
        
        mock_is_process_running.side_effect = is_process_running_side_effect
        
        # Write test data to the temporary file
        os.makedirs(os.path.dirname(self.temp_sessions_file), exist_ok=True)
        with open(self.temp_sessions_file, 'w') as f:
            json.dump(test_sessions, f)
        
        # Patch the SESSIONS_FILE constant
        with patch('qcmd_cli.utils.session.SESSIONS_FILE', self.temp_sessions_file):
            # Run the cleanup function
            active_sessions = cleanup_stale_sessions()
            
            # Verify that only the active session remains
            self.assertEqual(len(active_sessions), 1)
            self.assertIn("active-session", active_sessions)
            self.assertNotIn("stale-session", active_sessions)
            
            # Verify that the file was updated with only the active session
            with open(self.temp_sessions_file, 'r') as f:
                saved_sessions = json.load(f)
                self.assertEqual(len(saved_sessions), 1)
                self.assertIn("active-session", saved_sessions)
                self.assertNotIn("stale-session", saved_sessions)
    
    def test_end_session(self):
        """Test ending a session."""
        # Create test sessions data
        test_sessions = {
            "active-session-1": {"pid": 12345, "start_time": int(time.time()), "cmd": "command1"},
            "active-session-2": {"pid": 67890, "start_time": int(time.time()), "cmd": "command2"}
        }
        
        # Write test data to the temporary file
        os.makedirs(os.path.dirname(self.temp_sessions_file), exist_ok=True)
        with open(self.temp_sessions_file, 'w') as f:
            json.dump(test_sessions, f)
        
        # Patch the SESSIONS_FILE constant and test ending an existing session
        with patch('qcmd_cli.utils.session.SESSIONS_FILE', self.temp_sessions_file):
            # End one of the sessions
            result = end_session("active-session-1")
            
            # Verify the session was removed
            self.assertTrue(result)
            
            # Verify only one session remains in the file
            with open(self.temp_sessions_file, 'r') as f:
                saved_sessions = json.load(f)
                self.assertEqual(len(saved_sessions), 1)
                self.assertNotIn("active-session-1", saved_sessions)
                self.assertIn("active-session-2", saved_sessions)
    
    @patch('os.kill')
    def test_is_process_running_posix(self, mock_kill):
        """Test checking if a process is running on POSIX systems."""
        # Mock os.name to be 'posix'
        with patch('os.name', 'posix'):
            # Test with a running process
            mock_kill.return_value = None  # No exception
            self.assertTrue(is_process_running(12345))
            mock_kill.assert_called_with(12345, 0)
            
            # Test with a non-existent process
            mock_kill.side_effect = OSError()
            self.assertFalse(is_process_running(67890))
    
    @unittest.skipIf(os.name != 'nt', "Windows-specific test")
    def test_is_process_running_windows(self):
        """Test checking if a process is running on Windows."""
        # This test will be skipped on non-Windows platforms
        with patch('ctypes.windll.kernel32.OpenProcess') as mock_open_process:
            with patch('ctypes.windll.kernel32.CloseHandle') as mock_close_handle:
                # Test with a running process
                mock_open_process.return_value = 1234  # Non-zero handle
                self.assertTrue(is_process_running(12345))
                mock_close_handle.assert_called_once_with(1234)
                
                # Test with a non-existent process
                mock_open_process.return_value = 0  # Zero handle
                self.assertFalse(is_process_running(67890))


if __name__ == '__main__':
    unittest.main() 