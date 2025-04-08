#!/usr/bin/env python3
"""
Additional tests for the session management functionality to improve coverage.
"""
import unittest
import os
import sys
import json
import tempfile
from unittest.mock import patch, mock_open, MagicMock

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test
from qcmd_cli.utils.session import (
    save_session, load_sessions, cleanup_stale_sessions,
    end_session, is_process_running, SESSIONS_FILE
)


class TestSessionManagementAdditional(unittest.TestCase):
    """Additional tests for the session management functions."""
    
    def setUp(self):
        """Set up temporary files for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_sessions_file = os.path.join(self.temp_dir.name, 'sessions.json')
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    @patch('qcmd_cli.utils.session.os.makedirs')
    @patch('qcmd_cli.utils.session.os.path.exists')
    def test_save_session_exception_making_dir(self, mock_exists, mock_makedirs):
        """Test save_session handling exception when creating directory."""
        # Set up mock to make os.path.exists return False for CONFIG_DIR
        mock_exists.return_value = False
        
        # Simulate permission error when creating directory
        mock_makedirs.side_effect = PermissionError("Permission denied")
        
        # Patch the SESSIONS_FILE constant
        with patch('qcmd_cli.utils.session.SESSIONS_FILE', self.temp_sessions_file):
            with patch('qcmd_cli.utils.session.CONFIG_DIR', self.temp_dir.name):
                with patch('sys.stderr'):  # Suppress error output
                    # Test with empty sessions file (not yet exists)
                    session_id = "test-session-1"
                    session_info = {"pid": 12345, "start_time": 1617717600, "cmd": "test_command"}
                    
                    # Save the session - should handle exception and return False
                    result = save_session(session_id, session_info)
                    
                    # Check that the function returns failure
                    self.assertFalse(result)
    
    @patch('qcmd_cli.utils.session.os.path.exists')
    def test_save_session_json_decode_error(self, mock_exists):
        """Test save_session handling JSONDecodeError when reading existing file."""
        # Set up mock to make os.path.exists return True
        mock_exists.return_value = True
        
        # Patch open to return invalid JSON
        mock_file = mock_open(read_data="invalid_json{")
        
        # Patch the SESSIONS_FILE constant
        with patch('qcmd_cli.utils.session.SESSIONS_FILE', self.temp_sessions_file):
            with patch('qcmd_cli.utils.session.open', mock_file):
                with patch('sys.stderr'):  # Suppress error output
                    session_id = "test-session-1"
                    session_info = {"pid": 12345, "start_time": 1617717600, "cmd": "test_command"}
                    
                    # Save the session - should handle JSONDecodeError and continue
                    result = save_session(session_id, session_info)
                    
                    # Should still write new file with just this session
                    self.assertTrue(result)
                    
                    # Verify write was called
                    handle = mock_file()
                    handle.write.assert_called()
    
    @patch('qcmd_cli.utils.session.os.path.exists')
    def test_save_session_write_error(self, mock_exists):
        """Test save_session handling error when writing file."""
        # Set up mock to make os.path.exists return True
        mock_exists.return_value = True
        
        # Create mock file that raises error on write
        mock_file = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value.write.side_effect = IOError("Write error")
        mock_file.return_value = mock_context
        
        # Patch the SESSIONS_FILE constant
        with patch('qcmd_cli.utils.session.SESSIONS_FILE', self.temp_sessions_file):
            with patch('qcmd_cli.utils.session.open', mock_file):
                with patch('sys.stderr'):  # Suppress error output
                    session_id = "test-session-1"
                    session_info = {"pid": 12345, "start_time": 1617717600, "cmd": "test_command"}
                    
                    # Save the session - should handle IOError and return False
                    result = save_session(session_id, session_info)
                    
                    # Check that the function returns failure
                    self.assertFalse(result)
    
    @patch('qcmd_cli.utils.session.os.path.exists')
    def test_load_sessions_file_not_exists(self, mock_exists):
        """Test load_sessions when file doesn't exist."""
        # Set up mock to make os.path.exists return False
        mock_exists.return_value = False
        
        # Patch the SESSIONS_FILE constant
        with patch('qcmd_cli.utils.session.SESSIONS_FILE', self.temp_sessions_file):
            # Test loading sessions
            sessions = load_sessions()
            
            # Verify empty dict is returned
            self.assertEqual(sessions, {})
    
    @patch('qcmd_cli.utils.session.os.path.exists')
    def test_load_sessions_with_io_error(self, mock_exists):
        """Test load_sessions handling IO error."""
        # Set up mock to make os.path.exists return True
        mock_exists.return_value = True
        
        # Mock open to raise IOError
        mock_file = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.side_effect = IOError("Read error")
        mock_file.return_value = mock_context
        
        # Patch the SESSIONS_FILE constant
        with patch('qcmd_cli.utils.session.SESSIONS_FILE', self.temp_sessions_file):
            with patch('qcmd_cli.utils.session.open', mock_file):
                with patch('sys.stderr'):  # Suppress error output
                    # Test loading sessions - should handle IOError and return empty dict
                    sessions = load_sessions()
                    
                    # Verify empty dict is returned
                    self.assertEqual(sessions, {})
    
    @patch('qcmd_cli.utils.session.os.path.exists')
    def test_load_sessions_json_decode_error(self, mock_exists):
        """Test load_sessions handling JSONDecodeError."""
        # Set up mock to make os.path.exists return True
        mock_exists.return_value = True
        
        # Patch open to return invalid JSON
        mock_file = mock_open(read_data="invalid_json{")
        
        # Patch the SESSIONS_FILE constant
        with patch('qcmd_cli.utils.session.SESSIONS_FILE', self.temp_sessions_file):
            with patch('qcmd_cli.utils.session.open', mock_file):
                with patch('sys.stderr'):  # Suppress error output
                    # Test loading sessions with invalid JSON - should handle JSONDecodeError
                    sessions = load_sessions()
                    
                    # Verify empty dict is returned
                    self.assertEqual(sessions, {})
    
    @patch('qcmd_cli.utils.session.load_sessions')
    @patch('qcmd_cli.utils.session.is_process_running')
    def test_cleanup_stale_sessions_write_error(self, mock_is_process_running, mock_load_sessions):
        """Test cleanup_stale_sessions handling error when writing file."""
        # Setup test sessions data
        test_sessions = {
            "active-session": {"pid": 12345, "start_time": 1617717600, "cmd": "active_command"},
            "stale-session": {"pid": 67890, "start_time": 1617717600, "cmd": "stale_command"}
        }
        
        # Configure mock to return test sessions
        mock_load_sessions.return_value = test_sessions
        
        # Configure mock to make only the active session appear active
        mock_is_process_running.side_effect = lambda pid: pid == 12345
        
        # Create mock file that raises error on write
        mock_file = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value.write.side_effect = IOError("Write error")
        mock_file.return_value = mock_context
        
        # Patch the open function
        with patch('qcmd_cli.utils.session.open', mock_file):
            with patch('sys.stderr'):  # Suppress error output
                # Run the cleanup function - should handle IOError
                active_sessions = cleanup_stale_sessions()
                
                # Verify active sessions are correctly identified despite write error
                self.assertEqual(len(active_sessions), 1)
                self.assertIn("active-session", active_sessions)
    
    @patch('qcmd_cli.utils.session.load_sessions')
    @patch('qcmd_cli.utils.session.is_process_running')
    def test_cleanup_stale_sessions_no_pid(self, mock_is_process_running, mock_load_sessions):
        """Test cleanup_stale_sessions with sessions missing pid."""
        # Setup test sessions data
        test_sessions = {
            "session-with-pid": {"pid": 12345, "start_time": 1617717600, "cmd": "command1"},
            "session-no-pid": {"start_time": 1617717600, "cmd": "command2"}  # No pid
        }
        
        # Configure mock to return test sessions
        mock_load_sessions.return_value = test_sessions
        
        # Configure mock to consider any pid active
        mock_is_process_running.return_value = True
        
        # Patch the SESSIONS_FILE constant and open function
        with patch('qcmd_cli.utils.session.SESSIONS_FILE', self.temp_sessions_file):
            with patch('qcmd_cli.utils.session.open', mock_open()):
                # Run the cleanup function
                active_sessions = cleanup_stale_sessions()
                
                # Verify only session with pid is retained
                self.assertEqual(len(active_sessions), 1)
                self.assertIn("session-with-pid", active_sessions)
                self.assertNotIn("session-no-pid", active_sessions)
    
    @patch('qcmd_cli.utils.session.load_sessions')
    def test_end_session_not_found(self, mock_load_sessions):
        """Test end_session with session ID that doesn't exist."""
        # Setup test sessions data
        test_sessions = {
            "session-1": {"pid": 12345, "start_time": 1617717600, "cmd": "command1"}
        }
        
        # Configure mock to return test sessions
        mock_load_sessions.return_value = test_sessions
        
        # Patch the SESSIONS_FILE constant
        with patch('qcmd_cli.utils.session.SESSIONS_FILE', self.temp_sessions_file):
            # Try to end a non-existent session
            result = end_session("non-existent-session")
            
            # Verify the function returns success (even though session wasn't found)
            self.assertTrue(result)
    
    @patch('qcmd_cli.utils.session.load_sessions')
    def test_end_session_write_error(self, mock_load_sessions):
        """Test end_session handling error when writing file."""
        # Setup test sessions data
        test_sessions = {
            "session-1": {"pid": 12345, "start_time": 1617717600, "cmd": "command1"}
        }
        
        # Configure mock to return test sessions
        mock_load_sessions.return_value = test_sessions
        
        # Create mock file that raises error on write
        mock_file = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value.write.side_effect = IOError("Write error")
        mock_file.return_value = mock_context
        
        # Patch the open function
        with patch('qcmd_cli.utils.session.open', mock_file):
            with patch('sys.stderr'):  # Suppress error output
                # Try to end session - should handle IOError
                result = end_session("session-1")
                
                # Verify the function returns failure
                self.assertFalse(result)
    
    def test_is_process_running_invalid_pid(self):
        """Test is_process_running with invalid PID."""
        # Test with non-integer PID
        self.assertFalse(is_process_running("not-a-pid"))
        
        # Test with None PID
        self.assertFalse(is_process_running(None))
    
    def test_is_process_running_unknown_os(self):
        """Test is_process_running on unknown OS."""
        # Mock os.name to be something unknown
        with patch('os.name', 'unknown_os'):
            # Should return False for unknown OS
            self.assertFalse(is_process_running(12345))


if __name__ == '__main__':
    unittest.main() 