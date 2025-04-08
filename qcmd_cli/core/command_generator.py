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
from typing import List, Optional, Dict, Tuple, Any

from ..ui.display import Colors
from ..config.settings import DEFAULT_MODEL

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

def generate_command(prompt: str, model: str = DEFAULT_MODEL, temperature: float = 0.2) -> str:
    """
    Generate a shell command from a natural language description.
    
    Args:
        prompt: The natural language description of what command to generate
        model: The model to use for generation
        temperature: Temperature for generation
        
    Returns:
        The generated command as a string
    """
    system_prompt = """You are a command-line expert. Generate a shell command based on the user's request.
Reply with ONLY the command, nothing else - no explanations or markdown."""

    formatted_prompt = f"""Generate a shell command for this request: "{prompt}"

Output only the exact command with no introduction, explanation, or markdown formatting."""
    
    # Get available models for fallback
    available_models = []
    try:
        available_models = list_models()
    except:
        pass
        
    # Try with the specified model first
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            # Prepare the request payload
            payload = {
                "model": model,
                "prompt": formatted_prompt,
                "system": system_prompt,
                "stream": False,
                "temperature": temperature,
            }
            
            if attempt > 0:
                print(f"{Colors.YELLOW}Retry attempt {attempt+1}/{max_retries}...{Colors.END}")
            else:
                print(f"{Colors.BLUE}Generating command with {Colors.BOLD}{model}{Colors.END}{Colors.BLUE}...{Colors.END}")
            
            # Make the API request with timeout
            response = requests.post(f"{OLLAMA_API}/generate", json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            result = response.json()
            
            # Extract the command from the response
            command = result.get("response", "").strip()
            
            # Clean up the command (remove any markdown formatting)
            if command.startswith("```") and "\n" in command:
                # Handle multiline code blocks
                lines = command.split("\n")
                command = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            elif command.startswith("```") and command.endswith("```"):
                # Handle single line code blocks with triple backticks
                command = command[3:-3].strip()
            elif command.startswith("`") and command.endswith("`"):
                # Handle inline code with single backticks
                command = command[1:-1].strip()
                
            return command
                
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                print(f"{Colors.YELLOW}Request timed out. Retrying in {retry_delay} seconds...{Colors.END}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                print(f"{Colors.RED}Error: Request to Ollama API timed out after {REQUEST_TIMEOUT} seconds.{Colors.END}")
                
                # Try fallback if the original model isn't available
                if available_models and model != DEFAULT_MODEL and DEFAULT_MODEL in available_models:
                    print(f"{Colors.YELLOW}Trying with fallback model {DEFAULT_MODEL}...{Colors.END}")
                    try:
                        # Use the default model as fallback
                        payload["model"] = DEFAULT_MODEL
                        response = requests.post(f"{OLLAMA_API}/generate", json=payload, timeout=REQUEST_TIMEOUT)
                        response.raise_for_status()
                        result = response.json()
                        command = result.get("response", "").strip()
                        if command:
                            print(f"{Colors.GREEN}Successfully generated command with fallback model.{Colors.END}")
                            return command
                    except:
                        # Fallback failed as well
                        pass
                        
                print(f"{Colors.YELLOW}Please check if Ollama is running and responsive.{Colors.END}")
                return "echo 'Error: Command generation failed due to timeout'"
                
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                print(f"{Colors.YELLOW}Connection error. Retrying in {retry_delay} seconds...{Colors.END}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                print(f"{Colors.RED}Error: Could not connect to Ollama API after {max_retries} attempts.{Colors.END}")
                print(f"{Colors.YELLOW}Make sure Ollama is running with 'ollama serve'{Colors.END}", file=sys.stderr)
                return "echo 'Error: Command generation failed - API connection issue'"
                
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                print(f"{Colors.YELLOW}Request error: {e}. Retrying in {retry_delay} seconds...{Colors.END}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                print(f"{Colors.RED}Error connecting to Ollama API: {e}{Colors.END}", file=sys.stderr)
                
                # Try fallback if the original model isn't available
                if available_models and model != DEFAULT_MODEL and DEFAULT_MODEL in available_models:
                    print(f"{Colors.YELLOW}Trying with fallback model {DEFAULT_MODEL}...{Colors.END}")
                    try:
                        # Use the default model as fallback
                        payload["model"] = DEFAULT_MODEL
                        response = requests.post(f"{OLLAMA_API}/generate", json=payload, timeout=REQUEST_TIMEOUT)
                        response.raise_for_status()
                        result = response.json()
                        command = result.get("response", "").strip()
                        if command:
                            print(f"{Colors.GREEN}Successfully generated command with fallback model.{Colors.END}")
                            return command
                    except:
                        # Fallback failed as well
                        pass
                        
                print(f"{Colors.YELLOW}Make sure Ollama is running with 'ollama serve'{Colors.END}", file=sys.stderr)
                return "echo 'Error: Command generation failed - API connection issue'"
                
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"{Colors.YELLOW}Unexpected error: {e}. Retrying in {retry_delay} seconds...{Colors.END}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                print(f"{Colors.RED}Unexpected error: {e}{Colors.END}", file=sys.stderr)
                return "echo 'Error: Command generation failed'"

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
        if fixed_command.startswith("```") and fixed_command.endswith("```"):
            fixed_command = fixed_command[3:-3].strip()
        elif fixed_command.startswith("`") and fixed_command.endswith("`"):
            fixed_command = fixed_command[1:-1].strip()
            
        return fixed_command
            
    except Exception as e:
        print(f"{Colors.RED}Error generating fixed command: {e}{Colors.END}", file=sys.stderr)
        return command  # Return the original command if we can't fix it

def list_models() -> List[str]:
    """
    List available language models from Ollama.
    
    Returns:
        List of available model names
    """
    try:
        # Make the API request with timeout
        response = requests.get(f"{OLLAMA_API}/tags", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        result = response.json()
        
        # Extract the model names from the response
        models = [model.get("name") for model in result.get("models", [])]
        return models
            
    except Exception as e:
        print(f"{Colors.YELLOW}Error listing models: {e}{Colors.END}", file=sys.stderr)
        return []

def execute_command(command: str, analyze_errors: bool = False, model: str = DEFAULT_MODEL, timeout: int = 60) -> Tuple[int, str]:
    """
    Execute a shell command and capture output.
    
    Args:
        command: The command to execute
        analyze_errors: Whether to analyze errors if the command fails
        model: The model to use for error analysis
        timeout: Maximum execution time in seconds (default: 60)
        
    Returns:
        Tuple of (return_code, output)
    """
    # Check if the command might be dangerous
    if is_dangerous_command(command):
        print(f"{Colors.RED}{Colors.BOLD}Warning: This command appears potentially dangerous!{Colors.END}")
        print(f"{Colors.RED}It might delete important files or cause system damage.{Colors.END}")
        print(f"{Colors.YELLOW}Command: {command}{Colors.END}")
        
        confirmation = input(f"\n{Colors.BOLD}Are you absolutely sure you want to run this? (yes/no): {Colors.END}")
        if confirmation.lower() not in ["yes", "y"]:
            print(f"{Colors.GREEN}Command execution cancelled.{Colors.END}")
            return (1, "Command execution cancelled by user due to safety warning.")
    
    try:
        # Execute the command with timeout and capture output
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Use configurable timeout
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            return_code = process.returncode
            
            # Combine stdout and stderr
            output = stdout
            if stderr:
                if output:
                    output += "\n" + stderr
                else:
                    output = stderr

            # If command failed and analyze_errors is True, get AI analysis
            if return_code != 0 and analyze_errors and stderr:
                print(f"{Colors.YELLOW}Command failed with return code {return_code}.{Colors.END}")
                print(f"{Colors.BLUE}Analyzing error...{Colors.END}")
                error_analysis = analyze_error(stderr, command, model)
                if error_analysis:
                    output += f"\n\n{Colors.BOLD}Error Analysis:{Colors.END}\n{error_analysis}"
                
            return (return_code, output)
            
        except subprocess.TimeoutExpired:
            # Attempt to gracefully terminate the process
            print(f"{Colors.RED}Command execution timed out after {timeout} seconds. Terminating...{Colors.END}")
            process.terminate()
            
            try:
                # Give the process 5 seconds to terminate gracefully
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate gracefully
                process.kill()
                print(f"{Colors.RED}Process had to be forcefully terminated.{Colors.END}")
            
            # Collect any output that might have been generated before timeout
            try:
                stdout, stderr = process.communicate(timeout=2)
                partial_output = stdout if stdout else ""
                if stderr:
                    partial_output += "\n" + stderr if partial_output else stderr
                
                timeout_message = f"Command execution timed out after {timeout} seconds."
                if partial_output:
                    timeout_message += f"\n\nPartial output before timeout:\n{partial_output}"
                
                return (1, timeout_message)
            except:
                return (1, f"Command execution timed out after {timeout} seconds.")
            
    except FileNotFoundError:
        error_msg = f"Error: Command not found or executable could not be run."
        print(f"{Colors.RED}{error_msg}{Colors.END}", file=sys.stderr)
        return (127, error_msg)
    except PermissionError:
        error_msg = f"Error: Permission denied when trying to execute command."
        print(f"{Colors.RED}{error_msg}{Colors.END}", file=sys.stderr)
        return (126, error_msg)
    except Exception as e:
        error_msg = f"Error executing command: {str(e)}"
        print(f"{Colors.RED}{error_msg}{Colors.END}", file=sys.stderr)
        return (1, error_msg)

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