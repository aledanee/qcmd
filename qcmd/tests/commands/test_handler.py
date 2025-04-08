#!/usr/bin/env python3
"""
Tests for the command handler functionality.
"""
import unittest
import os
import sys
import argparse
import tempfile
from unittest.mock import patch, MagicMock

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test - but DO NOT import parser directly to avoid conflicts
from qcmd_cli.commands.handler import parse_args, main


class TestCommandHandler(unittest.TestCase):
    """Test the command handler functions."""
    
    def setUp(self):
        """Set up temporary files for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = os.path.join(self.temp_dir.name, '.qcmd')
        os.makedirs(self.config_dir, exist_ok=True)
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    @patch('sys.argv', ['qcmd', 'list files'])
    @patch('qcmd_cli.commands.handler.load_config')
    @patch('qcmd_cli.commands.handler.parser', new_callable=lambda: argparse.ArgumentParser(description='Test parser'))
    def test_parse_args_with_prompt(self, mock_parser, mock_load_config):
        """Test parsing command-line arguments with a prompt."""
        # Set up mock parser
        mock_parser.add_argument = MagicMock()
        mock_parser.parse_args = MagicMock(return_value=argparse.Namespace(
            prompt='list files',
            execute=False,
            shell=False,
            model='test-model',
            temperature=None,
            status=False,
            check_updates=False,
            history=False,
            logs=False,
            auto=False,
            config=None,
            log_file=None,
            no_banner=False,
            no_progress=False,
            compact=False,
            banner_font=None,
            history_count=20,
            search_history=None
        ))
        
        # Mock config
        mock_load_config.return_value = {
            'model': 'test-model',
            'temperature': 0.7,
            'ui': {
                'show_iraq_banner': True,
                'show_progress_bar': True
            }
        }
        
        # Call the function
        args = parse_args()
        
        # Check the results
        self.assertEqual(args.prompt, 'list files')
        self.assertFalse(args.execute)
        self.assertFalse(args.shell)
        self.assertEqual(args.model, 'test-model')
    
    @patch('sys.argv', ['qcmd', '--shell'])
    @patch('qcmd_cli.commands.handler.load_config')
    @patch('qcmd_cli.commands.handler.parser', new_callable=lambda: argparse.ArgumentParser(description='Test parser'))
    def test_parse_args_with_shell(self, mock_parser, mock_load_config):
        """Test parsing command-line arguments with shell flag."""
        # Set up mock parser
        mock_parser.add_argument = MagicMock()
        mock_parser.parse_args = MagicMock(return_value=argparse.Namespace(
            prompt=None,
            execute=False,
            shell=True,
            model='test-model',
            temperature=None,
            status=False,
            check_updates=False,
            history=False,
            logs=False,
            auto=False,
            config=None,
            log_file=None,
            no_banner=False,
            no_progress=False,
            compact=False,
            banner_font=None,
            history_count=20,
            search_history=None
        ))
        
        # Mock config
        mock_load_config.return_value = {
            'model': 'test-model',
            'temperature': 0.7,
            'ui': {}
        }
        
        # Call the function
        args = parse_args()
        
        # Check the results
        self.assertTrue(args.shell)
        self.assertIsNone(args.prompt)
        self.assertEqual(args.model, 'test-model')
    
    @patch('sys.argv', ['qcmd', '--status'])
    @patch('qcmd_cli.commands.handler.load_config')
    @patch('qcmd_cli.commands.handler.parser', new_callable=lambda: argparse.ArgumentParser(description='Test parser'))
    def test_parse_args_with_status(self, mock_parser, mock_load_config):
        """Test parsing command-line arguments with status flag."""
        # Set up mock parser
        mock_parser.add_argument = MagicMock()
        mock_parser.parse_args = MagicMock(return_value=argparse.Namespace(
            prompt=None,
            execute=False,
            shell=False,
            model=None,
            temperature=None,
            status=True,
            check_updates=False,
            history=False,
            logs=False,
            auto=False,
            config=None,
            log_file=None,
            no_banner=False,
            no_progress=False,
            compact=False,
            banner_font=None,
            history_count=20,
            search_history=None
        ))
        
        # Mock config
        mock_load_config.return_value = {'ui': {}}
        
        # Call the function
        args = parse_args()
        
        # Check the results
        self.assertTrue(args.status)
    
    @patch('sys.argv', ['qcmd', '--model', 'custom-model', 'list files'])
    @patch('qcmd_cli.commands.handler.load_config')
    @patch('qcmd_cli.commands.handler.parser', new_callable=lambda: argparse.ArgumentParser(description='Test parser'))
    def test_parse_args_with_model(self, mock_parser, mock_load_config):
        """Test parsing command-line arguments with model override."""
        # Set up mock parser
        mock_parser.add_argument = MagicMock()
        mock_parser.parse_args = MagicMock(return_value=argparse.Namespace(
            prompt='list files',
            execute=False,
            shell=False,
            model='custom-model',
            temperature=None,
            status=False,
            check_updates=False,
            history=False,
            logs=False,
            auto=False,
            config=None,
            log_file=None,
            no_banner=False,
            no_progress=False,
            compact=False,
            banner_font=None,
            history_count=20,
            search_history=None
        ))
        
        # Mock config
        mock_load_config.return_value = {
            'model': 'default-model',
            'ui': {}
        }
        
        # Call the function
        args = parse_args()
        
        # Check the results
        self.assertEqual(args.prompt, 'list files')
        self.assertEqual(args.model, 'custom-model')
    
    @patch('qcmd_cli.commands.handler.parse_args')
    @patch('qcmd_cli.commands.handler.load_config')
    @patch('qcmd_cli.commands.handler.display_system_status')
    def test_main_with_status(self, mock_display_status, mock_load_config, mock_parse_args):
        """Test main function with status flag."""
        # Set up mock args
        mock_args = MagicMock()
        mock_args.status = True
        mock_args.check_updates = False
        mock_args.config = None
        mock_args.history = False
        mock_args.logs = False
        mock_args.shell = False
        mock_args.prompt = None
        mock_parse_args.return_value = mock_args
        
        # Mock config
        mock_load_config.return_value = {
            'ui': {
                'show_iraq_banner': False,
                'show_progress_bar': False
            },
            'check_updates': False
        }
        
        # Call the function
        main()
        
        # Check the results
        mock_display_status.assert_called_once()
    
    @patch('qcmd_cli.commands.handler.parse_args')
    @patch('qcmd_cli.commands.handler.load_config')
    @patch('qcmd_cli.commands.handler.print_cool_header')
    @patch('qcmd_cli.commands.handler.print_examples')
    @patch('qcmd_cli.commands.handler.start_interactive_shell')
    def test_main_with_shell(self, mock_shell, mock_examples, mock_header, mock_load_config, mock_parse_args):
        """Test main function with shell flag."""
        # Set up mock args
        mock_args = MagicMock()
        mock_args.status = False
        mock_args.check_updates = False
        mock_args.config = None
        mock_args.history = False
        mock_args.logs = False
        mock_args.shell = True
        mock_args.prompt = None
        mock_args.auto = False
        mock_args.model = 'test-model'
        mock_args.temperature = 0.8
        mock_parse_args.return_value = mock_args
        
        # Mock config
        mock_load_config.return_value = {
            'ui': {
                'show_iraq_banner': False,
                'show_progress_bar': False
            },
            'check_updates': False,
            'max_attempts': 3
        }
        
        # Call the function
        main()
        
        # Check the results
        mock_header.assert_called_once()
        mock_examples.assert_called_once()
        mock_shell.assert_called_once_with(
            auto_mode_enabled=False,
            current_model='test-model',
            current_temperature=0.8,
            max_attempts=3
        )
    
    @patch('qcmd_cli.commands.handler.parse_args')
    @patch('qcmd_cli.commands.handler.load_config')
    @patch('qcmd_cli.commands.handler.save_to_history')
    @patch('qcmd_cli.commands.handler.generate_command')
    def test_main_with_prompt(self, mock_generate, mock_history, mock_load_config, mock_parse_args):
        """Test main function with prompt."""
        # Set up mock args
        mock_args = MagicMock()
        mock_args.status = False
        mock_args.check_updates = False
        mock_args.config = None
        mock_args.history = False
        mock_args.logs = False
        mock_args.shell = False
        mock_args.auto = False
        mock_args.prompt = "list files"
        mock_args.model = 'test-model'
        mock_args.temperature = None
        mock_args.execute = False
        mock_parse_args.return_value = mock_args
        
        # Mock config
        mock_load_config.return_value = {
            'ui': {
                'show_iraq_banner': False,
                'show_progress_bar': False
            },
            'check_updates': False,
            'temperature': 0.7
        }
        
        # Mock generate_command
        mock_generate.return_value = "ls -la"
        
        # Call the function
        with patch('builtins.print') as mock_print:
            main()
        
        # Check the results
        mock_history.assert_called_once_with('list files')
        mock_generate.assert_called_once_with(
            prompt='list files',
            model='test-model',
            temperature=0.7
        )
        mock_print.assert_any_call('\nls -la')


if __name__ == '__main__':
    unittest.main() 