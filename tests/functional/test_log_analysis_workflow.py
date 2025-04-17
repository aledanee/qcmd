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
        """Test the complete log analysis workflow."""
        # Setup mocks
        mock_find_logs.return_value = self.log_files
        mock_input.side_effect = ['2', 'a']  # Select file 2, choose analyze

    @patch('qcmd_cli.log_analysis.log_files.find_log_files')
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=StringIO)
    def test_workflow_with_invalid_selection(self, mock_stdout, mock_input, mock_find_logs):
        """Test invalid selection handling."""
        mock_find_logs.return_value = self.log_files
        mock_input.side_effect = ['5', '2', 'a']  # Invalid, then valid, then analyze
        
        handle_log_analysis(model="test-model", file_path=None)
        
        output = mock_stdout.getvalue()
        self.assertIn("Invalid selection '5'", output)
    
    @patch('qcmd_cli.log_analysis.log_files.analyze_log_file')
    @patch('builtins.input')
    def test_direct_file_analysis(self, mock_input, mock_analyze):
        """Test analyzing a file directly without selection."""
        # Set up input mock
        mock_input.return_value = 'a'  # Choose analyze option
        
        # Call handle_log_analysis with a specific file path
        handle_log_analysis(model="test-model", file_path=self.temp_log.name)
        
        # Verify analyze_log_file was called correctly
        mock_analyze.assert_called_once_with(
            self.temp_log.name,
            "test-model",
            background=False  # Change this line
        )

if __name__ == '__main__':
    unittest.main()