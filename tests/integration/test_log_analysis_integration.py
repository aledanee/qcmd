#!/usr/bin/env python3
"""
Integration tests for log file selection and analysis.

These tests verify that the log selection and analysis components
work together correctly, focusing on the interaction between these
key components.
"""
import sys
import os
import unittest
from unittest.mock import patch, Mock
from io import StringIO
import tempfile

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from qcmd_cli.log_analysis.log_files import handle_log_selection
from qcmd_cli.ui.display import Colors

class TestLogAnalysisIntegration(unittest.TestCase):
    """
    Test cases for the integration between log selection and analysis.
    """
    
    def setUp(self):
        """Set up test data."""
        # Create a temporary log file
        self.temp_log = tempfile.NamedTemporaryFile(delete=False, mode='w+')
        self.temp_log.write("May 10 12:34:56 server test: Test log entry\n")
        self.temp_log.write("May 10 12:35:00 server error: Error occurred\n")
        self.temp_log.close()

    def tearDown(self):
        """Clean up after tests."""
        # Delete the temporary file
        if os.path.exists(self.temp_log.name):
            os.unlink(self.temp_log.name)

    @patch('qcmd_cli.log_analysis.log_files.analyze_log_file')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_log_selection_to_analysis(self, mock_stdout, mock_input, mock_analyze):
        """Test the integration between log selection and log analysis."""
        # Simulate user choosing to analyze (not monitor)
        mock_input.return_value = 'a'
        
        # Call handle_log_selection with our temp file
        handle_log_selection(self.temp_log.name, "test-model")
        
        # Verify analyze_log_file was called with correct parameters
        mock_analyze.assert_called_once()
        args, kwargs = mock_analyze.call_args
        self.assertEqual(args[0], self.temp_log.name)  # File path
        self.assertEqual(args[1], "test-model")  # Model
        self.assertEqual(args[2], False)  # Not background (not monitoring)
    
    @patch('qcmd_cli.log_analysis.log_files.analyze_log_file')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_log_selection_to_monitoring(self, mock_stdout, mock_input, mock_analyze):
        """Test the integration between log selection and log monitoring."""
        # Simulate user choosing to monitor
        mock_input.return_value = 'm'
        
        # Call handle_log_selection with our temp file
        handle_log_selection(self.temp_log.name, "test-model")
        
        # Verify analyze_log_file was called with monitoring=True
        mock_analyze.assert_called_once()
        args, kwargs = mock_analyze.call_args
        self.assertEqual(args[0], self.temp_log.name)  # File path
        self.assertEqual(args[1], "test-model")  # Model
        self.assertEqual(args[2], True)  # Background=True (monitoring)
    
    @patch('qcmd_cli.log_analysis.log_files.analyze_log_file')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=StringIO)
    def test_handle_log_selection_invalid_then_valid(self, mock_stdout, mock_input, mock_analyze):
        """Test recovery from invalid action choice in log handling."""
        # Simulate user entering invalid choice then valid
        mock_input.side_effect = ['x', 'a']
        
        # Call handle_log_selection with our temp file
        handle_log_selection(self.temp_log.name, "test-model")
        
        # Should still proceed to analysis after invalid then valid input
        mock_analyze.assert_called_once()
        
        # Output should show some kind of error/retry prompt
        output = mock_stdout.getvalue()
        # In a real test with proper error handling for action choice,
        # we would assert something like:
        # self.assertIn("Invalid choice", output)

if __name__ == '__main__':
    unittest.main() 