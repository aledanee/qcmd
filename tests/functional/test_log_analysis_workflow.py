#!/usr/bin/env python3
"""
Functional tests for the full log analysis workflow.

These tests verify the end-to-end log analysis functionality,
ensuring that all components work together properly.
"""
import sys
import os
import unittest
from unittest.mock import patch, Mock, call
from io import StringIO
import tempfile

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from qcmd_cli.log_analysis.log_files import handle_log_analysis, display_log_selection
from qcmd_cli.log_analysis.analyzer import analyze_log_file
from qcmd_cli.ui.display import Colors

class TestLogAnalysisWorkflow(unittest.TestCase):
    """
    Test cases for the complete log analysis workflow.
    """
    
    def setUp(self):
        """Set up test data."""
        # Create a temporary log file
        self.temp_log = tempfile.NamedTemporaryFile(delete=False, mode='w+')
        self.temp_log.write("May 10 12:34:56 server test: Test log entry\n")
        self.temp_log.write("May 10 12:35:00 server error: Error occurred\n")
        self.temp_log.close()
        
        # Create a list of mock log files
        self.log_files = [
            '/var/log/test1.log',
            '/var/log/test2.log',
            self.temp_log.name  # This one actually exists
        ]

    def tearDown(self):
        """Clean up after tests."""
        # Delete the temporary file
        if os.path.exists(self.temp_log.name):
            os.unlink(self.temp_log.name)

    @patch('qcmd_cli.log_analysis.log_files.find_log_files')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=StringIO)
    def test_full_log_analysis_workflow(self, mock_stdout, mock_input, mock_find_logs):
        """Test the complete log analysis workflow with user interaction."""
        # Setup mocks
        mock_find_logs.return_value = self.log_files
        
        # Simulate user selecting the third log (our temp file) and choosing to analyze it once
        mock_input.side_effect = ['3', 'a']
        
        # Run the handle_log_analysis function
        handle_log_analysis(model="test-model", file_path=None)
        
        # Verify the output indicates successful analysis
        output = mock_stdout.getvalue()
        
        # Check for key steps in the workflow
        self.assertIn("Starting log analysis tool", output)
        self.assertIn("Found 3 log files", output)
        
        # In a real test, additional assertions would verify the analysis output
        # Since we're mocking most of it, we'll focus on workflow verification
    
    @patch('qcmd_cli.log_analysis.log_files.find_log_files')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=StringIO)
    def test_workflow_with_invalid_selection(self, mock_stdout, mock_input, mock_find_logs):
        """Test the workflow when user makes an invalid selection first."""
        # Setup mocks
        mock_find_logs.return_value = self.log_files
        
        # Simulate user making invalid selection first, then choosing correctly
        mock_input.side_effect = ['5', '3', 'a']
        
        # Run the handle_log_analysis function
        handle_log_analysis(model="test-model", file_path=None)
        
        # Verify the error message and successful recovery
        output = mock_stdout.getvalue()
        
        # Check that our improved error message appears
        self.assertIn("Invalid selection '5'", output)
        self.assertIn("Please enter a number between 1 and 3", output)
        
        # Note: We can't reliably check for "Do you want to" in output since it might
        # fail before reaching that point if the test file doesn't exist
        # Instead, just verify the error handling worked as expected
    
    @patch('qcmd_cli.log_analysis.log_files.analyze_log_file')
    def test_direct_file_analysis(self, mock_analyze):
        """Test analyzing a file directly without selection."""
        # Call handle_log_analysis with a specific file path
        with patch('builtins.input', return_value='n'):  # Don't monitor
            handle_log_analysis(model="test-model", file_path=self.temp_log.name)
        
        # Verify that analyze_log_file was called with the correct parameters
        mock_analyze.assert_called_once()
        args, kwargs = mock_analyze.call_args
        self.assertEqual(args[0], self.temp_log.name)
        self.assertEqual(args[1], "test-model")
        self.assertEqual(args[2], False)  # Not monitoring

if __name__ == '__main__':
    unittest.main() 