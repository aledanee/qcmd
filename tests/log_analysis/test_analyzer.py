#!/usr/bin/env python3
"""
Tests for log analysis functionality.
"""
import unittest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock
import re

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test
from qcmd_cli.log_analysis.analyzer import analyze_log_file, analyze_log_content, read_large_file
from qcmd_cli.ui.display import Colors


class TestLogAnalyzer(unittest.TestCase):
    """Test the log analysis functions."""
    
    def setUp(self):
        """Set up temporary files for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_log_file = os.path.join(self.temp_dir.name, 'test.log')
        
        # Create a test log file
        with open(self.temp_log_file, 'w') as f:
            f.write("2023-01-01 12:00:00 ERROR: Failed to connect to database\n")
            f.write("2023-01-01 12:01:00 INFO: Retrying connection\n")
            f.write("2023-01-01 12:02:00 ERROR: Connection timed out\n")
            f.write("2023-01-01 12:03:00 WARNING: Using fallback connection\n")
            f.write("2023-01-01 12:04:00 INFO: Connected successfully\n")
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    @patch('qcmd_cli.log_analysis.analyzer.analyze_log_content')
    @patch('builtins.print')
    @patch('builtins.input', return_value='n')  # Simulate user answering 'n' to analyze only last portion
    def test_analyze_log_file(self, mock_input, mock_print, mock_analyze_content):
        """Test analyzing a log file once."""
        # Call the function
        analyze_log_file(self.temp_log_file, model='test-model', background=False, analyze=True)
        
        # Verify analyze_log_content was called
        mock_analyze_content.assert_called_once()
        
        # Verify the file path was included in the call
        args, kwargs = mock_analyze_content.call_args
        self.assertEqual(kwargs.get('log_file'), self.temp_log_file)
        self.assertEqual(kwargs.get('model'), 'test-model')
    
    @patch('qcmd_cli.log_analysis.analyzer.analyze_log_content')
    @patch('builtins.print')
    @patch('builtins.input', return_value='y')  # Simulate user answering 'y' to analyze only last portion
    def test_analyze_log_file_large_last_portion(self, mock_input, mock_print, mock_analyze_content):
        """Test analyzing only the last portion of a large log file."""
        # Create a large temporary log file (11 MB to trigger the size check)
        large_log_file = os.path.join(self.temp_dir.name, 'large.log')
        with open(large_log_file, 'w') as f:
            # Write some content (we'll mock the size check)
            f.write('X' * 1024 + '\n')
        
        # Call the function
        with patch('os.path.getsize', return_value=11 * 1024 * 1024):
            analyze_log_file(large_log_file, model='test-model', background=False, analyze=True)
        
        # Verify analyze_log_content was called
        mock_analyze_content.assert_called_once()
        
        # Check that we printed a warning about the file size
        mock_print.assert_any_call(f"{Colors.YELLOW}Analyzing only the last 1 MB of the log file.{Colors.END}")
    
    @patch('builtins.print')
    def test_analyze_log_file_nonexistent(self, mock_print):
        """Test analyzing a nonexistent log file."""
        # Call the function with a nonexistent file
        non_existent_file = os.path.join(self.temp_dir.name, 'nonexistent.log')
        analyze_log_file(non_existent_file, model='test-model', background=False, analyze=True)
        
        # Verify error message was printed
        mock_print.assert_any_call(f"{Colors.RED}Error: Log file {non_existent_file} does not exist.{Colors.END}")
    
    @patch('builtins.print')
    def test_analyze_log_content(self, mock_print):
        """Test analyzing log content."""
        log_content = """
        2023-01-01 12:00:00 ERROR: Failed to connect to database
        2023-01-01 12:01:00 INFO: Retrying connection
        2023-01-01 12:02:00 ERROR: Connection timed out
        """
        
        analysis_result = "The log shows database connection issues."
        
        # Call the function with properly mocked generate_command
        with patch('qcmd_cli.log_analysis.analyzer.generate_command') as mock_generate:
            mock_generate.return_value = analysis_result
            analyze_log_content(log_content, self.temp_log_file, model='test-model')
        
        # Just verify that print was called at all - the output might include formatting
        self.assertTrue(mock_print.called)
        
        # If needed, check specific argument patterns
        called_with_analysis = False
        for call_args in mock_print.call_args_list:
            args, kwargs = call_args
            if args and analysis_result in str(args[0]):
                called_with_analysis = True
                break
        
        self.assertTrue(called_with_analysis, f"Print was never called with '{analysis_result}'")
    
    @patch('builtins.print')
    def test_analyze_log_content_large(self, mock_print):
        """Test analyzing large log content that gets truncated to last 1000 lines."""
        # Create a log with 1100 lines
        large_content = "\n".join([f"Line {i}" for i in range(1100)])
    
        # Mock the generate_command function
        with patch('qcmd_cli.log_analysis.analyzer.generate_command') as mock_generate:
            # Set up the mock to return a specific analysis
            analysis_result = "Analysis of the last 1000 lines shows..."
            mock_generate.return_value = analysis_result
    
            # Call the function
            analyze_log_content(large_content, self.temp_log_file, model='test-model')
    
            # Get all print calls
            print_calls = [args[0] for args, _ in mock_print.call_args_list]
    
            # Verify we see a message about truncating the content
            truncate_msg = f"{Colors.YELLOW}Log content is large. Analyzing only the last 1000 lines.{Colors.END}"
            self.assertIn(truncate_msg, print_calls)
    
            # Verify generate_command was called with the correct arguments
            mock_generate.assert_called_once()
            args, kwargs = mock_generate.call_args
    
            # Check that the prompt contains the expected format
            prompt = args[0]
            self.assertIn(f"Please analyze this log from {self.temp_log_file}:", prompt)
            
            # Extract the log content from between the code block markers
            log_content_match = re.search(r'```\n(.*?)\n```', prompt, re.DOTALL)
            self.assertIsNotNone(log_content_match, "Could not find log content between code block markers")
            log_content = log_content_match.group(1)
            
            # Split the log content into lines and verify we have exactly 1000 lines
            log_lines = log_content.strip().split('\n')
            self.assertEqual(len(log_lines), 1000, "Expected exactly 1000 lines in truncated content")
            
            # Verify the first and last lines are correct
            self.assertEqual(log_lines[0], "Line 100", "First line should be Line 100")
            self.assertEqual(log_lines[-1], "Line 1099", "Last line should be Line 1099")
            
            # Verify the model parameter was passed correctly
            self.assertEqual(kwargs.get('model'), 'test-model')
            
            # Verify the analysis was printed
            self.assertIn(analysis_result, print_calls)
    
    def test_read_large_file(self):
        """Test reading a large file in chunks."""
        # Create a temporary large file
        large_file = os.path.join(self.temp_dir.name, 'large.log')
        with open(large_file, 'w') as f:
            f.write('x' * 1000 + '\n')  # 1001 bytes
            f.write('y' * 1000 + '\n')  # 1001 bytes
            f.write('z' * 1000 + '\n')  # 1001 bytes
        
        # Patch the input and file size checks to make it behave deterministically
        with patch('os.path.getsize', return_value=1024):  # Small enough for single chunk
            content = read_large_file(large_file)
            
            # Verify the content
            self.assertEqual(len(content), 3003)  # 3 lines of 1001 bytes each
            self.assertTrue(content.startswith('x' * 1000))
            self.assertTrue('y' * 1000 in content)
            self.assertTrue(content.endswith('z' * 1000 + '\n'))
    
    def test_read_large_file_small(self):
        """Test reading a small file in a single chunk."""
        with patch('os.path.getsize', return_value=1024):  # Small file
            content = read_large_file(self.temp_log_file)
            
            # Verify the content
            self.assertIn("ERROR: Failed to connect to database", content)
            self.assertIn("INFO: Connected successfully", content)
    
    @patch('os.path.exists', return_value=False)
    @patch('builtins.print')
    def test_read_large_file_nonexistent(self, mock_print, mock_exists):
        """Test reading a nonexistent file."""
        non_existent_file = os.path.join(self.temp_dir.name, 'nonexistent.log')
        
        # Set up the error
        with patch('builtins.open', side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError):
                read_large_file(non_existent_file)
    
    @patch('builtins.open', side_effect=UnicodeDecodeError('utf-8', b'', 0, 1, 'Test error'))
    @patch('builtins.print')
    def test_read_large_file_unicode_error(self, mock_print, mock_open):
        """Test handling unicode decode errors when reading files."""
        # We'll patch a secondary open to still fail
        with patch('builtins.open', side_effect=UnicodeDecodeError('utf-8', b'', 0, 1, 'Test error')):
            # This should now raise an exception
            with self.assertRaises(Exception):
                read_large_file(self.temp_log_file)


if __name__ == '__main__':
    unittest.main() 