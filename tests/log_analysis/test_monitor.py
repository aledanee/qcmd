#!/usr/bin/env python3
"""
Tests for log monitoring functionality.
"""
import unittest
import os
import sys
import json
import tempfile
import time
from unittest.mock import patch, MagicMock, mock_open

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test
from qcmd_cli.log_analysis.monitor import (
    save_monitors, load_monitors, cleanup_stale_monitors, 
    monitor_log, MONITORS_FILE
)
from qcmd_cli.ui.display import Colors


class TestLogMonitor(unittest.TestCase):
    """Test the log monitoring functionality."""
    
    def setUp(self):
        """Set up temporary files for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_monitors_file = os.path.join(self.temp_dir.name, 'active_monitors.json')
        self.temp_log_file = os.path.join(self.temp_dir.name, 'test.log')
        
        # Create test log file
        with open(self.temp_log_file, 'w') as f:
            f.write("2023-01-01 12:00:00 ERROR: Failed to connect to database\n")
            f.write("2023-01-01 12:01:00 INFO: Retrying connection\n")
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    @patch('qcmd_cli.log_analysis.monitor.os.makedirs')
    def test_save_monitors(self, mock_makedirs):
        """Test saving monitor info to file."""
        # Setup test monitor data
        test_monitors = {
            "monitor1": {
                "log_file": "/var/log/test.log",
                "pid": 12345,
                "started_at": "2023-01-01 12:00:00",
                "model": "test-model",
                "analyze": True
            }
        }
        
        # We need to mock the file operations since we're not using the real filesystem path
        with patch('qcmd_cli.log_analysis.monitor.open', mock_open()) as mock_file:
            # Replace hardcoded path in function with our temp file
            with patch('qcmd_cli.log_analysis.monitor.os.path.join', return_value=self.temp_monitors_file):
                # Patch MONITORS_FILE as well for safety
                with patch('qcmd_cli.log_analysis.monitor.MONITORS_FILE', self.temp_monitors_file):
                    # Save the monitors
                    save_monitors(test_monitors)
                    
                    # Verify directory was created - now with our temp_monitors_file
                    mock_makedirs.assert_called_once_with(os.path.dirname(self.temp_monitors_file), exist_ok=True)
                    
                    # Verify file was opened for writing
                    mock_file.assert_called_once_with(self.temp_monitors_file, 'w')
                    
                    # Verify the correct data was written - json.dump writes in multiple calls
                    # So we check that write was called and that pid was in one of the write calls
                    handle = mock_file()
                    self.assertTrue(handle.write.called)
                    
                    # Check that key parts of our test data were written
                    call_args_list = [call_args[0][0] for call_args in handle.write.call_args_list]
                    self.assertTrue(any('12345' in arg for arg in call_args_list), "PID missing from written data")
                    self.assertTrue(any('test-model' in arg for arg in call_args_list), "Model missing from written data")
                    self.assertTrue(any('"/var/log/test.log"' in arg for arg in call_args_list), "Log file path missing from written data")
    
    def test_load_monitors(self):
        """Test loading monitors from file."""
        # Create test monitors data
        test_monitors = {
            "monitor1": {
                "log_file": "/var/log/test.log",
                "pid": 12345,
                "started_at": "2023-01-01 12:00:00",
                "model": "test-model",
                "analyze": True
            },
            "monitor2": {
                "log_file": "/var/log/system.log",
                "pid": 67890,
                "started_at": "2023-01-01 13:00:00",
                "model": "llama3",
                "analyze": False
            }
        }
        
        # Mock file operations
        mock_file_content = json.dumps(test_monitors)
        
        # Patch file existence check and open function
        with patch('qcmd_cli.log_analysis.monitor.os.path.exists', return_value=True):
            with patch('qcmd_cli.log_analysis.monitor.open', mock_open(read_data=mock_file_content)) as mock_file:
                # Patch MONITORS_FILE
                with patch('qcmd_cli.log_analysis.monitor.MONITORS_FILE', self.temp_monitors_file):
                    # Load the monitors
                    loaded_monitors = load_monitors()
                    
                    # Verify loaded data is correct
                    self.assertEqual(len(loaded_monitors), 2)
                    self.assertEqual(loaded_monitors["monitor1"]["pid"], 12345)
                    self.assertEqual(loaded_monitors["monitor2"]["pid"], 67890)
    
    def test_load_monitors_nonexistent(self):
        """Test loading monitors when file doesn't exist."""
        # Patch file existence check to return False
        with patch('qcmd_cli.log_analysis.monitor.os.path.exists', return_value=False):
            # Patch MONITORS_FILE
            with patch('qcmd_cli.log_analysis.monitor.MONITORS_FILE', self.temp_monitors_file):
                # Load the monitors
                loaded_monitors = load_monitors()
                
                # Verify empty dict is returned
                self.assertEqual(loaded_monitors, {})
    
    @patch('qcmd_cli.log_analysis.monitor.os.kill')
    def test_cleanup_stale_monitors(self, mock_kill):
        """Test cleaning up stale monitors."""
        # Setup test monitors data with both active and stale monitors
        test_monitors = {
            "active_monitor": {
                "log_file": "/var/log/test.log",
                "pid": 12345,
                "started_at": "2023-01-01 12:00:00",
                "model": "test-model",
                "analyze": True
            },
            "stale_monitor": {
                "log_file": "/var/log/system.log",
                "pid": 67890,
                "started_at": "2023-01-01 13:00:00",
                "model": "llama3",
                "analyze": False
            }
        }
        
        # Configure mock to make only the first monitor appear active
        def is_process_running_side_effect(pid, sig):
            if pid == 12345:
                return True  # Process exists
            else:
                raise OSError("No such process")
        
        mock_kill.side_effect = is_process_running_side_effect
        
        # Setup mocks for file operations
        with patch('qcmd_cli.log_analysis.monitor.load_monitors', return_value=test_monitors):
            with patch('qcmd_cli.log_analysis.monitor.save_monitors') as mock_save:
                # Patch MONITORS_FILE
                with patch('qcmd_cli.log_analysis.monitor.MONITORS_FILE', self.temp_monitors_file):
                    # Run the cleanup function
                    updated_monitors = cleanup_stale_monitors()
                    
                    # Verify only active monitor remains
                    self.assertEqual(len(updated_monitors), 1)
                    self.assertIn("active_monitor", updated_monitors)
                    self.assertNotIn("stale_monitor", updated_monitors)
                    
                    # Verify save was called with the updated monitors
                    mock_save.assert_called_once()
                    call_args = mock_save.call_args[0][0]  # First positional arg
                    self.assertEqual(len(call_args), 1)
                    self.assertIn("active_monitor", call_args)
    
    @patch('qcmd_cli.log_analysis.monitor.analyze_log_content')
    @patch('qcmd_cli.log_analysis.monitor.os.fork')
    @patch('builtins.print')
    def test_monitor_log_background(self, mock_print, mock_fork, mock_analyze):
        """Test monitoring a log file in background mode."""
        # Mock fork to simulate parent process
        mock_fork.return_value = 12345  # Non-zero PID means parent process
        
        # Mock the monitors data
        test_monitors = {}
        
        # Patch file operations and process handling
        with patch('qcmd_cli.log_analysis.monitor.load_monitors', return_value=test_monitors):
            with patch('qcmd_cli.log_analysis.monitor.save_monitors') as mock_save:
                with patch('qcmd_cli.log_analysis.monitor.os._exit'):  # Prevent actual process exit
                    # Call monitor_log in background mode
                    monitor_log(self.temp_log_file, background=True, analyze=True, model="test-model")
                    
                    # Verify fork was called
                    mock_fork.assert_called_once()
                    
                    # Verify save_monitors was called with correct data
                    mock_save.assert_called_once()
                    saved_data = mock_save.call_args[0][0]  # First positional arg
                    
                    # Verify the monitor was saved with correct data
                    self.assertEqual(len(saved_data), 1)
                    monitor_key = list(saved_data.keys())[0]
                    monitor_data = saved_data[monitor_key]
                    self.assertEqual(monitor_data['pid'], 12345)
                    self.assertEqual(monitor_data['log_file'], self.temp_log_file)
                    self.assertEqual(monitor_data['model'], "test-model")
                    self.assertTrue(monitor_data['analyze'])
                    
                    # Check that the correct messages were printed
                    expected_message = f"{Colors.GREEN}Started monitoring {self.temp_log_file} in background (PID: 12345).{Colors.END}"
                    mock_print.assert_any_call(expected_message)
    
    @patch('builtins.print')
    def test_monitor_log_file_not_found(self, mock_print):
        """Test error handling when file doesn't exist."""
        non_existent_file = os.path.join(self.temp_dir.name, 'nonexistent.log')
        
        # Call monitor_log with non-existent file
        monitor_log(non_existent_file)
        
        # Verify error message was printed
        mock_print.assert_any_call(f"{Colors.RED}Error: Log file '{non_existent_file}' does not exist.{Colors.END}")
    
    @patch('builtins.print')
    def test_monitor_log_not_a_file(self, mock_print):
        """Test error handling when path is not a file."""
        # Call monitor_log with a directory
        monitor_log(self.temp_dir.name)
        
        # Verify error message was printed
        mock_print.assert_any_call(f"{Colors.RED}Error: '{self.temp_dir.name}' is not a file.{Colors.END}")
    
    @patch('qcmd_cli.log_analysis.monitor.analyze_log_content')
    @patch('qcmd_cli.log_analysis.monitor.time.sleep', side_effect=KeyboardInterrupt)  # Simulate Ctrl+C
    @patch('builtins.print')
    def test_monitor_log_non_background(self, mock_print, mock_sleep, mock_analyze):
        """Test monitoring a log file in non-background mode."""
        # Call monitor_log in non-background mode
        monitor_log(self.temp_log_file, background=False, analyze=True, model="test-model")
        
        # Verify analyze_log_content was called
        mock_analyze.assert_called_once()
        
        # Check that the correct messages were printed
        mock_print.assert_any_call(f"{Colors.GREEN}Monitoring {Colors.BOLD}{self.temp_log_file}{Colors.END}")
        mock_print.assert_any_call(f"{Colors.GREEN}Press Ctrl+C to stop.{Colors.END}")
        mock_print.assert_any_call(f"\n{Colors.YELLOW}Monitoring stopped.{Colors.END}")


if __name__ == '__main__':
    unittest.main() 