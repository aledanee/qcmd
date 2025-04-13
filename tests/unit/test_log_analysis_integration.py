#!/usr/bin/env python3
"""
Tests for integration between log analysis components.
"""

import unittest
import os
import sys
import json
import tempfile
import time
from unittest.mock import patch, MagicMock, call

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test
from qcmd_cli.log_analysis.log_files import (
    handle_log_analysis, handle_log_selection, 
    list_active_log_monitors, stop_log_monitor
)
from qcmd_cli.log_analysis.monitor import monitor_log
from qcmd_cli.log_analysis.analyzer import analyze_log_file
from qcmd_cli.utils.session import (
    create_log_monitor_session, get_active_log_monitors, 
    load_sessions, end_session
)


class TestLogAnalysisIntegration(unittest.TestCase):
    """Test the integration between log analysis components."""
    
    def setUp(self):
        """Set up a temporary environment for testing."""
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
    
    def test_handle_log_selection_with_analyze_once(self):
        """Test handle_log_selection with analyze once option."""
        with patch('builtins.input', return_value='a'), \
             patch('qcmd_cli.log_analysis.analyzer.analyze_log_file') as mock_analyze:
            
            handle_log_selection(self.test_log_file, "test-model")
            
            # Verify analyze_log_file was called correctly
            mock_analyze.assert_called_once_with(self.test_log_file, "test-model")
    
    def test_handle_log_selection_with_monitor(self):
        """Test handle_log_selection with monitor option."""
        with patch('builtins.input', return_value='m'), \
             patch('qcmd_cli.log_analysis.monitor.monitor_log') as mock_monitor:
            
            handle_log_selection(self.test_log_file, "test-model")
            
            # Verify monitor_log was called correctly
            mock_monitor.assert_called_once_with(
                self.test_log_file, 
                background=True, 
                analyze=True, 
                model="test-model"
            )
    
    def test_handle_log_selection_with_watch(self):
        """Test handle_log_selection with watch option."""
        with patch('builtins.input', return_value='w'), \
             patch('qcmd_cli.log_analysis.monitor.monitor_log') as mock_monitor:
            
            handle_log_selection(self.test_log_file, "test-model")
            
            # Verify monitor_log was called correctly
            mock_monitor.assert_called_once_with(
                self.test_log_file, 
                background=True, 
                analyze=False, 
                model="test-model"
            )
    
    def test_handle_log_analysis_with_specific_file(self):
        """Test handle_log_analysis with a specific file path."""
        with patch('builtins.input', return_value='1'), \
             patch('qcmd_cli.log_analysis.analyzer.analyze_log_file') as mock_analyze, \
             patch('qcmd_cli.log_analysis.log_files.list_active_log_monitors'):
            
            handle_log_analysis("test-model", self.test_log_file)
            
            # Verify analyze_log_file was called with the specific file
            mock_analyze.assert_called_once()
    
    def test_handle_log_analysis_with_no_monitors(self):
        """Test handle_log_analysis when no monitors are active."""
        # Create empty monitoring state
        with open(self.sessions_file, 'w') as f:
            json.dump({}, f)
        
        # Mock user inputs and function calls
        with patch('builtins.input', side_effect=['c', 'q']), \
             patch('qcmd_cli.log_analysis.log_files.find_log_files', return_value=[self.test_log_file]), \
             patch('qcmd_cli.log_analysis.log_files.display_log_selection', return_value=None) as mock_display:
            
            handle_log_analysis("test-model")
            
            # Verify display_log_selection was called
            mock_display.assert_called_once()
    
    def test_handle_log_analysis_stop_monitor(self):
        """Test handle_log_analysis when stopping a monitor."""
        # Create test session data
        session_id = "test-session-1"
        test_sessions = {
            session_id: {
                "type": "log_monitor",
                "log_file": self.test_log_file,
                "pid": os.getpid(),
                "model": "test-model",
                "analyze": True
            }
        }
        
        with open(self.sessions_file, 'w') as f:
            json.dump(test_sessions, f)
        
        # Mock inputs and function calls
        with patch('builtins.input', side_effect=['s', '1', 'n']), \
             patch('qcmd_cli.utils.session.is_process_running', return_value=True), \
             patch('qcmd_cli.log_analysis.log_files.stop_log_monitor') as mock_stop:
            
            handle_log_analysis("test-model")
            
            # Verify stop_log_monitor was called with the session ID
            mock_stop.assert_called_once_with(session_id)
    
    def test_stop_monitor_with_invalid_session(self):
        """Test stopping a monitor with an invalid session ID."""
        # Empty sessions file
        with open(self.sessions_file, 'w') as f:
            json.dump({}, f)
            
        # Try to stop a non-existent session
        result = stop_log_monitor("non-existent-session")
        
        # Should return False
        self.assertFalse(result)
    
    def test_handle_log_analysis_journalctl(self):
        """Test handle_log_analysis with a journalctl service."""
        journalctl_log = "journalctl:test.service"
        
        # Mock inputs and functions
        with patch('builtins.input', side_effect=['c', journalctl_log, 'a']), \
             patch('qcmd_cli.log_analysis.log_files.find_log_files', return_value=[journalctl_log]), \
             patch('qcmd_cli.log_analysis.log_files.display_log_selection', return_value=journalctl_log), \
             patch('tempfile.NamedTemporaryFile'), \
             patch('subprocess.check_output', return_value="Test log content"), \
             patch('qcmd_cli.log_analysis.analyzer.analyze_log_file') as mock_analyze:
            
            handle_log_analysis("test-model")
            
            # Verify analyze_log_file was called (specific arguments are hard to test due to temp file)
            mock_analyze.assert_called_once()
    
    def test_active_log_monitors_integration(self):
        """Test the integration between get_active_log_monitors and list_active_log_monitors."""
        # Create test session data
        test_sessions = {
            "test-session-1": {
                "type": "log_monitor",
                "log_file": self.test_log_file,
                "pid": os.getpid(),
                "model": "test-model",
                "analyze": True,
                "start_time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        
        with open(self.sessions_file, 'w') as f:
            json.dump(test_sessions, f)
        
        # Mock process check and capture print output
        with patch('qcmd_cli.utils.session.is_process_running', return_value=True), \
             patch('builtins.print') as mock_print:
            
            list_active_log_monitors()
            
            # Verify print was called with the expected text
            # We can't easily test the exact output, but we can check if a key phrase was printed
            found = False
            for call_args in mock_print.call_args_list:
                args = call_args[0]
                if args and isinstance(args[0], str) and "Active Log Monitors" in args[0]:
                    found = True
                    break
            
            self.assertTrue(found, "Active Log Monitors heading not found in output")


if __name__ == '__main__':
    unittest.main() 