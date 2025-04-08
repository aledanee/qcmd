#!/usr/bin/env python3
"""
Additional tests for log analysis functionality to improve coverage.
"""
import unittest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock, mock_open

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test
from qcmd_cli.log_analysis.analyzer import analyze_log_file, analyze_log_content, read_large_file
from qcmd_cli.ui.display import Colors


class TestLogAnalyzerAdditional(unittest.TestCase):
    """Additional tests for the log analysis functions to improve coverage."""
    
    def setUp(self):
        """Set up temporary files for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_log_file = os.path.join(self.temp_dir.name, 'test.log')
        
        # Create a test log file
        with open(self.temp_log_file, 'w') as f:
            f.write("2023-01-01 12:00:00 ERROR: Failed to connect to database\n")
            f.write("2023-01-01 12:01:00 INFO: Retrying connection\n")
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    @patch('qcmd_cli.log_analysis.monitor.monitor_log')
    @patch('builtins.print')
    def test_analyze_log_file_background_mode(self, mock_print, patched_monitor_log):
        """Test analyzing a log file in background mode."""
        # Call the function with background=True
        analyze_log_file(self.temp_log_file, model='test-model', background=True, analyze=True)
        
        # Verify monitor_log was called
        patched_monitor_log.assert_called_once_with(
            log_file=self.temp_log_file, 
            background=True, 
            analyze=True, 
            model='test-model'
        )
    
    @patch('builtins.open')
    @patch('builtins.print')
    @patch('os.path.exists', return_value=True)
    @patch('os.path.getsize', return_value=15 * 1024 * 1024)  # 15 MB
    @patch('builtins.input', return_value='')  # Default 'y' response
    def test_analyze_log_file_unicode_error(self, mock_input, mock_getsize, mock_exists, mock_print, mock_open):
        """Test analyzing a log file with a Unicode decode error."""
        # First open raises a UnicodeDecodeError
        mock_open.side_effect = [
            UnicodeDecodeError('utf-8', b'', 0, 1, 'Test error'),
            MagicMock().__enter__.return_value  # Second open succeeds
        ]
        
        # Create a mock file handle that returns a read value
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "Log content"
        mock_file.__enter__.return_value.seek = MagicMock()  # Mock seek method
        mock_file.__enter__.return_value.readline = MagicMock()  # Mock readline method
        
        # Set up the mock_open to return our mock file
        mock_open.return_value = mock_file
        
        # Call the function
        with patch('qcmd_cli.log_analysis.analyzer.analyze_log_content') as mock_analyze:
            analyze_log_file(self.temp_log_file, model='test-model')
            
            # Verify analyze_log_content was called
            mock_analyze.assert_called_once()
    
    @patch('builtins.open')
    @patch('builtins.print')
    @patch('os.path.exists', return_value=True)
    @patch('os.path.getsize', return_value=15 * 1024 * 1024)  # 15 MB
    @patch('builtins.input', return_value='')  # Default 'y' response
    def test_analyze_log_file_double_unicode_error(self, mock_input, mock_getsize, mock_exists, mock_print, mock_open):
        """Test analyzing a log file with Unicode decode errors in both encodings."""
        # Both open attempts raise UnicodeDecodeError
        mock_open.side_effect = [
            UnicodeDecodeError('utf-8', b'', 0, 1, 'UTF-8 error'),
            UnicodeDecodeError('latin-1', b'', 0, 1, 'Latin-1 error')
        ]
        
        # Call the function
        analyze_log_file(self.temp_log_file, model='test-model')
        
        # Verify an error message was printed - just check for part of the message
        # since the exact format might vary
        error_printed = False
        for call_args in mock_print.call_args_list:
            args, kwargs = call_args
            if args and f"{Colors.RED}Error reading log file:" in str(args[0]):
                error_printed = True
                break
        self.assertTrue(error_printed, "Error message was not printed")
    
    @patch('builtins.open')
    @patch('builtins.print')
    @patch('os.path.exists', return_value=True)
    @patch('os.path.getsize', return_value=5 * 1024)  # 5 KB (small file)
    def test_analyze_log_file_general_error(self, mock_getsize, mock_exists, mock_print, mock_open):
        """Test analyzing a log file with a general exception."""
        # open raises a general exception
        mock_open.side_effect = Exception("General error")
        
        # Call the function
        analyze_log_file(self.temp_log_file, model='test-model')
        
        # Verify error message was printed
        mock_print.assert_any_call(f"{Colors.RED}Error reading log file: General error{Colors.END}")
    
    @patch('builtins.print')
    def test_analyze_log_content_no_truncation(self, mock_print):
        """Test analyzing log content that doesn't need truncation."""
        # Create a small log content (less than 1000 lines)
        small_content = "\n".join([f"Line {i}" for i in range(10)])
        
        # Call the function
        with patch('qcmd_cli.log_analysis.analyzer.generate_command') as mock_generate:
            mock_generate.return_value = "Analysis for small content"
            analyze_log_content(small_content, self.temp_log_file, model='test-model')
        
        # Verify we don't see a message about truncating the content
        truncation_message = f"{Colors.YELLOW}Log content is large. Analyzing only the last 1000 lines.{Colors.END}"
        for call_args in mock_print.call_args_list:
            args, kwargs = call_args
            if args and truncation_message in str(args[0]):
                self.fail(f"Unexpected truncation message for small content: {truncation_message}")
    
    @patch('os.path.getsize')
    @patch('os.path.exists', return_value=True)
    def test_read_large_file_multiple_chunks(self, mock_exists, mock_getsize):
        """Test reading a large file with multiple chunks."""
        # Set up a file size that requires multiple chunks
        mock_getsize.return_value = 3 * 1024 * 1024  # 3 MB
        
        # Create a mock open function that returns our mock file
        mock_file = mock_open(read_data="Test data" * 1000)
        
        # Patch the open function
        with patch('builtins.open', mock_file):
            # Call the function with a small chunk size to force multiple chunks
            content = read_large_file(self.temp_log_file, chunk_size=1 * 1024 * 1024)  # 1 MB chunks
            
            # Verify we got the expected content
            self.assertIn("Test data", content)
    
    @patch('os.path.getsize')
    @patch('os.path.exists', return_value=True)
    def test_read_large_file_unicode_fallback(self, mock_exists, mock_getsize):
        """Test reading a large file with Unicode error in first attempt but success in fallback."""
        # Set up a file size
        mock_getsize.return_value = 2 * 1024  # 2 KB
        
        # First open raises UnicodeDecodeError, second one succeeds
        with patch('builtins.open', side_effect=[
            UnicodeDecodeError('utf-8', b'', 0, 1, 'UTF-8 error'),
            mock_open(read_data="Latin-1 content").return_value
        ]):
            content = read_large_file(self.temp_log_file)
            
            # Verify we got the fallback content
            self.assertEqual(content, "Latin-1 content")
    
    @patch('os.path.getsize')
    @patch('os.path.exists', return_value=True)
    @patch('builtins.print')
    def test_read_large_file_all_encoding_errors(self, mock_print, mock_exists, mock_getsize):
        """Test reading a file where all encodings fail."""
        # Set up a file size
        mock_getsize.return_value = 2 * 1024  # 2 KB
        
        # Both utf-8 and latin-1 attempts fail
        with patch('builtins.open', side_effect=[
            UnicodeDecodeError('utf-8', b'', 0, 1, 'UTF-8 error'),
            UnicodeDecodeError('latin-1', b'', 0, 1, 'Latin-1 error')
        ]):
            # Should raise the second exception
            with self.assertRaises(UnicodeDecodeError):
                read_large_file(self.temp_log_file)
            
            # Verify some error message was printed
            error_printed = False
            for call_args in mock_print.call_args_list:
                args, kwargs = call_args
                if args and f"{Colors.RED}Error reading file:" in str(args[0]):
                    error_printed = True
                    break
            self.assertTrue(error_printed, "Error message was not printed")
    
    @patch('os.path.getsize')
    @patch('os.path.exists', return_value=True)
    @patch('builtins.print')
    def test_read_large_file_general_exception(self, mock_print, mock_exists, mock_getsize):
        """Test reading a large file with a general exception."""
        # Set up a file size for a large file
        mock_getsize.return_value = 2 * 1024 * 1024  # 2 MB
        
        # First open call - UTF-8 attempt raises a UnicodeDecodeError
        # Second open call - Latin-1 attempt raises a general exception
        mock_open_calls = [
            UnicodeDecodeError('utf-8', b'', 0, 1, 'UTF-8 error'),
            Exception("General latin-1 error")
        ]
        
        # Simulate a Unicode decode error followed by a general exception
        with patch('builtins.open', side_effect=mock_open_calls):
            # Should raise the exception
            with self.assertRaises(Exception):
                read_large_file(self.temp_log_file)
            
            # Verify error message was printed - check for part of the message
            # since the exact format might vary
            error_printed = False
            for call_args in mock_print.call_args_list:
                args, kwargs = call_args
                if args and "Error reading file: General latin-1 error" in str(args[0]):
                    error_printed = True
                    break
            self.assertTrue(error_printed, "Error message was not printed")
    
    @patch('qcmd_cli.log_analysis.analyzer.analyze_log_content')
    @patch('qcmd_cli.log_analysis.analyzer.read_large_file')
    @patch('os.path.exists', return_value=True)
    def test_analyze_log_file_non_background_return(self, mock_exists, mock_read_file, mock_analyze_content):
        """Test the early return path in analyze_log_file when background=False."""
        # Get the actual content from the file created in setUp
        with open(self.temp_log_file, 'r') as f:
            actual_content = f.read()
        
        # Set up mock return value for read_large_file to use the actual content
        mock_read_file.return_value = actual_content
        
        # Call analyze_log_file with background=False
        result = analyze_log_file(self.temp_log_file, model='test-model', background=False)
        
        # Verify analyze_log_content was called
        self.assertTrue(mock_analyze_content.called, "analyze_log_content should have been called")
        
        # Get the call arguments
        call_args = mock_analyze_content.call_args
        args, kwargs = call_args
        
        # Check that the file path and model were correct
        self.assertEqual(kwargs.get('log_file'), self.temp_log_file)
        self.assertEqual(kwargs.get('model'), 'test-model')
        
        # Compare log content ignoring trailing newlines
        passed_content = kwargs.get('log_content', '').rstrip('\n')
        expected_content = actual_content.rstrip('\n')
        self.assertEqual(passed_content, expected_content)
        
        # Verify the function returns None (implicitly)
        self.assertIsNone(result)
        
        # Verify monitor_log was NOT imported or called
        # This is implicit as we're not patching it and the test would fail if it were called


if __name__ == '__main__':
    unittest.main() 