#!/usr/bin/env python3
"""
Tests for the log file handling functions in the log_files module.
"""
import unittest
import os
import sys
import tempfile
import subprocess
from unittest.mock import patch, MagicMock, call

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test
from qcmd_cli.log_analysis.log_files import (
    handle_log_analysis, handle_log_selection
)
from qcmd_cli.ui.display import Colors


class TestLogHandlers(unittest.TestCase):
    """Test the log file handler functions."""
    
    def setUp(self):
        """Set up the test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_log_file = os.path.join(self.temp_dir.name, 'test.log')
        
        # Create a test log file
        with open(self.test_log_file, 'w') as f:
            f.write("Test log line 1\nTest log line 2\n")
    
    def tearDown(self):
        """Clean up the test environment."""
        self.temp_dir.cleanup()
    
    @patch('qcmd_cli.log_analysis.log_files.analyze_log_file')
    @patch('builtins.input')
    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch('builtins.print')
    def test_handle_log_analysis_with_specific_file(self, mock_print, mock_isfile, 
                                                 mock_exists, mock_input, mock_analyze):
        """Test handling log analysis with a specific file path."""
        # Setup mocks
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_input.return_value = 'n'  # Don't monitor continuously
        
        # Call the function with a specific file path
        handle_log_analysis(model="test-model", file_path=self.test_log_file)
        
        # Verify analyze_log_file was called correctly
        mock_analyze.assert_called_once_with(self.test_log_file, "test-model", False)
        
        # Verify the input prompt about monitoring
        mock_input.assert_called_once()
        self.assertIn("Monitor this file", str(mock_input.call_args[0][0]))
    
    @patch('qcmd_cli.log_analysis.log_files.find_log_files')
    @patch('qcmd_cli.log_analysis.log_files.display_log_selection')
    @patch('builtins.print')
    def test_handle_log_analysis_no_files_found(self, mock_print, mock_display, mock_find):
        """Test handling log analysis when no log files are found."""
        # Setup mocks
        mock_find.return_value = []
        
        # Call the function without a specific file path
        handle_log_analysis(model="test-model")
        
        # Verify find_log_files was called
        mock_find.assert_called_once()
        
        # Verify display_log_selection was not called
        mock_display.assert_not_called()
        
        # Verify appropriate error message
        no_files_msg = f"{Colors.YELLOW}No accessible log files found on the system.{Colors.END}"
        mock_print.assert_any_call(no_files_msg)
    
    @patch('qcmd_cli.log_analysis.log_files.find_log_files')
    @patch('qcmd_cli.log_analysis.log_files.display_log_selection')
    @patch('builtins.print')
    def test_handle_log_analysis_user_cancelled(self, mock_print, mock_display, mock_find):
        """Test handling log analysis when user cancels the selection."""
        # Setup mocks
        mock_find.return_value = ["/var/log/syslog", "/var/log/auth.log"]
        mock_display.return_value = None  # User cancelled
        
        # Call the function without a specific file path
        handle_log_analysis(model="test-model")
        
        # Verify find_log_files was called
        mock_find.assert_called_once()
        
        # Verify display_log_selection was called with the log files
        mock_display.assert_called_once_with(["/var/log/syslog", "/var/log/auth.log"])
    
    @patch('qcmd_cli.log_analysis.log_files.analyze_log_file')
    @patch('builtins.input')
    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch('builtins.print')
    def test_handle_log_selection_regular_file(self, mock_print, mock_isfile, 
                                           mock_exists, mock_input, mock_analyze):
        """Test handling a selected regular log file."""
        # Setup mocks
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_input.return_value = 'a'  # Analyze once
        
        # Call the function with a regular file
        handle_log_selection(self.test_log_file, "test-model")
        
        # Verify analyze_log_file was called correctly
        # Should be with analyze=True and background=False for 'a' option
        mock_analyze.assert_called_once_with(self.test_log_file, "test-model", False, True)
        
        # Verify the input prompt about the action
        mock_input.assert_called_once()
        self.assertIn("Do you want to", str(mock_input.call_args[0][0]))
    
    @patch('qcmd_cli.log_analysis.log_files.analyze_log_file')
    @patch('builtins.input')
    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch('builtins.print')
    def test_handle_log_selection_monitor_option(self, mock_print, mock_isfile, 
                                             mock_exists, mock_input, mock_analyze):
        """Test handling a selected log file with monitoring option."""
        # Setup mocks
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_input.return_value = 'm'  # Monitor with analysis
        
        # Call the function with a regular file
        handle_log_selection(self.test_log_file, "test-model")
        
        # Verify analyze_log_file was called correctly
        # Should be with analyze=True and background=True for 'm' option
        mock_analyze.assert_called_once_with(self.test_log_file, "test-model", True, True)
    
    @patch('qcmd_cli.log_analysis.log_files.analyze_log_file')
    @patch('builtins.input')
    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch('builtins.print')
    def test_handle_log_selection_watch_option(self, mock_print, mock_isfile, 
                                           mock_exists, mock_input, mock_analyze):
        """Test handling a selected log file with watch-only option."""
        # Setup mocks
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_input.return_value = 'w'  # Watch without analysis
        
        # Call the function with a regular file
        handle_log_selection(self.test_log_file, "test-model")
        
        # Verify analyze_log_file was called correctly
        # Should be with analyze=False and background=True for 'w' option
        mock_analyze.assert_called_once_with(self.test_log_file, "test-model", True, False)
    
    @patch('qcmd_cli.log_analysis.log_files.subprocess.check_output')
    @patch('qcmd_cli.log_analysis.log_files.analyze_log_file')
    @patch('builtins.input')
    @patch('tempfile.NamedTemporaryFile')
    @patch('builtins.print')
    def test_handle_log_selection_journalctl(self, mock_print, mock_temp_file, 
                                          mock_input, mock_analyze, mock_check_output):
        """Test handling a journalctl log service."""
        # Setup mocks
        mock_input.return_value = 'a'  # Analyze once
        mock_check_output.return_value = "Test journalctl output\nLine 2\n"
        
        # Setup tempfile mock
        mock_file = MagicMock()
        mock_file.name = f"{self.temp_dir.name}/temp_journal.log"
        mock_file.__enter__.return_value = mock_file
        mock_temp_file.return_value = mock_file
        
        # Call the function with a journalctl service
        handle_log_selection("journalctl:test-service", "test-model")
        
        # Verify analyze_log_file was called with the temp file
        mock_analyze.assert_called_once_with(mock_file.name, "test-model", False, True)
        
        # Verify journalctl was called
        mock_check_output.assert_called_once()
        self.assertIn("journalctl", mock_check_output.call_args[0][0][0])
        
        # Check that the service name is included in one of the command arguments
        cmd_args = mock_check_output.call_args[0][0]
        service_in_args = False
        for arg in cmd_args:
            if "test-service" in str(arg):
                service_in_args = True
                break
        self.assertTrue(service_in_args, "Service name not found in journalctl arguments")
    
    @patch('qcmd_cli.log_analysis.log_files.subprocess.check_output')
    @patch('builtins.input')
    @patch('tempfile.NamedTemporaryFile')
    @patch('builtins.print')
    def test_handle_log_selection_journalctl_timeout(self, mock_print, mock_temp_file, 
                                                 mock_input, mock_check_output):
        """Test handling a journalctl timeout."""
        # Setup mocks
        mock_input.return_value = 'a'  # Analyze once
        mock_check_output.side_effect = subprocess.TimeoutExpired(cmd="journalctl", timeout=10)
        
        # Setup tempfile mock
        mock_file = MagicMock()
        mock_file.name = f"{self.temp_dir.name}/temp_journal.log"
        mock_file.__enter__.return_value = mock_file
        mock_temp_file.return_value = mock_file
        
        # Call the function with a journalctl service
        handle_log_selection("journalctl:test-service", "test-model")
        
        # Verify timeout error message
        timeout_msg = f"{Colors.RED}Error: journalctl command timed out.{Colors.END}"
        mock_print.assert_any_call(timeout_msg)


if __name__ == '__main__':
    unittest.main() 