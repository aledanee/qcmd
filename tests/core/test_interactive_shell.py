#!/usr/bin/env python3
"""
Tests for interactive shell functionality.
"""
import unittest
import os
import sys
import readline
from unittest.mock import patch, MagicMock, call

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test
from qcmd_cli.core.interactive_shell import (
    start_interactive_shell, SimpleCompleter, auto_mode
)


class TestSimpleCompleter(unittest.TestCase):
    """Test the SimpleCompleter class."""
    
    def test_complete(self):
        """Test the complete method."""
        options = ['help', 'exit', 'quit', 'history']
        completer = SimpleCompleter(options)
        
        # Test completing when text matches a command
        self.assertEqual(completer.complete('he', 0), 'help')
        self.assertEqual(completer.complete('he', 1), None)  # No more matches
        
        # Test completing when text matches multiple commands
        self.assertEqual(completer.complete('h', 0), 'help')
        self.assertEqual(completer.complete('h', 1), 'history')
        self.assertEqual(completer.complete('h', 2), None)  # No more matches
        
        # Test completing with empty string (should return all options in order)
        self.assertEqual(completer.complete('', 0), 'help')
        self.assertEqual(completer.complete('', 1), 'exit')
        self.assertEqual(completer.complete('', 2), 'quit')
        self.assertEqual(completer.complete('', 3), 'history')
        self.assertEqual(completer.complete('', 4), None)  # No more matches
        
        # Test completing with no matches
        self.assertEqual(completer.complete('xyz', 0), None)


class TestInteractiveShell(unittest.TestCase):
    """Test the interactive shell functions."""
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('qcmd_cli.core.interactive_shell.generate_command')
    @patch('qcmd_cli.core.interactive_shell.execute_command')
    def test_shell_command_generation(self, mock_execute, mock_generate, mock_parse_bind, 
                                     mock_set_completer, mock_print, mock_input):
        """Test command generation in the shell."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            'list files',  # First command
            'y',           # Confirm execution
            '!exit'        # Exit command
        ]
        
        # Mock generate_command to return a test command
        mock_generate.return_value = 'ls -la'
        
        # Mock execute_command to return success
        mock_execute.return_value = (0, 'file1.txt\nfile2.txt')
        
        # Call the function
        start_interactive_shell(
            auto_mode_enabled=False,
            current_model='test-model',
            current_temperature=0.7,
            max_attempts=3
        )
        
        # Verify generate_command was called with correct parameters
        mock_generate.assert_called_once_with('list files', 'test-model', 0.7)
        
        # Verify execute_command was called with the generated command
        mock_execute.assert_called_once_with('ls -la')
        
        # Verify output was printed - using a more flexible check that looks for the success message
        # in any of the print calls
        success_message_found = False
        for call_args in mock_print.call_args_list:
            if len(call_args[0]) > 0 and "Command executed successfully" in str(call_args[0][0]):
                success_message_found = True
                break
        
        self.assertTrue(success_message_found, "Success message was not printed")
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('qcmd_cli.core.interactive_shell.display_help_command')
    def test_shell_help_command(self, mock_help, mock_parse_bind, 
                              mock_set_completer, mock_print, mock_input):
        """Test help command in the shell."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            '!help',  # Help command
            '!exit'   # Exit command
        ]
        
        # Call the function
        start_interactive_shell(
            auto_mode_enabled=False,
            current_model='test-model',
            current_temperature=0.7,
            max_attempts=3
        )
        
        # Verify help was displayed
        mock_help.assert_called_once_with('test-model', 0.7, False, 3)
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('qcmd_cli.core.interactive_shell.generate_command')
    @patch('qcmd_cli.core.interactive_shell.execute_command')
    def test_shell_edit_command(self, mock_execute, mock_generate, mock_parse_bind, 
                               mock_set_completer, mock_print, mock_input):
        """Test editing a command in the shell."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            'list files',     # First command
            'e',              # Edit command
            'ls -la | grep .txt',  # Edited command
            '!exit'           # Exit command
        ]
        
        # Mock generate_command to return a test command
        mock_generate.return_value = 'ls -la'
        
        # Mock execute_command to return success
        mock_execute.return_value = (0, 'file1.txt')
        
        # Call the function
        start_interactive_shell(
            auto_mode_enabled=False,
            current_model='test-model',
            current_temperature=0.7,
            max_attempts=3
        )
        
        # Verify execute_command was called with the edited command
        mock_execute.assert_called_once_with('ls -la | grep .txt')


if __name__ == '__main__':
    unittest.main() 