#!/usr/bin/env python3
"""
Additional tests for interactive shell functionality to improve coverage.
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
from qcmd_cli.ui.display import Colors


class TestInteractiveShellAdditional(unittest.TestCase):
    """Additional tests for the interactive shell functions."""
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('os.system')
    def test_shell_clear_command(self, mock_system, mock_parse_bind, 
                                mock_set_completer, mock_print, mock_input):
        """Test clear command in the shell."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            '!clear',  # Clear command
            '!exit'    # Exit command
        ]
        
        # Call the function
        start_interactive_shell()
        
        # Verify clear screen command was called
        mock_system.assert_called_once()
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('qcmd_cli.core.interactive_shell.show_history')
    def test_shell_history_command(self, mock_history, mock_parse_bind, 
                                  mock_set_completer, mock_print, mock_input):
        """Test history command in the shell."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            '!history',      # History command with default count
            '!history 10',   # History command with specific count
            '!exit'          # Exit command
        ]
        
        # Call the function
        start_interactive_shell()
        
        # Verify history function was called twice with correct parameters
        mock_history.assert_has_calls([
            call(20),  # Default count
            call(10)   # Specific count
        ])
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('qcmd_cli.core.interactive_shell.show_history')
    def test_shell_search_command(self, mock_history, mock_parse_bind, 
                                 mock_set_completer, mock_print, mock_input):
        """Test search command in the shell."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            '!search',        # Search command without term
            '!search files',  # Search command with term
            '!exit'           # Exit command
        ]
        
        # Call the function
        start_interactive_shell()
        
        # Verify search was called with correct term
        mock_history.assert_called_once_with(search_term='files')
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('qcmd_cli.core.interactive_shell.display_system_status')
    def test_shell_status_command(self, mock_status, mock_parse_bind, 
                                 mock_set_completer, mock_print, mock_input):
        """Test status command in the shell."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            '!status',  # Status command
            '!exit'     # Exit command
        ]
        
        # Call the function
        start_interactive_shell()
        
        # Verify system status was displayed
        mock_status.assert_called_once()
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('qcmd_cli.core.command_generator.list_models')
    def test_shell_models_command(self, mock_list_models, mock_parse_bind, 
                                 mock_set_completer, mock_print, mock_input):
        """Test models command in the shell."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            '!models',  # Models command
            '!exit'     # Exit command
        ]
        
        # Mock list_models to return some test models
        mock_list_models.return_value = ['model1', 'model2', 'test-model']
        
        # Call the function
        start_interactive_shell(current_model='test-model')
        
        # Verify list_models was called
        mock_list_models.assert_called_once()
        
        # Verify model list was printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any('Available models' in call for call in print_calls))
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('qcmd_cli.core.interactive_shell.load_config')
    @patch('qcmd_cli.config.settings.save_config')
    def test_shell_model_command(self, mock_save_config, mock_load_config, mock_parse_bind, 
                               mock_set_completer, mock_print, mock_input):
        """Test model command in the shell."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            '!model',          # Model command without argument
            '!model llama3',   # Model command with argument
            '!exit'            # Exit command
        ]
        
        # Mock load_config to return a test config
        mock_load_config.return_value = {'model': 'test-model', 'temperature': 0.7}
        
        # Call the function
        start_interactive_shell(current_model='test-model')
        
        # Verify config was updated with new model
        mock_save_config.assert_called_once()
        self.assertEqual(mock_save_config.call_args[0][0]['model'], 'llama3')
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('qcmd_cli.core.interactive_shell.load_config')
    @patch('qcmd_cli.config.settings.save_config')
    def test_shell_temperature_command(self, mock_save_config, mock_load_config, mock_parse_bind, 
                                      mock_set_completer, mock_print, mock_input):
        """Test temperature command in the shell."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            '!temperature',      # Temperature command without argument
            '!temperature 0.5',  # Temperature command with valid argument
            '!temperature 1.5',  # Temperature command with invalid argument
            '!temperature xyz',  # Temperature command with non-numeric argument
            '!exit'              # Exit command
        ]
        
        # Mock load_config to return a test config
        mock_load_config.return_value = {'model': 'test-model', 'temperature': 0.7}
        
        # Call the function
        start_interactive_shell(current_temperature=0.7)
        
        # Verify config was updated with new temperature
        mock_save_config.assert_called_once()
        self.assertEqual(mock_save_config.call_args[0][0]['temperature'], 0.5)
        
        # Verify appropriate messages were printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any('Temperature set to: 0.5' in call for call in print_calls))
        self.assertTrue(any('Temperature must be between 0.0 and 1.0' in call for call in print_calls))
        self.assertTrue(any('Invalid temperature value' in call for call in print_calls))
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    def test_shell_auto_command(self, mock_parse_bind, mock_set_completer, mock_print, mock_input):
        """Test auto command in the shell."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            '!auto',        # Auto command without argument
            '!auto on',     # Auto command to enable
            '!auto off',    # Auto command to disable
            '!auto invalid',# Auto command with invalid argument
            '!exit'         # Exit command
        ]
        
        # Call the function
        start_interactive_shell(auto_mode_enabled=False)
        
        # Verify appropriate messages were printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any('Auto-correction mode enabled' in call for call in print_calls))
        self.assertTrue(any('Auto-correction mode disabled' in call for call in print_calls))
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('qcmd_cli.core.interactive_shell.load_config')
    @patch('qcmd_cli.config.settings.save_config')
    def test_shell_max_command(self, mock_save_config, mock_load_config, mock_parse_bind, 
                              mock_set_completer, mock_print, mock_input):
        """Test max command in the shell."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            '!max',      # Max command without argument
            '!max 5',    # Max command with valid argument
            '!max 0',    # Max command with invalid argument
            '!max xyz',  # Max command with non-numeric argument
            '!exit'      # Exit command
        ]
        
        # Mock load_config to return a test config
        mock_load_config.return_value = {'model': 'test-model', 'max_attempts': 3}
        
        # Call the function
        start_interactive_shell(max_attempts=3)
        
        # Verify config was updated with new max attempts
        mock_save_config.assert_called_once()
        self.assertEqual(mock_save_config.call_args[0][0]['max_attempts'], 5)
        
        # Verify appropriate messages were printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any('Max attempts set to: 5' in call for call in print_calls))
        self.assertTrue(any('Max attempts must be greater than 0' in call for call in print_calls))
        self.assertTrue(any('Invalid value' in call for call in print_calls))
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('qcmd_cli.core.interactive_shell.check_for_updates')
    def test_shell_update_command(self, mock_check_updates, mock_parse_bind, 
                                 mock_set_completer, mock_print, mock_input):
        """Test update command in the shell."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            '!update',  # Update command
            '!exit'     # Exit command
        ]
        
        # Call the function
        start_interactive_shell()
        
        # Verify check_for_updates was called with force_display=True
        mock_check_updates.assert_called_once_with(force_display=True)
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('qcmd_cli.core.interactive_shell.handle_log_analysis')
    def test_shell_logs_command(self, mock_handle_logs, mock_parse_bind, 
                               mock_set_completer, mock_print, mock_input):
        """Test logs command in the shell."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            '!logs',           # Logs command without argument
            '!logs /var/log/syslog',  # Logs command with argument
            '!exit'            # Exit command
        ]
        
        # Call the function
        start_interactive_shell(current_model='test-model')
        
        # Verify handle_log_analysis was called with correct arguments
        mock_handle_logs.assert_has_calls([
            call('test-model', None),
            call('test-model', '/var/log/syslog')
        ])
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('qcmd_cli.config.settings.handle_config_command')
    def test_shell_config_command(self, mock_handle_config, mock_parse_bind, 
                                 mock_set_completer, mock_print, mock_input):
        """Test config command in the shell."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            '!config show',  # Config command with argument
            '!exit'          # Exit command
        ]
        
        # Call the function
        start_interactive_shell()
        
        # Verify handle_config_command was called with correct argument
        mock_handle_config.assert_called_once_with('show')
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('qcmd_cli.core.interactive_shell.generate_command')
    @patch('qcmd_cli.core.interactive_shell.execute_command')
    def test_shell_repeat_command(self, mock_execute, mock_generate, mock_parse_bind, 
                                 mock_set_completer, mock_print, mock_input):
        """Test repeat command (!!) in the shell."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            'list files',  # First command
            'y',           # Confirm execution
            '!!',          # Repeat command
            'y',           # Confirm execution again
            '!exit'        # Exit command
        ]
        
        # Mock generate_command to return a test command
        mock_generate.return_value = 'ls -la'
        
        # Mock execute_command to return success
        mock_execute.return_value = (0, 'file1.txt\nfile2.txt')
        
        # Call the function
        start_interactive_shell()
        
        # Verify generate_command was called at least once
        self.assertTrue(mock_generate.called)
        
        # Verify execute_command was called twice (for original and repeat)
        self.assertEqual(mock_execute.call_count, 2)
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('qcmd_cli.core.interactive_shell.generate_command')
    @patch('qcmd_cli.core.interactive_shell.execute_command')
    def test_shell_command_rejection(self, mock_execute, mock_generate, mock_parse_bind, 
                                    mock_set_completer, mock_print, mock_input):
        """Test rejecting a generated command."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            'list files',  # First command
            'n',           # Reject execution
            '!exit'        # Exit command
        ]
        
        # Mock generate_command to return a test command
        mock_generate.return_value = 'ls -la'
        
        # Call the function
        start_interactive_shell()
        
        # Verify generate_command was called
        mock_generate.assert_called_once()
        
        # Verify execute_command was not called
        mock_execute.assert_not_called()
    
    @patch('qcmd_cli.core.interactive_shell.generate_command')
    @patch('qcmd_cli.core.interactive_shell.execute_command')
    @patch('qcmd_cli.core.interactive_shell.fix_command')
    @patch('builtins.print')
    @patch('builtins.input')
    def test_auto_mode_success(self, mock_input, mock_print, mock_fix, mock_execute, mock_generate):
        """Test auto_mode with successful execution."""
        # Mock generate_command to return a command
        mock_generate.return_value = 'ls -la'
        
        # Mock execute_command to return success
        mock_execute.return_value = (0, 'file1.txt\nfile2.txt')
        
        # Call auto_mode
        auto_mode('list files', 'test-model', 3, 0.7)
        
        # Verify generate_command was called
        mock_generate.assert_called_once_with('list files', 'test-model', 0.7)
        
        # Verify execute_command was called
        mock_execute.assert_called_once_with('ls -la')
        
        # Verify fix_command was not called since execution succeeded
        mock_fix.assert_not_called()
    
    @patch('qcmd_cli.core.interactive_shell.generate_command')
    @patch('qcmd_cli.core.interactive_shell.execute_command')
    @patch('qcmd_cli.core.interactive_shell.fix_command')
    @patch('builtins.print')
    def test_auto_mode_failure_and_fix(self, mock_print, mock_fix, mock_execute, mock_generate):
        """Test auto_mode with failure and auto-fixing."""
        # Mock generate_command to return a command
        mock_generate.return_value = 'ls -z'  # Invalid option
        
        # Mock execute_command to return error first, then success
        mock_execute.side_effect = [
            (1, 'ls: invalid option -- z'),  # First execution fails
            (0, 'file1.txt\nfile2.txt')      # Second execution succeeds
        ]
        
        # Mock fix_command to return corrected command
        mock_fix.return_value = 'ls -a'
        
        # Call auto_mode
        auto_mode('list files', 'test-model', 3, 0.7)
        
        # Verify generate_command was called
        mock_generate.assert_called_once_with('list files', 'test-model', 0.7)
        
        # Verify execute_command was called twice
        self.assertEqual(mock_execute.call_count, 2)
        
        # Verify fix_command was called
        mock_fix.assert_called_once_with('ls -z', 'ls: invalid option -- z', 'test-model')
    
    @patch('qcmd_cli.core.interactive_shell.generate_command')
    @patch('qcmd_cli.core.interactive_shell.execute_command')
    @patch('qcmd_cli.core.interactive_shell.fix_command')
    @patch('builtins.print')
    def test_auto_mode_max_attempts(self, mock_print, mock_fix, mock_execute, mock_generate):
        """Test auto_mode reaching maximum attempts."""
        # Mock generate_command to return a command
        mock_generate.return_value = 'ls -z'  # Invalid option
        
        # Mock execute_command to always return error
        mock_execute.return_value = (1, 'ls: invalid option -- z')
        
        # Mock fix_command to return another invalid command
        mock_fix.return_value = 'ls -z'  # Still invalid
        
        # Call auto_mode with max_attempts=2
        auto_mode('list files', 'test-model', 2, 0.7)
        
        # Verify execute_command was called max_attempts times
        self.assertEqual(mock_execute.call_count, 2)
        
        # Verify fix_command was called max_attempts-1 times
        self.assertEqual(mock_fix.call_count, 1)
        
        # Verify appropriate message was printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        # Check for different possible messages that might be printed
        self.assertTrue(
            any('Maximum number of attempts' in call for call in print_calls) or
            any('attempt' in call for call in print_calls)
        )
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('signal.signal')
    @patch('sys.exit')
    def test_shell_sigint_handler(self, mock_exit, mock_signal, mock_parse_bind, 
                               mock_set_completer, mock_print, mock_input):
        """Test SIGINT handler function in the shell."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = ['!exit']  # Exit command
        
        # Call the function
        start_interactive_shell()
        
        # Get the signal handler function that was registered
        import signal
        mock_signal.assert_called_with(signal.SIGINT, mock_signal.call_args[0][1])
        
        # Call the handler function directly
        handler_func = mock_signal.call_args[0][1]
        handler_func(None, None)
        
        # Verify sys.exit was called
        mock_exit.assert_called_once_with(0)
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    def test_shell_empty_input(self, mock_parse_bind, mock_set_completer, mock_print, mock_input):
        """Test handling of empty input in the shell."""
        # Set up mock inputs to simulate user interaction with empty input
        mock_input.side_effect = [
            '',  # Empty input
            '!exit'  # Exit command
        ]
        
        # Call the function
        start_interactive_shell()
        
        # Verify shell continues after empty input (2 prompts)
        self.assertEqual(mock_input.call_count, 2)
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('qcmd_cli.core.interactive_shell.generate_command')
    def test_shell_command_generation_failure(self, mock_generate, mock_parse_bind, 
                                           mock_set_completer, mock_print, mock_input):
        """Test handling of command generation failure."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            'list files',  # Command that will fail to generate
            '!exit'  # Exit command
        ]
        
        # Mock generate_command to return None (failure)
        mock_generate.return_value = None
        
        # Call the function
        start_interactive_shell()
        
        # Verify error message was printed
        mock_print.assert_any_call(f"{Colors.RED}Failed to generate a command.{Colors.END}")
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('qcmd_cli.core.interactive_shell.generate_command')
    @patch('qcmd_cli.core.interactive_shell.execute_command')
    def test_shell_edit_command(self, mock_execute, mock_generate, mock_parse_bind, 
                             mock_set_completer, mock_print, mock_input):
        """Test editing and executing a command."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            'list files',  # Natural language command
            'e',          # Choose to edit
            'ls -la',     # Edited command
            '!exit'       # Exit command
        ]
        
        # Mock generate_command to return a command
        mock_generate.return_value = 'ls'
        
        # Mock execute_command to indicate success
        mock_execute.return_value = (0, 'file1.txt file2.txt')
        
        # Call the function
        start_interactive_shell()
        
        # Verify execute_command was called with edited command
        mock_execute.assert_called_with('ls -la')
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('qcmd_cli.core.interactive_shell.generate_command')
    @patch('qcmd_cli.core.interactive_shell.execute_command')
    def test_shell_edit_command_empty(self, mock_execute, mock_generate, mock_parse_bind, 
                                   mock_set_completer, mock_print, mock_input):
        """Test editing a command but providing empty input."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            'list files',  # Natural language command
            'e',          # Choose to edit
            '',           # Empty edited command
            '!exit'       # Exit command
        ]
        
        # Mock generate_command to return a command
        mock_generate.return_value = 'ls'
        
        # Call the function
        start_interactive_shell()
        
        # Verify execute_command was not called
        mock_execute.assert_not_called()
        
        # Verify cancellation message was printed
        mock_print.assert_any_call(f"{Colors.YELLOW}Command execution cancelled.{Colors.END}")
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    def test_shell_eof_handling(self, mock_parse_bind, mock_set_completer, mock_print, mock_input):
        """Test handling of EOF (Ctrl+D) in the shell."""
        # Set up mock input to raise EOFError
        mock_input.side_effect = EOFError()
        
        # Call the function
        start_interactive_shell()
        
        # Verify exit message was printed
        mock_print.assert_any_call("\nExiting QCMD interactive shell...")
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    def test_shell_keyboard_interrupt(self, mock_parse_bind, mock_set_completer, mock_print, mock_input):
        """Test handling of KeyboardInterrupt (Ctrl+C) in the shell."""
        # Set up mock inputs to simulate keyboard interrupt then exit
        mock_input.side_effect = [
            KeyboardInterrupt(),
            '!exit'
        ]
        
        # Call the function
        start_interactive_shell()
        
        # Verify interrupt message was printed
        mock_print.assert_any_call("\nCommand interrupted. Type !exit to quit.")
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    def test_shell_general_exception(self, mock_parse_bind, mock_set_completer, mock_print, mock_input):
        """Test handling of general exceptions in the shell."""
        # Set up mock input to raise Exception
        mock_input.side_effect = [
            Exception("Test exception"),
            '!exit'
        ]
        
        # Call the function
        start_interactive_shell()
        
        # Verify error message was printed
        error_printed = False
        for call_args in mock_print.call_args_list:
            args = call_args[0]
            if len(args) > 0 and "Error: Test exception" in args[0]:
                error_printed = True
                break
        self.assertTrue(error_printed)
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('qcmd_cli.core.interactive_shell.auto_mode')
    @patch('qcmd_cli.core.interactive_shell.save_to_history')
    def test_shell_auto_mode_execution(self, mock_history, mock_auto_mode, mock_parse_bind, 
                                    mock_set_completer, mock_print, mock_input):
        """Test auto mode execution flow."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            'list files',  # Natural language command
            '!exit'        # Exit command
        ]
        
        # Call the function with auto_mode_enabled=True
        start_interactive_shell(auto_mode_enabled=True)
        
        # Verify auto_mode was called with correct parameters
        mock_auto_mode.assert_called_once_with('list files', 'qwen2.5-coder:0.5b', 3, 0.7)
        
        # Verify history was saved
        mock_history.assert_called_once_with('list files')
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('qcmd_cli.core.interactive_shell.generate_command')
    @patch('qcmd_cli.core.interactive_shell.execute_command')
    def test_shell_execute_with_output(self, mock_execute, mock_generate, mock_parse_bind, 
                                    mock_set_completer, mock_print, mock_input):
        """Test executing a command that produces output."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            'list files',  # Natural language command
            'y',           # Confirm execution
            '!exit'        # Exit command
        ]
        
        # Mock generate_command to return a command
        mock_generate.return_value = 'ls -la'
        
        # Mock execute_command to return success with output
        mock_execute.return_value = (0, 'total 123\ndrwxr-xr-x 16 user user 4096 Jun 13 10:24 .')
        
        # Call the function
        start_interactive_shell()
        
        # Verify execute_command was called
        mock_execute.assert_called_once_with('ls -la')
        
        # Verify output was printed - The exact format might be different due to Colors
        output_printed = False
        for call_args in mock_print.call_args_list:
            args = call_args[0]
            if len(args) > 0 and 'total 123' in args[0]:
                output_printed = True
                break
        self.assertTrue(output_printed, "Command output was not printed")
    
    @patch('builtins.input')
    @patch('builtins.print')
    @patch('readline.set_completer')
    @patch('readline.parse_and_bind')
    @patch('qcmd_cli.core.interactive_shell.generate_command')
    @patch('qcmd_cli.core.interactive_shell.execute_command')
    def test_shell_execute_command_failure(self, mock_execute, mock_generate, mock_parse_bind, 
                                        mock_set_completer, mock_print, mock_input):
        """Test executing a command that fails."""
        # Set up mock inputs to simulate user interaction
        mock_input.side_effect = [
            'list files',  # Natural language command
            'y',           # Confirm execution
            '!exit'        # Exit command
        ]
        
        # Mock generate_command to return a command
        mock_generate.return_value = 'ls -Z'  # Invalid option
        
        # Mock execute_command to return failure with error output
        mock_execute.return_value = (1, 'ls: invalid option -- Z')
        
        # Call the function
        start_interactive_shell()
        
        # Verify execute_command was called
        mock_execute.assert_called_once_with('ls -Z')
        
        # Verify failure message was printed
        mock_print.assert_any_call(f"\n{Colors.RED}Command failed with return code 1{Colors.END}")
        
        # Verify error output was printed
        mock_print.assert_any_call('ls: invalid option -- Z')
    
    @patch('qcmd_cli.core.interactive_shell.generate_command')
    @patch('qcmd_cli.core.interactive_shell.time.sleep')
    @patch('builtins.print')
    def test_auto_mode_command_generation_failure(self, mock_print, mock_sleep, mock_generate):
        """Test auto_mode handling of command generation failure."""
        # Mock generate_command to return None (failure)
        mock_generate.return_value = None
        
        # Call the function
        auto_mode('list files')
        
        # Verify error message was printed
        mock_print.assert_any_call(f"{Colors.RED}Failed to generate a command.{Colors.END}")
    
    @patch('qcmd_cli.core.interactive_shell.generate_command')
    @patch('qcmd_cli.core.interactive_shell.execute_command')
    @patch('qcmd_cli.core.interactive_shell.fix_command')
    @patch('builtins.print')
    def test_auto_mode_keyboard_interrupt(self, mock_print, mock_fix, mock_execute, mock_generate):
        """Test keyboard interrupt handling in auto_mode."""
        # Mock generate_command to return a command
        mock_generate.return_value = 'ls -la'
        
        # Use a side_effect function to raise KeyboardInterrupt but only on first call
        call_count = [0]
        def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise KeyboardInterrupt()
            return (0, "file1.txt")
            
        mock_execute.side_effect = execute_side_effect
        
        # Call the function - we expect it to handle the KeyboardInterrupt
        try:
            auto_mode('list files')
            
            # Verify that the command generation was attempted
            mock_generate.assert_called_once_with('list files', 'qwen2.5-coder:0.5b', 0.7)
            
            # Verify execute_command was called
            mock_execute.assert_called_once_with('ls -la')
            
            # Verify interrupt message was printed
            interrupt_message_printed = False
            for call_args in mock_print.call_args_list:
                args = call_args[0]
                if len(args) > 0 and "Command interrupted" in args[0]:
                    interrupt_message_printed = True
                    break
            self.assertTrue(interrupt_message_printed, "Interrupt message was not printed")
            
        except KeyboardInterrupt:
            self.fail("KeyboardInterrupt was not handled properly")


if __name__ == '__main__':
    unittest.main() 