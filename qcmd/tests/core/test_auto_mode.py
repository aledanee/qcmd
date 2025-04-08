#!/usr/bin/env python3
"""
Tests for auto_mode functionality in interactive shell.
"""
import unittest
import os
import sys
import time
from unittest.mock import patch, MagicMock, call

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import function to test
from qcmd_cli.core.interactive_shell import auto_mode
from qcmd_cli.ui.display import Colors


class TestAutoMode(unittest.TestCase):
    """Test the auto mode functionality."""

    @patch('qcmd_cli.core.interactive_shell.generate_command')
    @patch('qcmd_cli.core.interactive_shell.execute_command')
    @patch('builtins.print')
    def test_auto_mode_success_first_attempt(self, mock_print, mock_execute, mock_generate):
        """Test auto mode with a successful command on the first try."""
        # Setup mocks
        mock_generate.return_value = "ls -la"
        mock_execute.return_value = (0, "file1.txt\nfile2.txt")  # Successful execution
        
        # Call the function
        auto_mode("list files", "test-model", 3, 0.7)
        
        # Verify the right functions were called
        mock_generate.assert_called_once_with("list files", "test-model", 0.7)
        mock_execute.assert_called_once_with("ls -la")
        
        # Verify appropriate messages were printed
        # Check for auto-correction mode message
        auto_mode_msg = f"{Colors.CYAN}Generating command in auto-correction mode...{Colors.END}"
        mock_print.assert_any_call(auto_mode_msg)
        
        # Check success message
        success_msg = f"\n{Colors.GREEN}Command executed successfully.{Colors.END}"
        mock_print.assert_any_call(success_msg)

    @patch('qcmd_cli.core.interactive_shell.generate_command')
    @patch('qcmd_cli.core.interactive_shell.execute_command')
    @patch('qcmd_cli.core.interactive_shell.fix_command')
    @patch('qcmd_cli.core.interactive_shell.time.sleep')  # Mock sleep to avoid delays
    @patch('builtins.print')
    def test_auto_mode_retry_then_success(self, mock_print, mock_sleep, mock_fix, mock_execute, mock_generate):
        """Test auto mode with a failed first attempt but successful retry."""
        # Setup mocks
        mock_generate.return_value = "invalid command"
        mock_execute.side_effect = [
            (1, "Command not found: invalid"),  # First execution fails
            (0, "file1.txt\nfile2.txt")         # Second execution succeeds
        ]
        mock_fix.return_value = "ls -la"  # Fixed command
        
        # Call the function
        auto_mode("list files", "test-model", 3, 0.7)
        
        # Verify the right functions were called
        mock_generate.assert_called_once_with("list files", "test-model", 0.7)
        self.assertEqual(mock_execute.call_count, 2)
        mock_fix.assert_called_once_with("invalid command", "Command not found: invalid", "test-model")
        
        # Verify appropriate messages were printed
        # Check for attempt message
        attempt_msg = f"\n{Colors.CYAN}Attempt 2/3:{Colors.END}"
        mock_print.assert_any_call(attempt_msg)
        
        # Check for fix message
        fix_msg = f"\n{Colors.CYAN}Attempting to fix the command...{Colors.END}"
        mock_print.assert_any_call(fix_msg)
        
        # Check success message
        success_msg = f"\n{Colors.GREEN}Command executed successfully.{Colors.END}"
        mock_print.assert_any_call(success_msg)

    @patch('qcmd_cli.core.interactive_shell.generate_command')
    @patch('qcmd_cli.core.interactive_shell.execute_command')
    @patch('qcmd_cli.core.interactive_shell.fix_command')
    @patch('qcmd_cli.core.interactive_shell.time.sleep')  # Mock sleep to avoid delays
    @patch('builtins.print')
    def test_auto_mode_max_attempts_reached(self, mock_print, mock_sleep, mock_fix, mock_execute, mock_generate):
        """Test auto mode with all attempts failing."""
        # Setup mocks
        mock_generate.return_value = "invalid command"
        # All executions fail
        mock_execute.return_value = (1, "Command not found")
        # Fix attempts also lead to invalid commands
        mock_fix.return_value = "still invalid"
        
        # Call the function with max 2 attempts
        auto_mode("list files", "test-model", 2, 0.7)
        
        # Verify the right functions were called
        mock_generate.assert_called_once_with("list files", "test-model", 0.7)
        self.assertEqual(mock_execute.call_count, 2)  # Should try exactly 2 times
        self.assertEqual(mock_fix.call_count, 1)  # Should fix only once (for the second attempt)
        
        # Verify max attempts message was printed
        max_attempts_msg = f"\n{Colors.YELLOW}Maximum correction attempts reached. Giving up.{Colors.END}"
        mock_print.assert_any_call(max_attempts_msg)

    @patch('qcmd_cli.core.interactive_shell.generate_command')
    @patch('builtins.print')
    def test_auto_mode_generation_failure(self, mock_print, mock_generate):
        """Test auto mode when command generation fails."""
        # Setup mock to return an empty string (generation failure)
        mock_generate.return_value = ""
        
        # Call the function
        auto_mode("list files", "test-model", 3, 0.7)
        
        # Verify the generate function was called but no execution happened
        mock_generate.assert_called_once_with("list files", "test-model", 0.7)
        
        # Verify error message was printed
        failure_msg = f"{Colors.RED}Failed to generate a command.{Colors.END}"
        mock_print.assert_any_call(failure_msg)

    # Test removed as the auto_mode function doesn't handle markdown cleanup directly
    # The markdown cleanup is done in the generate_command and fix_command functions


if __name__ == "__main__":
    unittest.main() 