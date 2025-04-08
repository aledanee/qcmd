#!/usr/bin/env python3
"""
Command generation functionality for QCMD.
"""
import os
import json
import time
import requests
import sys
import subprocess
import shlex
import logging
from typing import List, Optional, Dict, Tuple, Any, Union
import platform
import click
import signal

from ..ui.display import Colors
from ..config.settings import DEFAULT_MODEL

# Configure logging
log_dir = os.path.join(os.path.expanduser('~'), '.qcmd')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, 'qcmd.log'))
    ]
)
logger = logging.getLogger(__name__)

# Custom exceptions
class CommandGenerationError(Exception):
    """Base exception for command generation errors."""
    pass

class APITimeoutError(CommandGenerationError):
    """Exception raised when API request times out."""
    pass

class APIConnectionError(CommandGenerationError):
    """Exception raised when API connection fails."""
    pass

class CommandExecutionError(CommandGenerationError):
    """Exception raised when command execution fails."""
    pass

class DangerousCommandError(CommandGenerationError):
    """Exception raised when a potentially dangerous command is detected."""
    pass

class APIResponseError(CommandGenerationError):
    """Exception raised when API returns an invalid response."""
    pass

class ModelUnavailableError(CommandGenerationError):
    """Exception raised when the requested model is not available."""
    pass

class CommandValidationError(CommandGenerationError):
    """Exception raised when a generated command fails validation."""
    pass

class ProcessTimeoutError(CommandExecutionError):
    """Exception raised when a process times out."""
    pass

class ProcessError(CommandExecutionError):
    """Exception raised when a process fails with a non-zero exit code."""
    pass

class ProcessCreationError(CommandExecutionError):
    """Exception raised when process creation fails."""
    pass

class CommandOutputError(CommandExecutionError):
    """Exception raised when there are issues with command output."""
    pass

class APIError(CommandGenerationError):
    """Base exception for API-related errors."""
    pass

class APIRateLimitError(APIError):
    """Exception raised when API rate limit is exceeded."""
    pass

class APIAuthenticationError(APIError):
    """Exception raised when API authentication fails."""
    pass

# Ollama API settings
OLLAMA_API = "http://127.0.0.1:11434/api"
REQUEST_TIMEOUT = 30  # Timeout for API requests in seconds

# Additional dangerous patterns for improved detection
DANGEROUS_PATTERNS = [
    # File system operations
    "rm -rf", "rm -r /", "rm -f /", "rmdir /", "shred -uz", 
    "mkfs", "dd if=/dev/zero", "format", "fdisk", "mkswap",
    # Disk operations
    "> /dev/sd", "of=/dev/sd", "dd of=/dev", 
    # Network-dangerous
    ":(){ :|:& };:", ":(){:|:&};:", "fork bomb", "while true", "dd if=/dev/random of=/dev/port",
    # Permission changes
    "chmod -R 777 /", "chmod 777 /", "chown -R", "chmod 000", 
    # File moves/redirections
    "mv /* /dev/null", "> /dev/null", "2>&1",
    # System commands
    "halt", "shutdown", "poweroff", "reboot", "init 0", "init 6",
    # User management
    "userdel -r root", "passwd root", "deluser --remove-home"
]

def _handle_api_error(error: Exception, attempt: int, max_retries: int, retry_delay: int) -> Union[str, None]:
    """
    Handle API errors and determine if retry is possible.
    
    Args:
        error: The exception that occurred
        attempt: Current attempt number
        max_retries: Maximum number of retries
        retry_delay: Current retry delay in seconds
        
    Returns:
        Error message if no more retries, None if retry is possible
        
    Raises:
        APITimeoutError: If request times out after all retries
        APIConnectionError: If connection fails after all retries
        APIResponseError: If API returns an invalid response
        CommandGenerationError: For other API-related errors
    """
    if attempt < max_retries - 1:
        logger.warning(f"API error: {str(error)}. Retrying in {retry_delay} seconds...")
        time.sleep(retry_delay)
        return None
    
    if isinstance(error, requests.exceptions.Timeout):
        error_msg = f"API request timed out after {REQUEST_TIMEOUT} seconds"
        logger.error(error_msg)
        raise APITimeoutError(error_msg)
    elif isinstance(error, requests.exceptions.ConnectionError):
        error_msg = "Could not connect to Ollama API. Please ensure Ollama is running."
        logger.error(error_msg)
        raise APIConnectionError(error_msg)
    elif isinstance(error, requests.exceptions.HTTPError):
        error_msg = f"API returned HTTP error: {str(error)}"
        logger.error(error_msg)
        raise APIResponseError(error_msg)
    else:
        error_msg = f"Unexpected API error: {str(error)}"
        logger.error(error_msg)
        raise CommandGenerationError(error_msg)

def _clean_markdown_formatting(command: str) -> str:
    """Clean up markdown formatting from the command string."""
    if not command:
        return ""

    # Remove leading/trailing whitespace
    command = command.strip()

    # Handle triple backticks
    if command.startswith("```") and command.endswith("```"):
        command = command[3:-3].strip()
        # If there's a language specifier after the opening backticks, remove it
        if command.startswith("bash") or command.startswith("sh"):
            command = command[4:].strip()

    # Handle single backticks
    if command.startswith("`") and command.endswith("`"):
        command = command[1:-1].strip()

    return command

def generate_command(prompt, model=DEFAULT_MODEL):
    """Generate a shell command from a natural language prompt."""
    max_retries = 3
    retry_count = 0
    last_error = None
    base_timeout = 30

    while retry_count < max_retries:
        current_timeout = base_timeout * (2 ** retry_count)
        try:
            # Check if model is available
            available_models = list_models()
            if model not in available_models:
                raise ModelUnavailableError(f"Model '{model}' is not available")

            url = f"{OLLAMA_API}/generate"
            data = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }

            try:
                response = requests.post(url, json=data, stream=True, timeout=current_timeout)
                response.raise_for_status()
                result = response.json()
                command = result.get("response", "").strip()

                if not command:
                    raise CommandGenerationError("Empty command generated")

                return command

            except requests.exceptions.Timeout as e:
                # Handle timeout specifically
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(2 ** retry_count)  # Exponential backoff
                    continue
                error_msg = f"API request timed out after {retry_count} attempts"
                logger.error(error_msg)
                last_error = APITimeoutError(error_msg)
                raise last_error from e
            except requests.exceptions.RequestException as e:
                # Handle other request errors
                error_msg = f"API request failed: {str(e)}"
                logger.error(error_msg)
                raise CommandGenerationError(error_msg) from e

        except Exception as e:
            if isinstance(e, APITimeoutError):
                raise e
            error_msg = f"Command generation failed: {str(e)}"
            logger.error(error_msg)
            raise CommandGenerationError(error_msg) from e

    # If we get here, we've exhausted all retries
    raise last_error

def analyze_error(error_output: str, command: str, model: str = DEFAULT_MODEL) -> str:
    """
    Analyze command execution error using AI.
    
    Args:
        error_output: The error message from the command execution
        command: The command that was executed
        model: The Ollama model to use
        
    Returns:
        Analysis and suggested fix for the error
    """
    system_prompt = """You are a command-line expert. Analyze the error message from a failed shell command and provide:
1. A brief explanation of what went wrong
2. A specific suggestion to fix the issue
3. A corrected command that would work

Be concise and direct."""

    formatted_prompt = f"""The following command failed:
```
{command}
```

With this error output:
```
{error_output}
```

What went wrong and how can I fix it? Provide a brief analysis and a corrected command."""

    try:
        print(f"{Colors.BLUE}Analyzing error with {Colors.BOLD}{model}{Colors.END}{Colors.BLUE}...{Colors.END}")
        
        # Prepare the request payload
        payload = {
            "model": model,
            "prompt": formatted_prompt,
            "system": system_prompt,
            "stream": False,
            "temperature": 0.2,  # Lower temperature for more deterministic results
        }
        
        # Make the API request with timeout
        response = requests.post(f"{OLLAMA_API}/generate", json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        result = response.json()
        
        # Extract the analysis from the response
        analysis = result.get("response", "").strip()
        
        return analysis
            
    except Exception as e:
        print(f"{Colors.RED}Error analyzing error: {e}{Colors.END}", file=sys.stderr)
        return f"Could not analyze error due to API issue: {e}"

def fix_command(command: str, error_output: str, model: str = DEFAULT_MODEL) -> str:
    """
    Generate a fixed version of a failed command.
    
    Args:
        command: The original command that failed
        error_output: The error message from the failed command
        model: The Ollama model to use
        
    Returns:
        A fixed command that should work
    """
    system_prompt = """You are a command-line expert. Your task is to fix a failed shell command.
Reply with ONLY the fixed command, nothing else - no explanations or markdown."""

    formatted_prompt = f"""The following command failed:
```
{command}
```

With this error output:
```
{error_output}
```

Generate a fixed version of the command that would work correctly.
Output only the exact fixed command with no introduction, explanation, or markdown formatting."""

    try:
        print(f"{Colors.BLUE}Generating fixed command with {Colors.BOLD}{model}{Colors.END}{Colors.BLUE}...{Colors.END}")
        
        # Prepare the request payload
        payload = {
            "model": model,
            "prompt": formatted_prompt,
            "system": system_prompt,
            "stream": False,
            "temperature": 0.2,  # Lower temperature for more deterministic results
        }
        
        # Make the API request with timeout
        response = requests.post(f"{OLLAMA_API}/generate", json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        result = response.json()
        
        # Extract the fixed command from the response
        fixed_command = result.get("response", "").strip()
        
        # Clean up the command (remove any markdown formatting)
        if fixed_command.startswith("```"):
            # Handle multiline code blocks
            lines = fixed_command.split("\n")
            if len(lines) > 1:
                # Remove the opening backticks and any language specifier
                first_line = lines[0].strip()
                language = first_line[3:].strip() if len(first_line) > 3 else ""
                lines = lines[1:]
                # Remove closing backticks if present
                if lines[-1].strip() == "```":
                    lines = lines[:-1]
                fixed_command = (language + "\n" if language else "") + "\n".join(lines).strip()
            else:
                # Handle single line code blocks with triple backticks
                fixed_command = fixed_command[3:-3].strip() if fixed_command.endswith("```") else fixed_command[3:].strip()
        elif fixed_command.startswith("`") and fixed_command.endswith("`"):
            # Handle inline code with single backticks
            fixed_command = fixed_command[1:-1].strip()
            
        return fixed_command
            
    except Exception as e:
        print(f"{Colors.RED}Error generating fixed command: {e}{Colors.END}", file=sys.stderr)
        return command  # Return the original command if we can't fix it

def list_models() -> List[str]:
    """
    List available models from the Ollama API.
    
    Returns:
        List[str]: List of available model names
        
    Raises:
        APIConnectionError: If connection to Ollama API fails
        APITimeoutError: If request times out
        APIResponseError: If API returns an invalid response
        ModelUnavailableError: If no models are available
    """
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{OLLAMA_API}/tags", timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            if not isinstance(data, dict):
                raise APIResponseError("Invalid API response format: not a dictionary")
            
            if "models" not in data:
                raise APIResponseError("Invalid API response format: 'models' key missing")
                
            models = [model["name"] for model in data["models"]]
            if not models:
                raise ModelUnavailableError("No models available")
                
            return models
            
        except requests.exceptions.ConnectionError as e:
            if attempt == max_retries - 1:
                logger.error(f"Error listing models: {str(e)}")
                raise APIConnectionError(f"Could not connect to Ollama API: {str(e)}")
            time.sleep(retry_delay)
            
        except requests.exceptions.Timeout as e:
            if attempt == max_retries - 1:
                logger.error(f"Timeout listing models: {str(e)}")
                raise APITimeoutError(f"API request timed out: {str(e)}")
            time.sleep(retry_delay)
            
        except requests.exceptions.HTTPError as e:
            if attempt == max_retries - 1:
                logger.error(f"HTTP error listing models: {str(e)}")
                raise APIResponseError(f"API returned HTTP error: {str(e)}")
            time.sleep(retry_delay)
            
        except json.JSONDecodeError as e:
            if attempt == max_retries - 1:
                logger.error(f"Invalid JSON response: {str(e)}")
                raise APIResponseError(f"Invalid JSON response: {str(e)}")
            time.sleep(retry_delay)
            
        except ModelUnavailableError:
            # Re-raise ModelUnavailableError without retrying
            raise
            
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Unexpected error listing models: {str(e)}")
                raise APIResponseError(f"Unexpected error listing models: {str(e)}")
            time.sleep(retry_delay)
    
    raise APIResponseError("Maximum retries exceeded")

def _handle_process_error(error: Exception, command: str) -> Tuple[int, str]:
    """
    Handle process-related errors during command execution.
    
    Args:
        error: The exception that occurred
        command: The command that failed
        
    Returns:
        Tuple of (return_code, error_message)
        
    Raises:
        ProcessTimeoutError: If process times out
        ProcessError: If process fails with non-zero exit code
        ProcessCreationError: If process creation fails
        CommandOutputError: If there are issues with command output
    """
    if isinstance(error, subprocess.TimeoutExpired):
        logger.error(f"Command execution timed out: {command}")
        raise ProcessTimeoutError(f"Command execution timed out after 60 seconds")
    elif isinstance(error, subprocess.CalledProcessError):
        logger.error(f"Command failed with return code {error.returncode}: {command}")
        raise ProcessError(f"Command failed with return code {error.returncode}")
    elif isinstance(error, subprocess.SubprocessError):
        logger.error(f"Process creation failed: {error}")
        raise ProcessCreationError(f"Process creation failed: {error}")
    else:
        logger.error(f"Unexpected process error: {error}")
        raise CommandExecutionError(f"Unexpected process error: {error}")

def _handle_api_response(response: requests.Response) -> None:
    """
    Handle API response and raise appropriate exceptions.
    
    Args:
        response: The API response to handle
        
    Raises:
        APIRateLimitError: If rate limit is exceeded
        APIAuthenticationError: If authentication fails
        APIResponseError: If response is invalid
    """
    if response.status_code == 429:
        logger.error("API rate limit exceeded")
        raise APIRateLimitError("API rate limit exceeded")
    elif response.status_code == 401:
        logger.error("API authentication failed")
        raise APIAuthenticationError("API authentication failed")
    elif not response.ok:
        logger.error(f"API returned error status: {response.status_code}")
        raise APIResponseError(f"API returned error status: {response.status_code}")
    
    try:
        response.json()
    except ValueError:
        logger.error("Invalid JSON response from API")
        raise APIResponseError("Invalid JSON response from API")

def _validate_command_output(output: str) -> None:
    """
    Validate command output for potential issues.
    
    Args:
        output: The command output to validate
        
    Raises:
        CommandOutputError: If output validation fails
    """
    if not output:
        return
    
    # Check for common error patterns in output
    error_patterns = [
        "command not found",
        "permission denied",
        "no such file or directory",
        "invalid option",
        "syntax error"
    ]
    
    for pattern in error_patterns:
        if pattern in output.lower():
            logger.warning(f"Command output contains error pattern: {pattern}")
            raise CommandOutputError(f"Command output indicates error: {pattern}")

def _get_fallback_command(command: str, error: str) -> Optional[str]:
    """
    Generate a fallback command based on the original command and error message.
    
    Args:
        command: The original command that failed
        error: The error message from the failed command
        
    Returns:
        Optional[str]: A fallback command or None if no fallback is available
    """
    # Common command fallbacks
    fallbacks = {
        'ls': {
            'permission denied': 'ls -la',
            'command not found': 'dir' if platform.system() == 'Windows' else 'ls -la'
        },
        'cat': {
            'no such file': 'less',
            'permission denied': 'less'
        },
        'rm': {
            'permission denied': 'rm -f',
            'directory not empty': 'rm -rf'
        }
    }
    
    # Extract base command
    base_cmd = command.split()[0] if command else ''
    
    # Check for fallback based on error message
    if base_cmd in fallbacks:
        for error_pattern, fallback in fallbacks[base_cmd].items():
            if error_pattern.lower() in error.lower():
                return fallback + command[len(base_cmd):]
    
    return None

def _suggest_command_correction(command: str, error: str) -> Optional[str]:
    """
    Suggest a corrected version of a command based on common mistakes.
    
    Args:
        command: The original command that failed
        error: The error message from the failed command
        
    Returns:
        Optional[str]: A suggested correction or None if no suggestion is available
    """
    # Common command corrections
    corrections = {
        'git': {
            'not a git repository': 'git init',
            'command not found': 'git --version'
        },
        'docker': {
            'command not found': 'docker --version',
            'permission denied': 'sudo docker'
        },
        'python': {
            'command not found': 'python3',
            'no such file': 'python3'
        }
    }
    
    # Extract base command
    base_cmd = command.split()[0] if command else ''
    
    # Check for correction based on error message
    if base_cmd in corrections:
        for error_pattern, correction in corrections[base_cmd].items():
            if error_pattern.lower() in error.lower():
                return correction + command[len(base_cmd):]
    
    return None

def _get_retry_strategy(error: Exception) -> Tuple[int, float]:
    """
    Determine retry strategy based on error type.
    
    Args:
        error: The exception that occurred
        
    Returns:
        Tuple[int, float]: (max_retries, base_delay)
    """
    if isinstance(error, APITimeoutError):
        return 3, 1.0  # Fewer retries, shorter delay for timeouts
    elif isinstance(error, APIConnectionError):
        return 5, 2.0  # More retries, longer delay for connection issues
    elif isinstance(error, APIRateLimitError):
        return 2, 5.0  # Few retries, long delay for rate limits
    else:
        return 3, 1.5  # Default strategy

def _handle_command_failure(command: str, error_msg: str) -> Tuple[bool, Optional[str], str]:
    """
    Handle command failure and attempt recovery.
    
    Args:
        command: The command that failed
        error_msg: The error message from the failed command
        
    Returns:
        Tuple of:
        - bool: Whether recovery is possible
        - Optional[str]: The new command to try (if recovery is possible)
        - str: A message describing the recovery attempt
    """
    # Try to get a fallback command first
    fallback = _get_fallback_command(command, error_msg)
    if fallback:
        return True, fallback, f"Trying fallback command: {fallback}"
    
    # If no fallback, try to get a command correction
    correction = _suggest_command_correction(command, error_msg)
    if correction:
        return True, correction, f"Suggested correction: {correction}"
    
    # No recovery options available
    return False, None, f"Command failed: {error_msg}"

def execute_command(command, timeout=30, max_retries=3):
    """Execute a shell command with timeout and retry logic."""
    retries = 0
    while retries < max_retries:
        try:
            # Start the process
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            try:
                # Wait for the process with timeout
                stdout, stderr = process.communicate(timeout=timeout)
                
                # Check return code
                if process.returncode != 0:
                    error_msg = f"Command failed with return code {process.returncode}. Error: {stderr}"
                    logger.error(error_msg)
                    retries += 1
                    if retries >= max_retries:
                        raise CommandExecutionError(f"Command failed after {max_retries} attempts: {error_msg}")
                    continue
                
                return stdout.strip()
                
            except subprocess.TimeoutExpired:
                # Clean up the process
                try:
                    process.terminate()
                    process.wait(timeout=5)  # Give it 5 seconds to terminate gracefully
                except subprocess.TimeoutExpired:
                    process.kill()  # Force kill if it doesn't terminate
                
                error_msg = f"Command timed out after {timeout} seconds"
                logger.error(error_msg)
                retries += 1
                if retries >= max_retries:
                    raise CommandExecutionError(f"Command failed after {max_retries} attempts: {error_msg}")
                continue
                
        except subprocess.SubprocessError as e:
            error_msg = f"Failed to create process: {str(e)}"
            logger.error(error_msg)
            retries += 1
            if retries >= max_retries:
                raise CommandExecutionError(f"Command failed after {max_retries} attempts: {error_msg}")
            continue

    raise CommandExecutionError(f"Command failed after {max_retries} attempts: {error_msg}")

def is_dangerous_command(command: str) -> bool:
    """
    Check if a command appears to be potentially dangerous.
    
    Args:
        command: The command to check
        
    Returns:
        True if the command appears potentially dangerous
    """
    command_lower = command.lower()
    
    # Check for common dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in command_lower:
            return True
            
    # Check for commands that might delete or overwrite system files
    if ("rm" in command_lower) and ("/" in command_lower) and not ("./") in command_lower:
        return True
        
    # Check for sudo or doas with potentially risky commands
    if ("sudo" in command_lower or "doas" in command_lower) and any(risky in command_lower for risky in [
        "rm", "mkfs", "dd", "fdisk", "chmod", "chown", "mv"
    ]):
        return True
        
    return False 

def _validate_command(command: str) -> None:
    """
    Validate a generated command.
    
    Args:
        command: The command to validate
        
    Raises:
        CommandValidationError: If the command fails validation
    """
    if not command:
        raise CommandValidationError("Empty command generated")
    
    if len(command) > 1000:  # Arbitrary limit to prevent extremely long commands
        raise CommandValidationError("Generated command is too long")
    
    # Check for invalid characters
    invalid_chars = ['\x00', '\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07',
                    '\x08', '\x0b', '\x0c', '\x0e', '\x0f', '\x10', '\x11', '\x12',
                    '\x13', '\x14', '\x15', '\x16', '\x17', '\x18', '\x19', '\x1a',
                    '\x1b', '\x1c', '\x1d', '\x1e', '\x1f', '\x7f']
    for char in invalid_chars:
        if char in command:
            raise CommandValidationError(f"Command contains invalid control character: {repr(char)}")
    
    # Check for potentially dangerous patterns
    if is_dangerous_command(command):
        raise CommandValidationError("Generated command appears to be potentially dangerous")
    
    # Check for common command injection patterns
    injection_patterns = [';', '&&', '||', '|', '>', '<', '`', '$(']
    for pattern in injection_patterns:
        if pattern in command and not command.strip().startswith(pattern):
            raise CommandValidationError(f"Command contains potential command injection pattern: {pattern}")
    
    # Check for basic syntax errors
    try:
        shlex.split(command)
    except ValueError as e:
        raise CommandValidationError(f"Command has invalid syntax: {str(e)}")
    
    # Check for empty or whitespace-only commands after cleaning
    if not command.strip():
        raise CommandValidationError("Command is empty after cleaning whitespace")
    
    # Check for commands that are just comments
    if command.strip().startswith('#'):
        raise CommandValidationError("Command is just a comment")

def _handle_command_execution_error(e: Exception, command: str) -> str:
    """Handle command execution errors with comprehensive context."""
    try:
        # Get environment context
        env = os.environ
        cwd = os.getcwd()
        user = os.getenv('USER', 'unknown')
        shell = os.getenv('SHELL', 'unknown')
        term = os.getenv('TERM', 'unknown')
        lang = os.getenv('LANG', 'unknown')
        path = os.getenv('PATH', 'unknown')
        hostname = os.getenv('HOSTNAME', 'unknown')
        pwd = os.getenv('PWD', 'unknown')
        editor = os.getenv('EDITOR', 'unknown')
        display = os.getenv('DISPLAY', 'unknown')
        ssh_client = os.getenv('SSH_CLIENT', 'unknown')
        ssh_connection = os.getenv('SSH_CONNECTION', 'unknown')
        xdg_session_type = os.getenv('XDG_SESSION_TYPE', 'unknown')
        xdg_session_desktop = os.getenv('XDG_SESSION_DESKTOP', 'unknown')
        term_program = os.getenv('TERM_PROGRAM', 'unknown')
        term_program_version = os.getenv('TERM_PROGRAM_VERSION', 'unknown')
        
        # Get system information
        system_info = platform.uname()
        
        # Format environment context
        env_context = [
            "╭───────────────────────────────────────────────────────────────",
            "│ Environment Context",
            "├───────────────────────────────────────────────────────────────",
            "│ System Information:",
            f"│   OS: {system_info.system} {system_info.release}",
            f"│   Version: {system_info.version}",
            f"│   Machine: {system_info.machine}",
            f"│   Processor: {system_info.processor}",
            "│",
            "│ User Environment:",
            f"│   Hostname: {hostname}",
            f"│   Current Directory: {pwd}",
            f"│   Preferred Editor: {editor}",
            f"│   Terminal Emulator: {term_program} {term_program_version}",
            f"│   Display Server: {display}",
            f"│   Session Type: {xdg_session_type}",
            f"│   Desktop Environment: {xdg_session_desktop}",
            "│",
            "│ Connection Information:",
            f"│   SSH Client: {ssh_client}",
            f"│   SSH Connection: {ssh_connection}",
            "│",
            "│ Environment Variables:",
            f"│   Language: {lang}",
            f"│   PATH: {path}",
            f"│   TERM: {term}",
            "╰───────────────────────────────────────────────────────────────"
        ]
        
        # Format command context
        cmd_context = [
            "╭───────────────────────────────────────────────────────────────",
            "│ Command Context",
            "├───────────────────────────────────────────────────────────────",
            f"│ Full Command: {command}",
            "│",
            "│ Command Parts:",
        ]
        
        # Add each part of the command
        for i, part in enumerate(command.split()):
            cmd_context.append(f"│   {i + 1}. {part}")
        
        cmd_context.extend([
            "│",
            f"│ Command Length: {len(command)} characters",
            "╰───────────────────────────────────────────────────────────────"
        ])
        
        # Format error message
        error_msg = [
            "╭───────────────────────────────────────────────────────────────",
            "│ Error Details",
            "├───────────────────────────────────────────────────────────────"
        ]
        
        if isinstance(e, subprocess.CalledProcessError):
            error_msg.extend([
                f"│ Command failed with exit code {e.returncode}",
                f"│ Output: {e.output.decode('utf-8', errors='replace') if e.output else 'None'}",
                f"│ Error: {e.stderr.decode('utf-8', errors='replace') if e.stderr else 'None'}"
            ])
        elif isinstance(e, subprocess.TimeoutExpired):
            error_msg.extend([
                f"│ Command timed out after {e.timeout} seconds",
                f"│ Output: {e.output.decode('utf-8', errors='replace') if e.output else 'None'}"
            ])
        elif isinstance(e, FileNotFoundError):
            error_msg.extend([
                f"│ Command not found: {e.filename}",
                f"│ PATH: {path}"
            ])
        elif isinstance(e, PermissionError):
            error_msg.extend([
                f"│ Permission denied: {e.filename}",
                f"│ Current User: {user}"
            ])
        else:
            error_msg.append(f"│ {str(e)}")
        
        error_msg.append("╰───────────────────────────────────────────────────────────────")
        
        # Combine all contexts
        return "\n".join(env_context + [""] + cmd_context + [""] + error_msg)
        
    except Exception as context_error:
        logger.error(f"Error generating context: {str(context_error)}")
        return f"Error executing command: {str(e)}" 