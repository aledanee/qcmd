#!/usr/bin/env python3
"""
Tests for log file selection functionality to verify the fix for issue #9.

These tests ensure that:
1. The log selection function accepts valid inputs
2. The function properly handles invalid selections by showing a clear error and allowing retry
3. The function allows the user to quit
"""
import sys
import os
import unittest
from unittest.mock import patch, Mock
from io import StringIO

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from qcmd_cli.log_analysis.log_files import display_log_selection
from qcmd_cli.ui.display import Colors

class TestLogSelection(unittest.TestCase):
    """Test cases for log selection functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Common test data for all tests
        self.log_files = [
            '/var/log/test1.log', 
            '/var/log/test2.log', 
            '/var/log/test3.log'
        ]

    @patch('builtins.input')
    @patch('sys.stdout', new_callable=StringIO)
    def test_valid_selection(self, mock_stdout, mock_input):
        """Test valid log file selection."""
        # Setup mock input
        mock_input.return_value = '2'  # Select the second log file
        
        # Call the function
        result = display_log_selection(self.log_files)
        
        # Check that we got the correct log file
        self.assertEqual(result, '/var/log/test2.log')
        
        # Check that appropriate text was displayed
        output = mock_stdout.getvalue()
        self.assertIn("Found 3 log files", output)
        self.assertIn("2. test2.log", output)

    @patch('builtins.input')
    @patch('sys.stdout', new_callable=StringIO)
    def test_invalid_then_valid_selection(self, mock_stdout, mock_input):
        """Test invalid selection followed by valid selection."""
        # First provide invalid input, then valid input
        mock_input.side_effect = ['5', '2']
        
        # Call the function
        result = display_log_selection(self.log_files)
        
        # Check that we eventually got the correct file
        self.assertEqual(result, '/var/log/test2.log')
        
        # Check that the improved error message was shown with useful information
        output = mock_stdout.getvalue()
        self.assertIn("Invalid selection '5'", output, "Enhanced error message missing")
        self.assertIn("Please enter a number between 1 and 3", output, "Valid range missing from error message")

    @patch('builtins.input')
    @patch('sys.stdout', new_callable=StringIO)
    def test_non_numeric_then_valid_selection(self, mock_stdout, mock_input):
        """Test non-numeric input followed by valid selection."""
        # First provide non-numeric input, then valid input
        mock_input.side_effect = ['abc', '1']
        
        # Call the function
        result = display_log_selection(self.log_files)
        
        # Check that we eventually got the correct file
        self.assertEqual(result, '/var/log/test1.log')
        
        # Check that the error message was shown
        output = mock_stdout.getvalue()
        self.assertIn("Please enter a number or 'q' to cancel", output)

    @patch('builtins.input')
    @patch('sys.stdout', new_callable=StringIO)
    def test_quit_selection(self, mock_stdout, mock_input):
        """Test quitting the selection."""
        mock_input.return_value = 'q'
        
        # Call the function
        result = display_log_selection(self.log_files)
        
        # Check that we got None when quitting
        self.assertIsNone(result)
        
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=StringIO)
    def test_multiple_retries_then_valid(self, mock_stdout, mock_input):
        """Test multiple invalid selections followed by a valid one."""
        # Multiple invalid inputs followed by valid
        mock_input.side_effect = ['10', 'xyz', '0', '-1', '2']
        
        # Call the function
        result = display_log_selection(self.log_files)
        
        # Should eventually succeed with the valid input
        self.assertEqual(result, '/var/log/test2.log')
        
        # Error messages should have been displayed multiple times
        output = mock_stdout.getvalue()
        self.assertIn("Invalid selection '10'", output)
        self.assertIn("Please enter a number or 'q' to cancel", output)
        self.assertIn("Invalid selection '0'", output)
        self.assertIn("Invalid selection '-1'", output)

if __name__ == '__main__':
    unittest.main() 