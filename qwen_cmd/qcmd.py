#!/usr/bin/env python3
"""
qcmd - A simple command-line tool that generates shell commands using Qwen2.5-Coder via Ollama.
"""

import argparse
import json
import subprocess
import sys
import requests
from typing import Optional, Dict, Any

# Ollama API settings
OLLAMA_API = "http://127.0.0.1:11434/api"
DEFAULT_MODEL = "qwen2.5-coder:0.5b"

def generate_command(prompt: str, model: str = DEFAULT_MODEL, temperature: float = 0.2) -> str:
    """
    Generate a shell command based on a natural language prompt using Ollama.
    
    Args:
        prompt: The natural language description of what command to generate
        model: The Ollama model to use
        temperature: Temperature for generation (higher = more creative)
        
    Returns:
        The generated shell command
    """
    system_prompt = "You are a command-line assistant. Generate a shell command that accomplishes the user's request. Reply with only the command, no explanations or markdown."
    formatted_prompt = f"Generate a shell command that will {prompt}"
    
    try:
        # Prepare the request payload
        payload = {
            "model": model,
            "prompt": formatted_prompt,
            "system": system_prompt,
            "stream": False,
            "temperature": temperature,
            "top_p": 0.9,
        }
        
        # Make the API request
        response = requests.post(f"{OLLAMA_API}/generate", json=payload)
        response.raise_for_status()
        result = response.json()
        
        # Extract the command from the response
        command = result.get("response", "").strip()
        
        # Clean up the command (remove any markdown formatting, etc.)
        if command.startswith("```") and command.endswith("```"):
            command = command[3:-3].strip()
        elif command.startswith("`") and command.endswith("`"):
            command = command[1:-1].strip()
            
        # If the response includes multiple lines, just take the first one
        if "\n" in command:
            command = command.split("\n")[0].strip()
            
        return command
        
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Ollama API: {e}", file=sys.stderr)
        print("Make sure Ollama is running with 'ollama serve'", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error generating command: {e}", file=sys.stderr)
        sys.exit(1)

def list_models() -> None:
    """
    List all available models from Ollama.
    """
    try:
        response = requests.get(f"{OLLAMA_API}/tags")
        response.raise_for_status()
        models = response.json().get("models", [])
        
        if not models:
            print("No models found.")
            return
            
        print("\nAvailable models:")
        for model in models:
            name = model.get("name", "unknown")
            size = model.get("size", 0) // (1024*1024)  # Convert to MB
            modified = model.get("modified", "")
            print(f"  {name:<25} {size:>6} MB   {modified}")
            
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Ollama API: {e}", file=sys.stderr)
        print("Make sure Ollama is running with 'ollama serve'", file=sys.stderr)
        sys.exit(1)

def execute_command(command: str) -> None:
    """
    Execute a shell command.
    
    Args:
        command: The command to execute
    """
    try:
        print(f"\nExecuting: {command}\n")
        result = subprocess.run(command, shell=True, check=False)
        
        if result.returncode != 0:
            print(f"\nCommand exited with status code {result.returncode}")
            
    except Exception as e:
        print(f"Error executing command: {e}", file=sys.stderr)

def main() -> None:
    """
    Main entry point for the script.
    """
    parser = argparse.ArgumentParser(
        description="Generate and execute shell commands using Qwen2.5-Coder via Ollama."
    )
    
    parser.add_argument(
        "prompt",
        nargs="?",
        help="Natural language description of the command you want"
    )
    
    parser.add_argument(
        "--model", "-m",
        default=DEFAULT_MODEL,
        help=f"Model to use (default: {DEFAULT_MODEL})"
    )
    
    parser.add_argument(
        "--list-models", "-l",
        action="store_true",
        help="List available models and exit"
    )
    
    parser.add_argument(
        "--temperature", "-t",
        type=float,
        default=0.2,
        help="Temperature for generation (default: 0.2)"
    )
    
    parser.add_argument(
        "--execute", "-e",
        action="store_true",
        help="Execute the generated command automatically"
    )
    
    args = parser.parse_args()
    
    # List models and exit if requested
    if args.list_models:
        list_models()
        return
        
    # Ensure a prompt is provided
    if not args.prompt:
        parser.print_help()
        print("\nExamples:")
        print("  qcmd.py \"list all files in the current directory\"")
        print("  qcmd.py \"find large log files\" --execute")
        print("  qcmd.py \"restart the nginx service\" --model llama2:7b")
        return
    
    # Generate the command
    print(f"Generating command for: {args.prompt}")
    command = generate_command(args.prompt, args.model, args.temperature)
    
    # Display the generated command
    print(f"\nGenerated Command: {command}")
    
    # Execute the command if requested
    if args.execute:
        execute_command(command)
    else:
        # Ask for confirmation
        response = input("\nDo you want to execute this command? (y/n): ").lower()
        if response in ["y", "yes"]:
            execute_command(command)
        else:
            print("Command not executed.")

if __name__ == "__main__":
    main() 