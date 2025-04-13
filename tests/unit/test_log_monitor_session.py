#!/usr/bin/env python3
"""
Tests for log monitoring session functionality.
"""

import unittest
import os
import sys
import json
import tempfile
import time
import signal
from unittest.mock import patch, MagicMock, call

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test
from qcmd_cli.utils.session import (
    create_log_monitor_session, get_active_log_monitors, 
    load_sessions, save_session, end_session, update_session_activity
)
from qcmd_cli.log_analysis.log_files import list_active_log_monitors, stop_log_monitor, handle_log_analysis
from qcmd_cli.log_analysis.monitor import monitor_log, save_monitors, load_monitors, cleanup_stale_monitors


class TestLogMonitorSession(unittest.TestCase):
    """Test the log monitoring session functionality."""
    
    def setUp(self):
        """Set up a temporary sessions file for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sessions_file = os.path.join(self.temp_dir.name, "sessions.json")
        self.monitors_file = os.path.join(self.temp_dir.name, "active_monitors.json")
        
        # Patch sessions file path
        self.sessions_patch = patch('qcmd_cli.utils.session.SESSIONS_FILE', self.sessions_file)
        self.sessions_patch.start()
        
        # Patch monitors file path
        self.monitors_patch = patch('qcmd_cli.log_analysis.monitor.MONITORS_FILE', self.monitors_file)
        self.monitors_patch.start()
        
        # Create test log file
        self.test_log_file = os.path.join(self.temp_dir.name, "test.log")
        with open(self.test_log_file, 'w') as f:
            f.write("This is a test log file\n")
        
    def tearDown(self):
        """Clean up temporary files and patches."""
        self.sessions_patch.stop()
        self.monitors_patch.stop()
        self.temp_dir.cleanup()
    
    def test_create_log_monitor_session(self):
        """Test creating a log monitor session."""
        log_file = self.test_log_file
        model = "qwen2.5-coder:0.5b"
        
        with patch('qcmd_cli.utils.session.os.getpid', return_value=12345):
            session_id = create_log_monitor_session(log_file, model)
            
            # Verify session was created
            with open(self.sessions_file, 'r') as f:
                sessions = json.load(f)
                
            self.assertIn(session_id, sessions)
            session = sessions[session_id]
            self.assertEqual(session['type'], 'log_monitor')
            self.assertEqual(session['log_file'], log_file)
            self.assertEqual(session['model'], model)
            self.assertEqual(session['pid'], 12345)
            self.assertTrue(session['analyze'])
    
    def test_get_active_log_monitors(self):
        """Test getting active log monitor sessions."""
        # Create a mock session file with a log monitor session
        test_sessions = {
            "test-session-1": {
                "type": "log_monitor",
                "log_file": "/var/log/test1.log",
                "pid": os.getpid(),  # Current process should be considered running
                "model": "qwen2.5-coder:0.5b",
                "analyze": True
            },
            "test-session-2": {
                "type": "log_monitor",
                "log_file": "/var/log/test2.log",
                "pid": 99999,  # This process likely doesn't exist
                "model": "qwen2.5-coder:0.5b",
                "analyze": False
            },
            "test-session-3": {
                "type": "interactive_shell",  # Not a log monitor
                "pid": os.getpid()
            }
        }
        
        with open(self.sessions_file, 'w') as f:
            json.dump(test_sessions, f)
        
        # Mock the is_process_running function to only return True for the current process
        with patch('qcmd_cli.utils.session.is_process_running', 
                   side_effect=lambda pid: pid == os.getpid()):
            
            active_monitors = get_active_log_monitors()
            
            # Should only return the active log monitor session
            self.assertEqual(len(active_monitors), 1)
            self.assertIn("test-session-1", active_monitors)
            self.assertNotIn("test-session-2", active_monitors)  # Inactive process
            self.assertNotIn("test-session-3", active_monitors)  # Not a log monitor
    
    def test_stop_log_monitor(self):
        """Test stopping a log monitor."""
        # Create a mock session file with a log monitor session
        test_pid = os.getpid()  # Use current process for testing
        test_sessions = {
            "test-session-1": {
                "type": "log_monitor",
                "log_file": "/var/log/test1.log",
                "pid": test_pid,
                "model": "qwen2.5-coder:0.5b"
            }
        }
        
        with open(self.sessions_file, 'w') as f:
            json.dump(test_sessions, f)
        
        # Mock os.kill to avoid actually killing our test process
        with patch('os.kill') as mock_kill:
            # Test stopping the monitor
            result = stop_log_monitor("test-session-1")
            
            # Should return True indicating success
            self.assertTrue(result)
            
            # Should have called kill with our PID
            mock_kill.assert_called_once_with(test_pid, signal.SIGTERM)
            
            # Session should be removed
            with open(self.sessions_file, 'r') as f:
                sessions = json.load(f)
                self.assertNotIn("test-session-1", sessions)
                
    def test_integration_monitor_session(self):
        """Test the integration between monitor and session systems"""
        # Set up a temporary log file
        log_file = self.test_log_file
        log_file.write_text("Sample log content")
        
        # Mock the main components
        mock_save = MagicMock()
        mock_load = MagicMock(return_value={
            'active-monitor': {
                'pid': 9999,
                'log_file': str(log_file),
                'started_at': '2022-01-01 00:00:00',
                'model': 'test-model'
            }
        })
        
        with patch('qcmd_cli.log_analysis.monitor.save_monitors', mock_save), \
             patch('qcmd_cli.log_analysis.monitor.load_monitors', mock_load):
            
            # Mock session functions
            mock_save_session = MagicMock()
            mock_load_sessions = MagicMock(return_value={
                'test-session-id': {
                    'created_at': '2022-01-01 00:00:00',
                    'last_active': '2022-01-01 00:00:00',
                    'monitor_id': 'active-monitor'
                }
            })
            mock_is_active = MagicMock(return_value=True)
            
            with patch('qcmd_cli.utils.session.save_session', mock_save_session), \
                 patch('qcmd_cli.utils.session.load_sessions', mock_load_sessions), \
                 patch('qcmd_cli.utils.session.is_session_active', mock_is_active):
                
                # Mock process existence check
                with patch('psutil.pid_exists', lambda pid: True):
                    
                    # Create a monitor with a session
                    result = monitor_log(str(log_file), 'test-model', background=True)
                    assert result, "Monitor should have been created"
                    
                    # When listing active monitors, ensure it uses the non-interactive mode
                    list_result = list_active_log_monitors(non_interactive=True)
                    assert list_result, "Should have found active monitors"
                    
                    # Verify the session was saved
                    assert mock_save_session.called, "Session should have been saved"
                    
                    # Verify the session info
                    call_args = mock_save_session.call_args[0]
                    assert len(call_args) >= 1, "Session save should have been called with session ID"
                    session_id = call_args[0]
                    
                    # Check that the session was created with the monitor ID
                    mock_save_session.assert_called_with(
                        session_id,
                        {
                            'created_at': mock.ANY,
                            'last_active': mock.ANY,
                            'monitor_id': mock.ANY
                        }
                    )
                    
                    # Test session update
                    update_session_activity(session_id)
                    assert mock_save_session.call_count >= 2, "Session should have been updated"
    
    def test_cleanup_stale_monitors(self):
        """Test cleaning up stale monitors."""
        # Skip the real file operations and focus on the logic
        active_pid = os.getpid()
        stale_pid = 99999  # Unlikely to exist
        
        # Test data
        test_monitor_data = {
            "active-monitor": {
                "pid": active_pid,
                "session_id": "active-session-id"
            },
            "stale-monitor": {
                "pid": stale_pid,
                "session_id": "stale-session-id"
            }
        }
        
        # Mock load_monitors to return our test data
        with patch('qcmd_cli.log_analysis.monitor.load_monitors', return_value=test_monitor_data), \
             patch('qcmd_cli.log_analysis.monitor.save_monitors') as mock_save, \
             patch('qcmd_cli.log_analysis.monitor.is_process_running', lambda pid: int(pid) == active_pid), \
             patch('qcmd_cli.utils.session.end_session') as mock_end_session:
            
            # Run the cleanup
            result = cleanup_stale_monitors()
            
            # Verify end_session was called with stale session ID
            mock_end_session.assert_called_once_with("stale-session-id")
            
            # Verify save_monitors was called with only the active monitor
            self.assertEqual(len(mock_save.call_args[0][0]), 1)
            self.assertIn("active-monitor", mock_save.call_args[0][0])
            self.assertNotIn("stale-monitor", mock_save.call_args[0][0])
            
            # Verify the result includes only the active monitor
            self.assertEqual(len(result), 1)
            self.assertIn("active-monitor", result)
    
    def test_foreground_monitoring_creates_session(self):
        """Test that foreground monitoring creates a session."""
        # Use specific file path to avoid issues with path differences
        absolute_test_file = os.path.abspath(self.test_log_file)
        
        # Mock to avoid actually monitoring
        with patch('qcmd_cli.utils.session.create_log_monitor_session', return_value="test-session-id") as mock_create_session, \
             patch('qcmd_cli.log_analysis.monitor.signal.signal'), \
             patch('qcmd_cli.log_analysis.monitor.os.path.getsize', return_value=0), \
             patch('qcmd_cli.log_analysis.monitor.time.sleep', side_effect=KeyboardInterrupt):
            
            # This should return due to KeyboardInterrupt in the mock
            monitor_log(absolute_test_file, background=False, analyze=True, model="test-model")
            
            # Verify session creation was called with the correct parameters
            mock_create_session.assert_called_once_with(absolute_test_file, "test-model", True)
    
    def test_session_cleanup_on_exit(self):
        """Test that the session is cleaned up when monitoring ends."""
        session_id = "test-cleanup-session"
        absolute_test_file = os.path.abspath(self.test_log_file)
        
        # Create a session
        test_sessions = {
            session_id: {
                "type": "log_monitor",
                "log_file": absolute_test_file,
                "pid": os.getpid(),
                "model": "test-model"
            }
        }
        
        with open(self.sessions_file, 'w') as f:
            json.dump(test_sessions, f)
        
        # Mock necessary functions and cause a KeyboardInterrupt to exit monitoring
        with patch('qcmd_cli.utils.session.create_log_monitor_session', return_value=session_id), \
             patch('qcmd_cli.utils.session.end_session') as mock_end_session, \
             patch('qcmd_cli.log_analysis.monitor.signal.signal'), \
             patch('qcmd_cli.log_analysis.monitor.os.path.getsize', return_value=0), \
             patch('qcmd_cli.log_analysis.monitor.time.sleep', side_effect=KeyboardInterrupt), \
             patch('qcmd_cli.utils.session.is_process_running', return_value=True), \
             patch('qcmd_cli.log_analysis.monitor.is_process_running', return_value=True):
            
            # This should return due to KeyboardInterrupt in the mock
            monitor_log(absolute_test_file, background=False)
            
            # Verify end_session was called with our session ID
            mock_end_session.assert_called_once_with(session_id)


if __name__ == '__main__':
    unittest.main() 