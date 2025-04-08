#!/usr/bin/env python3
"""
Additional tests for the command handler functionality to improve coverage.
"""
import unittest
import os
import sys
import argparse
import tempfile
from unittest.mock import patch, MagicMock, call

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test
from qcmd_cli.commands.handler import parse_args, main


class TestCommandHandlerAdditional(unittest.TestCase):
    """Additional tests for the command handler functions."""
    
    def setUp(self):
        """Set up temporary files for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = os.path.join(self.temp_dir.name, '.qcmd')
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Configure logging to use the temporary directory
        log_dir = os.path.join(self.temp_dir.name, '.qcmd')
        os.makedirs(log_dir, exist_ok=True)
        
        # Patch the logging configuration
        self.logging_patch = patch('qcmd_cli.core.command_generator.logging.basicConfig')
        self.mock_logging = self.logging_patch.start()
        
        # Configure the mock logging
        self.mock_logging.return_value = None
    
    def tearDown(self):
        """Clean up temporary files."""
        self.logging_patch.stop()
        self.temp_dir.cleanup()
    
    @patch('qcmd_cli.commands.handler.parse_args')
    @patch('qcmd_cli.commands.handler.load_config')
    @patch('qcmd_cli.commands.handler.check_for_updates')
    def test_main_with_check_updates(self, mock_check_updates, mock_load_config, mock_parse_args):
        """Test main function with check_updates flag."""
        # Set up mock args
        mock_args = MagicMock()
        mock_args.status = False
        mock_args.check_updates = True
        mock_args.config = None
        mock_args.history = False
        mock_args.logs = False
        mock_args.shell = False
        mock_args.prompt = None
        mock_args.model = 'test-model'
        mock_parse_args.return_value = mock_args
        
        # Mock config
        mock_load_config.return_value = {
            'ui': {
                'show_iraq_banner': False,
                'show_progress_bar': False
            },
            'check_updates': True
        }
        
        # Call the function
        main()
        
        # Check that check_for_updates was called with force_display=True
        mock_check_updates.assert_called_with(force_display=True)
    
    @patch('qcmd_cli.commands.handler.parse_args')
    @patch('qcmd_cli.commands.handler.load_config')
    @patch('qcmd_cli.commands.handler.handle_config_command')
    def test_main_with_config(self, mock_handle_config, mock_load_config, mock_parse_args):
        """Test main function with config parameter."""
        # Set up mock args
        mock_args = MagicMock()
        mock_args.status = False
        mock_args.check_updates = False
        mock_args.config = 'model=llama2'
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
            }
        }
        
        # Call the function
        main()
        
        # Check that handle_config_command was called correctly
        mock_handle_config.assert_called_once_with('set model llama2')

    @patch('qcmd_cli.commands.handler.parse_args')
    @patch('qcmd_cli.commands.handler.load_config')
    @patch('qcmd_cli.commands.handler.handle_config_command')
    def test_main_with_invalid_config(self, mock_handle_config, mock_load_config, mock_parse_args):
        """Test main function with invalid config parameter."""
        # Set up mock args
        mock_args = MagicMock()
        mock_args.status = False
        mock_args.check_updates = False
        mock_args.config = 'invalid_config_format'  # No equals sign
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
            }
        }
        
        # Call the function
        with patch('builtins.print') as mock_print:
            main()
        
        # Check that handle_config_command was not called for invalid format
        mock_handle_config.assert_not_called()
        # Verify error message was printed
        mock_print.assert_any_call("Usage: --config KEY=VALUE")

    @patch('qcmd_cli.commands.handler.parse_args')
    @patch('qcmd_cli.commands.handler.load_config')
    @patch('qcmd_cli.commands.handler.show_history')
    def test_main_with_history(self, mock_show_history, mock_load_config, mock_parse_args):
        """Test main function with history flag."""
        # Set up mock args
        mock_args = MagicMock()
        mock_args.status = False
        mock_args.check_updates = False
        mock_args.config = None
        mock_args.history = True
        mock_args.history_count = 30
        mock_args.search_history = 'grep'
        mock_args.logs = False
        mock_args.shell = False
        mock_args.prompt = None
        mock_parse_args.return_value = mock_args
        
        # Mock config
        mock_load_config.return_value = {
            'ui': {
                'show_iraq_banner': False,
                'show_progress_bar': False
            }
        }
        
        # Call the function
        main()
        
        # Check that show_history was called with correct parameters
        mock_show_history.assert_called_once_with(30, 'grep')

    @patch('qcmd_cli.commands.handler.parse_args')
    @patch('qcmd_cli.commands.handler.load_config')
    @patch('qcmd_cli.commands.handler.handle_log_analysis')
    def test_main_with_logs(self, mock_handle_logs, mock_load_config, mock_parse_args):
        """Test main function with logs flag."""
        # Set up mock args
        mock_args = MagicMock()
        mock_args.status = False
        mock_args.check_updates = False
        mock_args.config = None
        mock_args.history = False
        mock_args.logs = True
        mock_args.log_file = '/var/log/test.log'
        mock_args.shell = False
        mock_args.prompt = None
        mock_args.model = 'test-model'
        mock_parse_args.return_value = mock_args
        
        # Mock config
        mock_load_config.return_value = {
            'ui': {
                'show_iraq_banner': False,
                'show_progress_bar': False
            }
        }
        
        # Call the function
        main()
        
        # Check that handle_log_analysis was called with correct parameters
        mock_handle_logs.assert_called_once_with('test-model', '/var/log/test.log')

    @patch('qcmd_cli.commands.handler.parse_args')
    @patch('qcmd_cli.commands.handler.load_config')
    @patch('qcmd_cli.commands.handler.auto_mode')
    @patch('qcmd_cli.core.command_generator.list_models')
    @patch('qcmd_cli.core.command_generator.requests.post')
    def test_main_with_auto_mode(self, mock_post, mock_list_models, mock_auto_mode, mock_load_config, mock_parse_args):
        """Test main function with auto mode flag."""
        # Set up mock args
        mock_args = MagicMock()
        mock_args.status = False
        mock_args.check_updates = False
        mock_args.config = None
        mock_args.history = False
        mock_args.logs = False
        mock_args.shell = False
        mock_args.auto = True
        mock_args.prompt = 'list files'
        mock_args.model = 'test-model'
        mock_args.temperature = 0.5
        mock_parse_args.return_value = mock_args
        
        # Mock config
        mock_load_config.return_value = {
            'ui': {
                'show_iraq_banner': False,
                'show_progress_bar': False
            },
            'max_attempts': 5
        }
        
        # Mock list_models to include our test model
        mock_list_models.return_value = ['test-model', 'qwen2.5-coder:0.5b']
        
        # Mock API response for streaming
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            b'{"response": "ls", "done": false}',
            b'{"response": " -la", "done": true}'
        ]
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Call the function
        main()
        
        # Verify auto_mode was called with the correct parameters
        mock_auto_mode.assert_called_once_with(
            prompt='list files',
            model='test-model',
            max_attempts=5,
            temperature=0.5
        )

    @patch('qcmd_cli.commands.handler.parse_args')
    @patch('qcmd_cli.commands.handler.load_config')
    @patch('qcmd_cli.commands.handler.save_to_history')
    @patch('qcmd_cli.commands.handler.generate_command')
    @patch('qcmd_cli.commands.handler.execute_command')
    def test_main_with_execute(self, mock_execute, mock_generate, mock_history, mock_load_config, mock_parse_args):
        """Test main function with execute flag."""
        # Set up mock args
        mock_args = MagicMock()
        mock_args.status = False
        mock_args.check_updates = False
        mock_args.config = None
        mock_args.history = False
        mock_args.logs = False
        mock_args.shell = False
        mock_args.auto = False
        mock_args.prompt = 'list files'
        mock_args.model = 'test-model'
        mock_args.temperature = 0.5
        mock_args.execute = True
        mock_parse_args.return_value = mock_args
        
        # Mock config
        mock_load_config.return_value = {
            'ui': {
                'show_iraq_banner': False,
                'show_progress_bar': False
            },
            'temperature': 0.7
        }
        
        # Mock command generation and execution
        mock_generate.return_value = 'ls -la'
        mock_execute.return_value = (0, 'total 120\ndrwxr-xr-x 16 user user 4096 Jun 12 10:24 .')
        
        # Call the function
        with patch('builtins.print') as mock_print:
            main()
        
        # Check that execute_command was called with correct parameters
        mock_execute.assert_called_once_with('ls -la')
        mock_print.assert_any_call('\nCommand executed successfully.')

    @patch('qcmd_cli.commands.handler.parse_args')
    @patch('qcmd_cli.commands.handler.load_config')
    @patch('qcmd_cli.commands.handler.save_to_history')
    @patch('qcmd_cli.commands.handler.generate_command')
    @patch('qcmd_cli.commands.handler.execute_command')
    def test_main_with_execute_failed(self, mock_execute, mock_generate, mock_history, mock_load_config, mock_parse_args):
        """Test main function with execute flag when command fails."""
        # Set up mock args
        mock_args = MagicMock()
        mock_args.status = False
        mock_args.check_updates = False
        mock_args.config = None
        mock_args.history = False
        mock_args.logs = False
        mock_args.shell = False
        mock_args.auto = False
        mock_args.prompt = 'list files'
        mock_args.model = 'test-model'
        mock_args.temperature = None
        mock_args.execute = True
        mock_parse_args.return_value = mock_args
        
        # Mock config
        mock_load_config.return_value = {
            'ui': {
                'show_iraq_banner': False,
                'show_progress_bar': False
            },
            'temperature': 0.7
        }
        
        # Mock command generation and execution
        mock_generate.return_value = 'invalid_command'
        mock_execute.return_value = (1, 'command not found: invalid_command')
        
        # Call the function
        with patch('builtins.print') as mock_print:
            main()
        
        # Check that execute_command was called and error was printed
        mock_execute.assert_called_once_with('invalid_command')
        mock_print.assert_any_call('\nCommand execution failed with return code 1.')

    @patch('sys.argv', ['qcmd', '--no-banner', '--no-progress', '--compact'])
    @patch('qcmd_cli.commands.handler.load_config')
    @patch('qcmd_cli.commands.handler.parser', new_callable=lambda: argparse.ArgumentParser(description='Test parser'))
    def test_parse_args_with_ui_options(self, mock_parser, mock_load_config):
        """Test parsing command-line arguments with UI customization options."""
        # Set up mock parser
        mock_parser.add_argument = MagicMock()
        mock_parser.parse_args = MagicMock(return_value=argparse.Namespace(
            prompt=None,
            execute=False,
            shell=False,
            model=None,
            temperature=None,
            status=False,
            check_updates=False,
            history=False,
            logs=False,
            auto=False,
            config=None,
            log_file=None,
            no_banner=True,
            no_progress=True,
            compact=True,
            banner_font='standard',
            history_count=20,
            search_history=None
        ))
        
        # Mock config
        mock_config = {
            'model': 'default-model',
            'ui': {
                'show_iraq_banner': True,
                'show_progress_bar': True,
                'compact_mode': False
            }
        }
        mock_load_config.return_value = mock_config
        
        # Call the function
        args = parse_args()
        
        # Check the results - verify UI settings were applied to config
        self.assertEqual(mock_config['ui']['show_iraq_banner'], False)
        self.assertEqual(mock_config['ui']['show_progress_bar'], False)
        self.assertEqual(mock_config['ui']['compact_mode'], True)

    @patch('qcmd_cli.commands.handler.parse_args')
    @patch('qcmd_cli.commands.handler.load_config')
    @patch('qcmd_cli.commands.handler.parser')
    def test_main_with_no_prompt(self, mock_parser, mock_load_config, mock_parse_args):
        """Test main function with no prompt."""
        # Set up mock args
        mock_args = MagicMock()
        mock_args.status = False
        mock_args.check_updates = False
        mock_args.config = None
        mock_args.history = False
        mock_args.logs = False
        mock_args.shell = False
        mock_args.auto = False
        mock_args.prompt = None
        mock_args.model = 'test-model'
        mock_parse_args.return_value = mock_args
        
        # Mock config
        mock_load_config.return_value = {
            'ui': {
                'show_iraq_banner': False,
                'show_progress_bar': False
            }
        }
        
        # Call the function
        with patch('qcmd_cli.commands.handler.print_cool_header') as mock_header:
            with patch('qcmd_cli.commands.handler.print_examples') as mock_examples:
                main()
        
        # Check that print_cool_header and print_examples were called
        mock_header.assert_called_once()
        mock_examples.assert_called_once()
        # Check that parser.print_help was called
        mock_parser.print_help.assert_called_once()

    @patch('sys.argv', ['qcmd', '--banner-font', 'slant'])
    @patch('qcmd_cli.commands.handler.load_config')
    @patch('qcmd_cli.commands.handler.parser', new_callable=lambda: argparse.ArgumentParser(description='Test parser'))
    def test_parse_args_with_banner_font(self, mock_parser, mock_load_config):
        """Test parsing command-line arguments with banner font option."""
        # Set up mock parser
        mock_parser.add_argument = MagicMock()
        mock_parser.parse_args = MagicMock(return_value=argparse.Namespace(
            prompt=None,
            execute=False,
            shell=False,
            model=None,
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
            banner_font='slant',
            history_count=20,
            search_history=None
        ))
        
        # Mock config
        mock_config = {
            'model': 'default-model',
            'ui': {
                'show_iraq_banner': True,
                'show_progress_bar': True,
                'banner_font': 'standard'
            }
        }
        mock_load_config.return_value = mock_config
        
        # Call the function
        args = parse_args()
        
        # Check the results - verify banner_font was set in config
        self.assertEqual(mock_config['ui']['banner_font'], 'slant')


if __name__ == '__main__':
    unittest.main() 