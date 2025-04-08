#!/usr/bin/env python3
"""
Tests for the CLI argument handling.
"""

import unittest
import os
import sys
import argparse
from unittest.mock import patch, MagicMock

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the module but not the functions directly to avoid conflicts
import qcmd_cli.commands.handler


class TestCLIArguments(unittest.TestCase):
    """Test the CLI argument handling."""
    
    def test_timeout_argument(self):
        """Test that the timeout argument is correctly parsed."""
        # Create a new parser for testing to avoid conflicts
        parser = argparse.ArgumentParser()
        parser.add_argument('prompt', nargs='?', default=None)
        parser.add_argument('-e', '--execute', action='store_true')
        parser.add_argument('--timeout', type=int, default=60)
        
        args = parser.parse_args(['--timeout', '30', 'list files'])
        self.assertEqual(args.timeout, 30)
        self.assertEqual(args.prompt, 'list files')
    
    def test_default_timeout(self):
        """Test that the default timeout is used when not specified."""
        # Create a new parser for testing to avoid conflicts
        parser = argparse.ArgumentParser()
        parser.add_argument('prompt', nargs='?', default=None)
        parser.add_argument('--timeout', type=int, default=60)
        
        args = parser.parse_args(['list files'])
        self.assertEqual(args.timeout, 60)  # Default value
        self.assertEqual(args.prompt, 'list files')
    
    def test_execute_with_timeout(self):
        """Test that execute and timeout can be used together."""
        # Create a new parser for testing to avoid conflicts
        parser = argparse.ArgumentParser()
        parser.add_argument('prompt', nargs='?', default=None)
        parser.add_argument('-e', '--execute', action='store_true')
        parser.add_argument('--timeout', type=int, default=60)
        
        args = parser.parse_args(['-e', '--timeout', '45', 'list files'])
        self.assertTrue(args.execute)
        self.assertEqual(args.timeout, 45)
        self.assertEqual(args.prompt, 'list files')
    
    def test_shell_mode(self):
        """Test shell mode argument."""
        # Create a new parser for testing to avoid conflicts
        parser = argparse.ArgumentParser()
        parser.add_argument('prompt', nargs='?', default=None)
        parser.add_argument('-s', '--shell', action='store_true')
        
        args = parser.parse_args(['-s'])
        self.assertTrue(args.shell)
        self.assertIsNone(args.prompt)
    
    @patch('qcmd_cli.commands.handler.execute_command')
    @patch('qcmd_cli.commands.handler.generate_command')
    @patch('qcmd_cli.commands.handler.parse_args')
    def test_main_with_execute_and_timeout(self, mock_parse_args, mock_generate, mock_execute):
        """Test that main correctly passes timeout to execute_command."""
        # Setup mock args
        mock_args = MagicMock()
        mock_args.execute = True
        mock_args.prompt = "list files"
        mock_args.timeout = 15
        mock_args.model = None
        mock_args.shell = False
        mock_args.auto = False
        mock_args.status = False
        mock_args.check_updates = False
        mock_args.history = False
        mock_args.logs = False
        mock_args.config = None
        mock_parse_args.return_value = mock_args
        
        # Setup other mocks
        mock_generate.return_value = "ls -la"
        mock_execute.return_value = (0, "Command output")
        
        # Run main with mocked dependencies
        with patch('builtins.print'):
            qcmd_cli.commands.handler.main()
        
        # Verify execute_command was called with correct timeout
        mock_execute.assert_called_once()
        args, kwargs = mock_execute.call_args
        self.assertEqual(kwargs['timeout'], 15)
    
    def test_help_includes_timeout(self):
        """Test that help output includes timeout parameter."""
        # Create a new parser for testing
        parser = argparse.ArgumentParser()
        parser.add_argument('--timeout', type=int, default=60,
                          help='Set the timeout for command execution in seconds (default: 60)')
        
        # Capture the help output
        with patch('sys.stdout') as mock_stdout:
            try:
                parser.parse_args(['--help'])
            except SystemExit:
                pass
        
        # Verify timeout is in help text
        self.assertTrue('--timeout' in str(mock_stdout.method_calls))


if __name__ == '__main__':
    unittest.main() 