#!/usr/bin/env python3
"""
Additional tests for the monitor module to improve test coverage.
"""
import unittest
import os
import sys
import json
import tempfile
import time
import signal
from unittest.mock import patch, MagicMock, mock_open, call

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test
from qcmd_cli.log_analysis.monitor import (
    save_monitors, load_monitors, cleanup_stale_monitors, 
    monitor_log, MONITORS_FILE
)
from qcmd_cli.ui.display import Colors
from qcmd_cli.log_analysis.analyzer import analyze_log_content


class TestMonitorAdditional(unittest.TestCase):
    """Additional tests for the monitor module."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.monitor_file_path = os.path.join(self.temp_dir.name, 'monitors.json')
        self.test_log_file = os.path.join(self.temp_dir.name, 'test.log')
        
        # Create a test log file
        with open(self.test_log_file, 'w') as f:
            f.write("Test log line 1\nTest log line 2\n")
    
    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()
    
    @patch('qcmd_cli.log_analysis.monitor.os.path.join')
    @patch('builtins.open')
    @patch('sys.stderr')
    def test_save_monitors_exception(self, mock_stderr, mock_open, mock_join):
        """Test save_monitors handles file writing exceptions."""
        # Mock os.path.join to return our test file path
        mock_join.return_value = self.monitor_file_path
        
        # Mock open to raise an exception when writing to file
        mock_open.side_effect = PermissionError("Permission denied")
        
        # Create test monitors
        test_monitors = {
            'monitor1': {'pid': 12345, 'log_file': self.test_log_file}
        }
        
        # Call save_monitors and verify exception is handled
        save_monitors(test_monitors)
        
        # Verify error message was printed to stderr
        self.assertTrue(mock_stderr.write.called)
    
    @patch('qcmd_cli.log_analysis.monitor.os.path.join')
    @patch('qcmd_cli.log_analysis.monitor.os.path.exists')
    @patch('builtins.open')
    def test_load_monitors_corrupted_json(self, mock_open, mock_exists, mock_join):
        """Test load_monitors handles corrupted JSON data."""
        # Mock os.path.join to return our test file path
        mock_join.return_value = self.monitor_file_path
        
        # Mock file existence
        mock_exists.return_value = True
        
        # Mock open to return corrupted JSON data
        mock_open.return_value = mock_open(read_data="{ invalid json data")
        
        # Call load_monitors and verify empty dict is returned on JSON error
        monitors = load_monitors()
        
        # Verify an empty dictionary is returned
        self.assertEqual(monitors, {})
    
    @patch('qcmd_cli.log_analysis.monitor.os.path.join')
    @patch('qcmd_cli.log_analysis.monitor.load_monitors')
    @patch('qcmd_cli.log_analysis.monitor.save_monitors')
    def test_cleanup_stale_monitors_null_pid(self, mock_save, mock_load, mock_join):
        """Test cleanup_stale_monitors handles monitors with null PIDs."""
        # Mock os.path.join to return our test file path
        mock_join.return_value = self.monitor_file_path
        
        # Create test monitors with one having a null PID
        test_monitors = {
            'monitor1': {'pid': 12345, 'log_file': self.test_log_file},
            'monitor2': {'pid': None, 'log_file': '/var/log/other.log'},
            'monitor3': {'log_file': '/var/log/third.log'}  # Missing pid key
        }
        
        # Mock load_monitors to return our test data
        mock_load.return_value = test_monitors
        
        # Mock os.kill to simulate a running process for monitor1
        with patch('qcmd_cli.log_analysis.monitor.os.kill') as mock_kill:
            # Configure mock to make the first monitor appear active
            def kill_side_effect(pid, sig):
                if pid == 12345:
                    return None  # Process exists
                else:
                    raise OSError("No such process")
            
            mock_kill.side_effect = kill_side_effect
            
            # Call cleanup_stale_monitors
            result = cleanup_stale_monitors()
            
            # Verify result includes only monitor1 and excludes those with null PIDs
            self.assertEqual(len(result), 1)
            self.assertIn('monitor1', result)
            self.assertNotIn('monitor2', result)
            self.assertNotIn('monitor3', result)
            
            # Verify save_monitors was called with the updated monitors
            mock_save.assert_called_once()
    
    @patch('qcmd_cli.log_analysis.monitor.os.path.join')
    @patch('qcmd_cli.log_analysis.monitor.os.fork')
    @patch('qcmd_cli.log_analysis.monitor.load_monitors')
    @patch('qcmd_cli.log_analysis.monitor.save_monitors')
    @patch('qcmd_cli.log_analysis.monitor.os.getpid')
    @patch('sys.exit')  # Add this to prevent actual exit
    def test_monitor_log_cleanup_function(self, mock_exit, mock_getpid, mock_save, mock_load, mock_fork, mock_join):
        """Test the cleanup function in monitor_log."""
        # Mock os.path.join to return our test file path
        mock_join.return_value = self.monitor_file_path
        
        # Mock os.fork to simulate a child process (return 0)
        mock_fork.return_value = 0
        
        # Mock os.getpid to return a known PID
        mock_getpid.return_value = 54321
        
        # Create test monitors
        test_monitors = {
            'monitor_12345': {'pid': 12345, 'log_file': '/var/log/other.log'},
            'monitor_54321': {'pid': 54321, 'log_file': self.test_log_file}  # This matches our mock PID
        }
        
        # Mock load_monitors to return our test data when cleanup is called
        mock_load.return_value = test_monitors
        
        # Setup signal handler mock to capture the registered handler
        signal_handlers = {}
        def mock_signal(sig, handler):
            signal_handlers[sig] = handler
        
        # Create a KeyboardInterrupt to break out of the monitoring loop
        with patch('signal.signal', side_effect=mock_signal):
            with patch('time.sleep', side_effect=KeyboardInterrupt):  # Break the loop on first iteration
                with patch('builtins.print'):  # Suppress output
                    # Call monitor_log in background mode
                    monitor_log(self.test_log_file, background=True)
                    
                    # Verify signal handlers were registered
                    self.assertIn(signal.SIGTERM, signal_handlers)
                    self.assertIn(signal.SIGINT, signal_handlers)
                    
                    # Simulate calling the SIGTERM handler to trigger cleanup
                    signal_handlers[signal.SIGTERM](signal.SIGTERM, None)
                    
                    # Verify sys.exit was called
                    mock_exit.assert_called_once_with(0)
                    
                    # Verify save_monitors was called with updated monitors (without our PID)
                    assert mock_save.call_count >= 1
                    # In the last call, our monitor should be removed
                    last_call_monitors = mock_save.call_args[0][0]
                    self.assertNotIn('monitor_54321', last_call_monitors)
    
    @patch('qcmd_cli.log_analysis.monitor.time.sleep')
    @patch('qcmd_cli.log_analysis.monitor.os.path.getsize')
    @patch('builtins.open')
    @patch('builtins.print')
    @patch('qcmd_cli.log_analysis.monitor.analyze_log_content')
    def test_monitor_log_file_update(self, mock_analyze, mock_print, mock_open, mock_getsize, mock_sleep):
        """Test the main monitoring loop in monitor_log detects file changes."""
        # Mock time.sleep to raise KeyboardInterrupt after a few calls
        # This allows us to break out of the while True loop after testing
        mock_sleep.side_effect = [None, KeyboardInterrupt]
        
        # Configure getsize to return different values on subsequent calls
        # to simulate a growing log file
        mock_getsize.side_effect = [100, 150]  # Initial size, then a larger size
        
        # Mock file opening and reading
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.side_effect = ["Initial content", "New log entries"]
        mock_open.return_value = mock_file
        
        # Call monitor_log
        monitor_log(self.test_log_file, background=False, analyze=True)
        
        # Verify analyze_log_content was called twice:
        # 1. For initial file content
        # 2. For new content when file size increased
        self.assertEqual(mock_analyze.call_count, 2)
        
        # Verify the second call was with the new content
        mock_analyze.assert_has_calls([
            call("Initial content", self.test_log_file, "llama3:latest"),
            call("New log entries", self.test_log_file, "llama3:latest")
        ])
    
    @patch('builtins.print')
    @patch('qcmd_cli.log_analysis.monitor.os.path.getsize')
    @patch('qcmd_cli.log_analysis.monitor.os.path.exists')
    @patch('qcmd_cli.log_analysis.monitor.os.path.isfile')
    def test_monitor_log_exception_handling(self, mock_isfile, mock_exists, mock_getsize, mock_print):
        """Test exception handling in monitor_log."""
        # Mock file existence checks to pass
        mock_exists.return_value = True
        mock_isfile.return_value = True
        
        # Mock getsize to raise an exception
        mock_getsize.side_effect = PermissionError("Permission denied")
        
        # Call monitor_log which should catch the exception
        monitor_log(self.test_log_file, background=False)
        
        # Verify error message was printed
        mock_print.assert_any_call(f"{Colors.RED}Error monitoring log file: Permission denied{Colors.END}")
        
    @patch('qcmd_cli.log_analysis.monitor.time.sleep')
    @patch('qcmd_cli.log_analysis.monitor.os.path.getsize')
    @patch('builtins.open')
    @patch('builtins.print')
    @patch('qcmd_cli.log_analysis.monitor.analyze_log_content')
    def test_monitor_log_no_file_change(self, mock_analyze, mock_print, mock_open, mock_getsize, mock_sleep):
        """Test the monitoring loop when file size doesn't change."""
        # Mock time.sleep to raise KeyboardInterrupt after a few calls
        # This allows us to break out of the while True loop after testing
        mock_sleep.side_effect = [None, None, KeyboardInterrupt]
        
        # Configure getsize to return the same value to simulate a file that hasn't changed
        mock_getsize.return_value = 100
        
        # Mock file opening and reading for initial analysis
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "Initial content"
        mock_open.return_value = mock_file
        
        # Call monitor_log
        monitor_log(self.test_log_file, background=False, analyze=True)
        
        # Verify analyze_log_content was called only once for the initial content
        # and not called again since the file didn't change
        mock_analyze.assert_called_once_with("Initial content", self.test_log_file, "llama3:latest")
        
        # Verify sleep was called multiple times in the monitoring loop
        self.assertEqual(mock_sleep.call_count, 3)

    @patch('qcmd_cli.log_analysis.monitor.time.sleep')
    @patch('qcmd_cli.log_analysis.monitor.os.path.getsize')
    @patch('builtins.open')
    @patch('builtins.print')
    @patch('qcmd_cli.log_analysis.monitor.analyze_log_content')
    def test_monitor_log_no_analysis(self, mock_analyze, mock_print, mock_open, mock_getsize, mock_sleep):
        """Test monitoring without analysis (just printing content)."""
        # Mock time.sleep to raise KeyboardInterrupt after a few calls
        mock_sleep.side_effect = [None, KeyboardInterrupt]
        
        # Configure getsize to return different values to simulate file growth
        mock_getsize.side_effect = [100, 150]
        
        # Mock file opening and reading
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "New log entries"
        mock_open.return_value = mock_file
        
        # Call monitor_log with analyze=False
        monitor_log(self.test_log_file, background=False, analyze=False)
        
        # Verify analyze_log_content was not called
        mock_analyze.assert_not_called()
        
        # Verify the right messages were printed for non-analysis mode
        mock_print.assert_any_call(f"{Colors.CYAN}New log entries:{Colors.END}")


if __name__ == '__main__':
    unittest.main() 