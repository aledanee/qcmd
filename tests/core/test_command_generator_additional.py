#!/usr/bin/env python3
"""
Additional tests for the command_generator module to improve coverage.
"""
import unittest
import os
import sys
import json
import requests
import time
from unittest.mock import patch, MagicMock, call, mock_open
import subprocess
import click
import pytest

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test
from qcmd_cli.core.command_generator import (
    generate_command, analyze_error, fix_command, 
    list_models, execute_command, is_dangerous_command,
    DANGEROUS_PATTERNS,
    CommandGenerationError, APITimeoutError, APIConnectionError,
    APIRateLimitError, APIResponseError, ModelUnavailableError,
    CommandValidationError, CommandExecutionError, CommandOutputError
)
from qcmd_cli.config.settings import DEFAULT_MODEL


class TestCommandGeneratorAdditional(unittest.TestCase):
    """Additional tests for the command generator functions."""

    @pytest.mark.api
    @patch('qcmd_cli.core.command_generator.time.sleep')  # Skip actual waiting
    @patch('qcmd_cli.core.command_generator.requests.post')
    @patch('qcmd_cli.core.command_generator.list_models')
    def test_generate_command_timeout(self, mock_list_models, mock_post, mock_sleep):
        """Test generate_command with timeout errors and retries."""
        # Mock list_models to return some models
        mock_list_models.return_value = ["model1", "model2", DEFAULT_MODEL]
        
        # Create response object for the successful attempt
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "ls -la"}
        mock_response.raise_for_status.return_value = None
        
        # Mock post to raise timeout for the first two attempts, then succeed
        mock_post.side_effect = [
            requests.exceptions.Timeout("Request timed out"),
            requests.exceptions.Timeout("Request timed out"),
            mock_response  # Success on third attempt
        ]
        
        # Call function
        command = generate_command("list files")
        
        # Verify the command is correct
        self.assertEqual(command, "ls -la")
        
        # Verify retries occurred
        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)  # Sleep only happens between retries

    @pytest.mark.api
    @pytest.mark.timeout
    @patch('qcmd_cli.core.command_generator.requests.post')
    @patch('qcmd_cli.core.command_generator.list_models')
    def test_generate_command_all_timeouts(self, mock_list_models, mock_post):
        """Test generate_command when all attempts timeout."""
        from qcmd_cli.core.command_generator import generate_command
        
        # Setup mocks
        mock_list_models.return_value = ["gpt-4"]
        mock_post.side_effect = requests.exceptions.Timeout()
        
        # Test that the function raises APITimeoutError after all retries
        with self.assertRaises(APITimeoutError) as context:
            generate_command("test command", model="gpt-4")
        
        # Verify error message
        self.assertIn("API request timed out after 3 attempts", str(context.exception))
        
        # Verify retry count
        self.assertEqual(mock_post.call_count, 3)
        
        # Verify exponential backoff was used
        call_times = [call[1]['timeout'] for call in mock_post.call_args_list]
        self.assertEqual(call_times, [30, 60, 120])  # 30s, 60s, 120s

    @pytest.mark.dangerous
    @patch('qcmd_cli.core.command_generator.time.sleep')  # Skip actual waiting
    @patch('qcmd_cli.core.command_generator.requests.post')
    @patch('qcmd_cli.core.command_generator.list_models')
    def test_generate_command_connection_error(self, mock_list_models, mock_post, mock_sleep):
        """Test generate_command with connection errors."""
        # Mock list_models to return empty list (no models available)
        mock_list_models.return_value = []
        
        # Mock post to raise connection error for all attempts
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        # Call function
        command = generate_command("list files")
        
        # Verify error command is returned
        self.assertIn("echo 'Error: Command generation failed", command)
        self.assertIn("API connection issue", command)

    @pytest.mark.dangerous
    @patch('qcmd_cli.core.command_generator.time.sleep')  # Skip actual waiting
    @patch('qcmd_cli.core.command_generator.requests.post')
    @patch('qcmd_cli.core.command_generator.list_models')
    def test_generate_command_request_exception(self, mock_list_models, mock_post, mock_sleep):
        """Test generate_command with general request exceptions."""
        # Mock list_models to return the requested model
        mock_list_models.return_value = ["custom-model"]
        
        # Mock post to raise an exception
        mock_post.side_effect = requests.exceptions.RequestException("Request failed")
        
        with self.assertRaises(CommandGenerationError) as context:
            generate_command("list files", model="custom-model")
        self.assertIn("Request failed", str(context.exception))

    @pytest.mark.dangerous
    @patch('qcmd_cli.core.command_generator.time.sleep')  # Skip actual waiting
    @patch('qcmd_cli.core.command_generator.requests.post')
    def test_generate_command_general_exception(self, mock_post, mock_sleep):
        """Test generate_command with other exceptions."""
        # Mock post to raise a general exception
        mock_post.side_effect = Exception("Unexpected error")
        
        # Call function
        command = generate_command("list files")
        
        # Verify error command is returned
        self.assertEqual(command, "echo 'Error: Command generation failed'")

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.requests.post')
    def test_fix_command_exceptions(self, mock_post):
        """Test fix_command error handling."""
        # Mock post to raise an exception
        mock_post.side_effect = Exception("API error")
        
        # Call function
        result = fix_command("broken command", "Some error")
        
        # Verify original command is returned on error
        self.assertEqual(result, "broken command")

    @pytest.mark.safe
    @patch('qcmd_cli.core.command_generator.requests.post')
    def test_fix_command_markdown_formats(self, mock_post):
        """Test fix_command handles different markdown formats."""
        # Test with triple backticks
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "```\nfixed command\n```"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        fixed = fix_command("broken command", "Some error")
        self.assertEqual(fixed, "fixed command")
        
        # Test with single backticks
        mock_response.json.return_value = {"response": "`fixed command`"}
        fixed = fix_command("broken command", "Some error")
        self.assertEqual(fixed, "fixed command")

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.requests.get')
    def test_list_models_exception(self, mock_get):
        """Test list_models handles exceptions."""
        # Mock get to raise an exception
        mock_get.side_effect = Exception("API error")
        
        # Call function
        models = list_models()
        
        # Verify empty list is returned on error
        self.assertEqual(models, [])

    @pytest.mark.dangerous
    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    @patch('qcmd_cli.core.command_generator.click.confirm')
    def test_execute_command_dangerous(self, mock_confirm, mock_popen):
        """Test execute_command with dangerous commands."""
        # Mock is_dangerous_command behavior by using a real dangerous command
        dangerous_cmd = "rm -rf /"
        
        # User confirms to proceed
        mock_confirm.return_value = True
        
        # Setup process mock
        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = ("Output", "")
        mock_popen.return_value = process_mock
        
        # Call function
        returncode, output = execute_command(dangerous_cmd)
        
        # Verify command was executed after confirmation
        self.assertEqual(returncode, 0)
        mock_popen.assert_called_once()
        
        # Reset mocks
        mock_confirm.reset_mock()
        mock_popen.reset_mock()
        
        # User aborts
        mock_confirm.return_value = False
        
        # Call function again
        with self.assertRaises(CommandExecutionError) as context:
            execute_command(dangerous_cmd)
        self.assertIn("Command execution cancelled by user", str(context.exception))
        mock_popen.assert_not_called()

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    @patch('qcmd_cli.core.command_generator.click.confirm')
    def test_execute_command_validation_errors(self, mock_confirm, mock_popen):
        """Test execute_command with various validation errors."""
        # Test dangerous command
        with self.assertRaises(CommandValidationError) as context:
            execute_command("rm -rf /")
        self.assertIn("Command appears to be dangerous", str(context.exception))
        
        # Test command with command injection
        with self.assertRaises(CommandValidationError) as context:
            execute_command("ls; rm -rf /")
        self.assertIn("Command contains potential command injection pattern", str(context.exception))
        
        # Test command with invalid characters
        with self.assertRaises(CommandValidationError) as context:
            execute_command("ls\x00 -la")
        self.assertIn("Command contains invalid control character", str(context.exception))
        
        # Verify no commands were executed
        mock_popen.assert_not_called()
        mock_confirm.assert_not_called()

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    def test_execute_command_exception(self, mock_popen):
        """Test execute_command with subprocess exception."""
        # Mock Popen to raise an exception
        mock_popen.side_effect = Exception("Execution error")
        
        with self.assertRaises(CommandExecutionError) as context:
            execute_command("ls")
        self.assertIn("Command failed after 3 attempts", str(context.exception))

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    def test_execute_command_process_exception(self, mock_popen):
        """Test execute_command when process creation fails."""
        # Mock Popen to raise a specific error that won't affect the parent process
        mock_popen.side_effect = [
            subprocess.SubprocessError("Process creation failed"),  # First attempt fails
            subprocess.SubprocessError("Process creation failed"),  # Second attempt fails
            subprocess.SubprocessError("Process creation failed")   # Third attempt fails
        ]
        
        # Test that the function handles process failure correctly
        with self.assertRaises(CommandExecutionError) as context:
            execute_command("test_command")
        self.assertIn("Command failed after 3 attempts", str(context.exception))
        
        # Verify Popen was called with the correct arguments
        expected_calls = [
            call("test_command", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        ] * 3  # Should be called three times due to retries
        mock_popen.assert_has_calls(expected_calls)
        self.assertEqual(mock_popen.call_count, 3)

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    def test_execute_command_process_timeout(self, mock_popen):
        """Test execute_command with a process that times out."""
        # Mock process that times out
        process_mock = MagicMock()
        process_mock.communicate.side_effect = subprocess.TimeoutExpired("sleep 100", 30)
        mock_popen.return_value = process_mock
        
        with self.assertRaises(CommandExecutionError) as context:
            execute_command("sleep 100")
        self.assertIn("Command failed after 3 attempts", str(context.exception))

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    def test_execute_command_timeout_handling(self, mock_popen):
        """Test execute_command handling process timeout."""
        # Mock process that times out
        process_mock = MagicMock()
        process_mock.communicate.side_effect = subprocess.TimeoutExpired("test_cmd", 60)
        mock_popen.return_value = process_mock
        
        with self.assertRaises(CommandExecutionError) as context:
            execute_command("test_cmd")
        self.assertIn("Command failed after 3 attempts", str(context.exception))

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    def test_execute_command_timeout_cleanup(self, mock_popen):
        """Test execute_command cleanup after timeout."""
        # Mock process that times out
        process_mock = MagicMock()
        process_mock.communicate.side_effect = subprocess.TimeoutExpired("test_cmd", 30)
        mock_popen.return_value = process_mock
        
        with self.assertRaises(CommandExecutionError) as context:
            execute_command("test_cmd")
        self.assertIn("Command failed after", str(context.exception))
        self.assertEqual(process_mock.kill.call_count, 3)  # Called once for each retry

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    def test_execute_command_timeout_with_output(self, mock_popen):
        """Test execute_command handling timeout with output."""
        # Mock process that times out with output
        process_mock = MagicMock()
        process_mock.communicate.side_effect = subprocess.TimeoutExpired("test_cmd", 30)
        process_mock.stdout = "Some output"
        mock_popen.return_value = process_mock
        
        with self.assertRaises(CommandExecutionError) as context:
            execute_command("test_cmd")
        self.assertIn("Command failed after 3 attempts", str(context.exception))

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    def test_execute_command_timeout_with_stderr(self, mock_popen):
        """Test execute_command handling timeout with stderr output."""
        # Mock process that times out with stderr
        process_mock = MagicMock()
        process_mock.communicate.side_effect = subprocess.TimeoutExpired("test_cmd", 30)
        process_mock.stderr = "Error output"
        mock_popen.return_value = process_mock
        
        with self.assertRaises(CommandExecutionError) as context:
            execute_command("test_cmd")
        self.assertIn("Command failed after 3 attempts", str(context.exception))

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    def test_execute_command_timeout_with_both_outputs(self, mock_popen):
        """Test execute_command handling timeout with both stdout and stderr output."""
        # Mock process that times out with both outputs
        process_mock = MagicMock()
        process_mock.communicate.side_effect = subprocess.TimeoutExpired("test_cmd", 30)
        process_mock.stdout = "Some output"
        process_mock.stderr = "Error output"
        mock_popen.return_value = process_mock
        
        with self.assertRaises(CommandExecutionError) as context:
            execute_command("test_cmd")
        self.assertIn("Command failed after 3 attempts", str(context.exception))

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    def test_execute_command_retry_strategy(self, mock_popen):
        """Test execute_command retry strategy."""
        # Mock process that fails with timeout
        process_mock = MagicMock()
        process_mock.communicate.side_effect = [
            subprocess.TimeoutExpired("test_cmd", 30),
            subprocess.TimeoutExpired("test_cmd", 30),
            subprocess.TimeoutExpired("test_cmd", 30)
        ]
        mock_popen.return_value = process_mock
        
        with self.assertRaises(CommandExecutionError) as context:
            execute_command("test_cmd")
        self.assertIn("Command failed after", str(context.exception))
        self.assertEqual(process_mock.communicate.call_count, 3)

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    @patch('qcmd_cli.core.command_generator.click.confirm')
    def test_execute_command_with_recovery(self, mock_confirm, mock_popen):
        """Test execute_command with error recovery."""
        from qcmd_cli.core.command_generator import execute_command
        
        # Setup process mock for initial failure and successful fallback
        process_mock = MagicMock()
        process_mock.returncode = 1
        process_mock.communicate.return_value = ("", "permission denied")
        mock_popen.return_value = process_mock
        mock_confirm.return_value = True
        
        # Test successful recovery with fallback
        return_code, output = execute_command("ls /root")
        self.assertEqual(return_code, 0)
        self.assertEqual(output, "success")  # Mocked success output
        
        # Verify the fallback command was used
        self.assertEqual(mock_popen.call_count, 2)  # Initial attempt + fallback
        self.assertIn("ls -la", mock_popen.call_args_list[1][0][0])
        
        # Test recovery with correction
        process_mock.communicate.return_value = ("", "not a git repository")
        return_code, output = execute_command("git status")
        self.assertEqual(return_code, 0)
        self.assertEqual(output, "success")
        
        # Verify the correction was used
        self.assertIn("git init", mock_popen.call_args_list[-1][0][0])
        
        # Test no recovery available
        process_mock.communicate.return_value = ("", "unknown error")
        with self.assertRaises(CommandExecutionError) as context:
            execute_command("unknown_command")
        self.assertIn("Command failed after 3 attempts", str(context.exception))

    @pytest.mark.safe
    def test_is_dangerous_command_additional_patterns(self):
        """Test additional dangerous command patterns."""
        # Test commands with sudo/doas
        sudo_commands = [
            "sudo rm -rf /var/log/",
            "doas chmod -R 777 /etc",
            "sudo mv /etc/passwd /tmp",
            "doas dd if=/dev/zero of=/dev/sda"
        ]
        
        for cmd in sudo_commands:
            self.assertTrue(is_dangerous_command(cmd), f"Should detect {cmd} as dangerous")
        
        # Test rm with path
        path_commands = [
            "rm -f /etc/passwd",
            "rm /var/www/html/index.php"
        ]
        
        for cmd in path_commands:
            self.assertTrue(is_dangerous_command(cmd), f"Should detect {cmd} as dangerous")
            
        # Test relative paths - should be safe
        safe_commands = [
            "rm -f ./temp.txt",
            "rm -r ./build/"
        ]
        
        for cmd in safe_commands:
            self.assertFalse(is_dangerous_command(cmd), f"Should not detect {cmd} as dangerous")

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.requests.post')
    @patch('qcmd_cli.core.command_generator.list_models')
    def test_generate_command_list_models_exception(self, mock_list_models, mock_post):
        """Test generate_command when list_models raises an exception."""
        # Mock list_models to raise an exception
        mock_list_models.side_effect = Exception("List models error")
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "ls -la"}
        mock_post.return_value = mock_response
        
        # Test command generation
        result = generate_command("list files")
        
        # Verify result
        self.assertEqual(result, "ls -la")
        mock_post.assert_called_once()
        
    @pytest.mark.safe
    @patch('qcmd_cli.core.command_generator.requests.post')
    def test_fix_command_clean_markdown_single_line(self, mock_post):
        """Test fix_command with single line markdown code block."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "```ls -la```"}
        mock_post.return_value = mock_response
        
        # Test command fixing
        result = fix_command("ls", "error", DEFAULT_MODEL)
        
        # Verify result
        self.assertEqual(result, "ls -la")
        mock_post.assert_called_once()
        
    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.requests.post')
    def test_analyze_error_fallback_failure(self, mock_post):
        """Test analyze_error when both primary and fallback attempts fail."""
        # Mock failed responses
        mock_post.side_effect = Exception("Primary error")
        
        # Test error analysis
        result = analyze_error("error", "ls", DEFAULT_MODEL)
        
        # Verify result
        self.assertTrue(result.startswith("Could not analyze error due to API issue"))
        self.assertEqual(mock_post.call_count, 1)
        
    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.requests.get')
    def test_list_models_exception_handling(self, mock_get):
        """Test list_models exception handling."""
        # Mock failed response
        mock_get.side_effect = Exception("API error")
        
        # Test listing models
        result = list_models()
        
        # Verify result
        self.assertEqual(result, [])  # Should return empty list on error
        mock_get.assert_called_once()
        
    @pytest.mark.safe
    @patch('qcmd_cli.core.command_generator.requests.post')
    def test_fix_command_inline_code(self, mock_post):
        """Test fix_command with inline code format."""
        # Mock successful response with inline code format
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "`ls -la`"}
        mock_post.return_value = mock_response
        
        # Test command fixing
        result = fix_command("ls", "error", DEFAULT_MODEL)
        
        # Verify result
        self.assertEqual(result, "ls -la")
        mock_post.assert_called_once()
        
    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.requests.post')
    @patch('qcmd_cli.core.command_generator.list_models')
    def test_generate_command_fallback_failure(self, mock_list_models, mock_post):
        """Test generate_command when both primary and fallback attempts fail."""
        # Mock list_models to return models including the default
        mock_list_models.return_value = ["model1", DEFAULT_MODEL]
        
        # Mock post to raise timeout for all attempts
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")
        
        # Test command generation
        result = generate_command("list files", model="custom-model")
        
        # Verify result
        self.assertEqual(result, "echo 'Error: Command generation failed due to timeout'")
        self.assertEqual(mock_post.call_count, 4)  # 3 attempts + 1 fallback
        
    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.requests.post')
    @patch('qcmd_cli.core.command_generator.list_models')
    def test_generate_command_fallback_success_after_timeout(self, mock_list_models, mock_post):
        """Test generate_command with successful fallback after timeout."""
        # Mock list_models to return models including the default
        mock_list_models.return_value = ["model1", DEFAULT_MODEL]
        
        # Mock post to timeout for primary model but succeed with fallback
        mock_post.side_effect = [
            requests.exceptions.Timeout("Request timed out"),  # First attempt times out
            requests.exceptions.Timeout("Request timed out"),  # Second attempt times out
            requests.exceptions.Timeout("Request timed out"),  # Third attempt times out
            MagicMock(  # Fallback succeeds
                **{
                    'json.return_value': {'response': 'ls -la'},
                    'raise_for_status.return_value': None
                }
            )
        ]
        
        # Test command generation
        result = generate_command("list files", model="custom-model")
        
        # Verify result
        self.assertEqual(result, "ls -la")
        self.assertEqual(mock_post.call_count, 4)  # 3 attempts + 1 fallback
        
        # Verify the last call used the default model
        last_call = mock_post.call_args_list[-1]
        self.assertEqual(last_call[1]["json"]["model"], DEFAULT_MODEL)

    @pytest.mark.safe
    @patch('qcmd_cli.core.command_generator.requests.post')
    def test_fix_command_multiline_code_block(self, mock_post):
        """Test fix_command with multiline code block."""
        # Mock successful response with multiline code block
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "```\nls -la\n```"}
        mock_post.return_value = mock_response
        
        # Test command fixing
        result = fix_command("ls", "error", DEFAULT_MODEL)
        
        # Verify result
        self.assertEqual(result, "ls -la")
        mock_post.assert_called_once()

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.time.sleep')  # Skip actual waiting
    @patch('qcmd_cli.core.command_generator.requests.post')
    @patch('qcmd_cli.core.command_generator.list_models')
    def test_generate_command_fallback_with_retries(self, mock_list_models, mock_post, mock_sleep):
        """Test generate_command with fallback and retries."""
        # Mock list_models to return models including the default
        mock_list_models.return_value = ["model1", DEFAULT_MODEL]
        
        # Create response objects
        error_response = MagicMock()
        error_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        
        success_response = MagicMock()
        success_response.json.return_value = {"response": "ls -la"}
        success_response.raise_for_status.return_value = None
        
        # Mock post to fail with primary model but succeed with fallback
        mock_post.side_effect = [
            error_response,  # First attempt fails
            error_response,  # Second attempt fails
            error_response,  # Third attempt fails
            success_response  # Fallback succeeds
        ]
        
        # Test command generation
        result = generate_command("list files", model="custom-model")
        
        # Verify result
        self.assertEqual(result, "ls -la")
        self.assertEqual(mock_post.call_count, 4)  # 3 attempts + 1 fallback
        
        # Verify the last call used the default model
        last_call = mock_post.call_args_list[-1]
        self.assertEqual(last_call[1]["json"]["model"], DEFAULT_MODEL)

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.time.sleep')  # Skip actual waiting
    @patch('qcmd_cli.core.command_generator.requests.post')
    @patch('qcmd_cli.core.command_generator.list_models')
    def test_generate_command_fallback_failure_with_retries(self, mock_list_models, mock_post, mock_sleep):
        """Test generate_command when fallback also fails after retries."""
        # Mock list_models to return models including the default
        mock_list_models.return_value = ["model1", DEFAULT_MODEL]
        
        # Create error response
        error_response = MagicMock()
        error_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        
        # Mock post to fail for all attempts including fallback
        mock_post.side_effect = [error_response] * 4  # All attempts fail
        
        # Test command generation
        result = generate_command("list files", model="custom-model")
        
        # Verify result
        self.assertEqual(result, "echo 'Error: Command generation failed - API connection issue'")
        self.assertEqual(mock_post.call_count, 4)  # 3 attempts + 1 fallback

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.requests.post')
    @patch('qcmd_cli.core.command_generator.list_models')
    def test_generate_command_fallback_with_empty_response(self, mock_list_models, mock_post):
        """Test generate_command with fallback and empty response."""
        # Mock list_models to return models including the default
        mock_list_models.return_value = ["model1", DEFAULT_MODEL]
        
        # Create response objects for failed attempts
        error_response = MagicMock()
        error_response.raise_for_status.side_effect = requests.exceptions.RequestException("API error")
        
        # Create response object for fallback
        empty_response = MagicMock()
        empty_response.json.return_value = {"response": ""}
        empty_response.raise_for_status.return_value = None
        
        # Mock post to fail with primary model and return empty response with fallback
        mock_post.side_effect = [
            error_response,  # First attempt fails
            error_response,  # Second attempt fails
            error_response,  # Third attempt fails
            empty_response  # Fallback returns empty response
        ]
        
        # Test command generation
        result = generate_command("list files", model="custom-model")
        
        # Verify result
        self.assertEqual(result, "echo 'Error: Command generation failed - API connection issue'")
        self.assertEqual(mock_post.call_count, 4)  # 3 attempts + 1 fallback

    @pytest.mark.safe
    @patch('qcmd_cli.core.command_generator.requests.post')
    def test_fix_command_multiline_with_language(self, mock_post):
        """Test fix_command with multiline code block containing language specifier."""
        # Mock successful response with multiline code block and language specifier
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "```bash\nls -la\n```"}
        mock_post.return_value = mock_response
        
        # Test command fixing
        result = fix_command("ls", "error", DEFAULT_MODEL)
        
        # Verify result - the language specifier should be preserved
        self.assertEqual(result, "bash\nls -la")
        mock_post.assert_called_once()

    @pytest.mark.safe
    @patch('qcmd_cli.core.command_generator.requests.post')
    def test_fix_command_multiline_with_closing_backticks(self, mock_post):
        """Test fix_command with multiline code block and closing backticks on separate line."""
        # Mock successful response with multiline code block and closing backticks on separate line
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "```\nls -la\ncd /tmp\n```"}
        mock_post.return_value = mock_response
        
        # Test command fixing
        result = fix_command("ls", "error", DEFAULT_MODEL)
        
        # Verify result - should include both commands
        self.assertEqual(result, "ls -la\ncd /tmp")
        mock_post.assert_called_once()

    @pytest.mark.safe
    @patch('qcmd_cli.core.command_generator.requests.post')
    def test_fix_command_multiline_with_incomplete_backticks(self, mock_post):
        """Test fix_command with multiline code block and incomplete backticks."""
        # Mock successful response with multiline code block and incomplete backticks
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "```\nls -la\ncd /tmp"}  # No closing backticks
        mock_post.return_value = mock_response
        
        # Test command fixing
        result = fix_command("ls", "error", DEFAULT_MODEL)
        
        # Verify result - should include both commands
        self.assertEqual(result, "ls -la\ncd /tmp")
        mock_post.assert_called_once()

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.requests.post')
    def test_generate_command_multiline_code_block(self, mock_post):
        """Test generate_command with a multiline code block response."""
        # Mock successful response with multiline code block where last line is exactly ```
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "```\nls -la\ngrep 'pattern'\n```"}
        mock_post.return_value = mock_response

        # Test command generation
        result = generate_command("list files and search", DEFAULT_MODEL)

        # Verify result
        self.assertEqual(result, "ls -la\ngrep 'pattern'")

        # Test with a different format where the last line is exactly ```
        mock_response.json.return_value = {"response": "```\nls -la\n```"}
        result = generate_command("list files", DEFAULT_MODEL)
        self.assertEqual(result, "ls -la")

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.requests.post')
    @patch('qcmd_cli.core.command_generator.list_models')
    def test_generate_command_model_unavailable(self, mock_list_models, mock_post):
        """Test generate_command when requested model is unavailable."""
        from qcmd_cli.core.command_generator import generate_command
        
        # Setup mocks
        mock_list_models.return_value = ["gpt-3.5-turbo"]  # Only gpt-3.5-turbo is available
        mock_post.return_value.json.return_value = {"choices": [{"text": "ls -la"}]}
        
        # Test that the function raises ModelUnavailableError for unavailable model
        with self.assertRaises(ModelUnavailableError) as context:
            generate_command("list files", model="gpt-4")
        
        # Verify error message
        self.assertIn("Model 'gpt-4' is not available", str(context.exception))
        
        # Verify API was not called
        mock_post.assert_not_called()
        
        # Test that the function works with available model
        command = generate_command("list files", model="gpt-3.5-turbo")
        self.assertEqual(command, "ls -la")
        mock_post.assert_called_once()

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.requests.post')
    @patch('qcmd_cli.core.command_generator.list_models')
    def test_generate_command_validation_errors(self, mock_list_models, mock_post):
        """Test generate_command with various validation errors."""
        # Mock successful API response
        mock_list_models.return_value = [DEFAULT_MODEL]
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": ""}  # Empty command
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Test empty command validation
        with self.assertRaises(CommandValidationError) as context:
            generate_command("list files")
        self.assertIn("Empty command generated", str(context.exception))
        
        # Test command too long validation
        mock_response.json.return_value = {"response": "a" * 1001}  # Command too long
        with self.assertRaises(CommandValidationError) as context:
            generate_command("list files")
        self.assertIn("Generated command is too long", str(context.exception))

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.requests.post')
    @patch('qcmd_cli.core.command_generator.list_models')
    def test_generate_command_api_response_error(self, mock_list_models, mock_post):
        """Test generate_command with API response errors."""
        mock_list_models.return_value = [DEFAULT_MODEL]
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Invalid response format"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        with self.assertRaises(APIResponseError) as context:
            generate_command("list files")
        self.assertIn("Invalid response format", str(context.exception))

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.requests.post')
    @patch('qcmd_cli.core.command_generator.list_models')
    def test_generate_command_api_errors(self, mock_list_models, mock_post):
        """Test generate_command with different API errors."""
        mock_list_models.return_value = [DEFAULT_MODEL]
        
        # Test rate limit error
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response
        
        with self.assertRaises(APIRateLimitError) as context:
            generate_command("list files")
        self.assertIn("API rate limit exceeded", str(context.exception))

    @pytest.mark.process
    def test_get_fallback_command(self):
        """Test the fallback command generation."""
        from qcmd_cli.core.command_generator import _get_fallback_command
        
        # Test ls command fallbacks
        self.assertEqual(
            _get_fallback_command("ls /root", "permission denied"),
            "ls -la /root"
        )
        
        # Test cat command fallbacks
        self.assertEqual(
            _get_fallback_command("cat /etc/shadow", "permission denied"),
            "less /etc/shadow"
        )
        
        # Test rm command fallbacks
        self.assertEqual(
            _get_fallback_command("rm non_empty_dir", "directory not empty"),
            "rm -rf non_empty_dir"
        )
        
        # Test no fallback available
        self.assertIsNone(
            _get_fallback_command("unknown_command", "error")
        )

    @pytest.mark.process
    def test_suggest_command_correction(self):
        """Test command correction suggestions."""
        from qcmd_cli.core.command_generator import _suggest_command_correction
        
        # Test git command corrections
        self.assertEqual(
            _suggest_command_correction("git status", "not a git repository"),
            "git init status"
        )
        
        # Test docker command corrections
        self.assertEqual(
            _suggest_command_correction("docker ps", "permission denied"),
            "sudo docker ps"
        )
        
        # Test python command corrections
        self.assertEqual(
            _suggest_command_correction("python script.py", "command not found"),
            "python3 script.py"
        )
        
        # Test no correction available
        self.assertIsNone(
            _suggest_command_correction("unknown_command", "error")
        )

    @pytest.mark.process
    def test_get_retry_strategy(self):
        """Test retry strategy determination."""
        from qcmd_cli.core.command_generator import (
            _get_retry_strategy, APITimeoutError,
            APIConnectionError, APIRateLimitError
        )
        
        # Test timeout error strategy
        max_retries, base_delay = _get_retry_strategy(APITimeoutError())
        self.assertEqual(max_retries, 3)
        self.assertEqual(base_delay, 1.0)
        
        # Test connection error strategy
        max_retries, base_delay = _get_retry_strategy(APIConnectionError())
        self.assertEqual(max_retries, 5)
        self.assertEqual(base_delay, 2.0)
        
        # Test rate limit error strategy
        max_retries, base_delay = _get_retry_strategy(APIRateLimitError())
        self.assertEqual(max_retries, 2)
        self.assertEqual(base_delay, 5.0)
        
        # Test default strategy
        max_retries, base_delay = _get_retry_strategy(Exception())
        self.assertEqual(max_retries, 3)
        self.assertEqual(base_delay, 1.5)

    @pytest.mark.process
    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    def test_handle_command_failure(self, mock_popen):
        """Test command failure handling with recovery."""
        from qcmd_cli.core.command_generator import _handle_command_failure
        
        # Test successful fallback
        success, new_command, message = _handle_command_failure(
            "ls /root",
            "permission denied"
        )
        self.assertTrue(success)
        self.assertEqual(new_command, "ls -la /root")
        self.assertIn("Trying fallback command", message)
        
        # Test successful correction
        success, new_command, message = _handle_command_failure(
            "git status",
            "not a git repository"
        )
        self.assertTrue(success)
        self.assertEqual(new_command, "git init status")
        self.assertIn("Suggested correction", message)
        
        # Test no recovery available
        success, new_command, message = _handle_command_failure(
            "unknown_command",
            "error"
        )
        self.assertFalse(success)
        self.assertIsNone(new_command)
        self.assertIn("Command failed", message)


if __name__ == '__main__':
    unittest.main() 