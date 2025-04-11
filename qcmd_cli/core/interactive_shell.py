#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Interactive shell module for QCMD.
This module provides a shell-like interface for users to interact with the system.
"""

import os
import sys
import readline
import time
import atexit
import signal
from typing import List, Optional, Tuple
from datetime import datetime

# Import from other modules
from qcmd_cli.config.settings import DEFAULT_MODEL
from qcmd_cli.config.constants import CONFIG_DIR
from qcmd_cli.ui.display import Colors, print_cool_header, clear_screen
from qcmd_cli.core.command_generator import generate_command, is_dangerous_command, list_models, fix_command
from qcmd_cli.utils.history import save_to_history, load_history, show_history
from qcmd_cli.utils.system import execute_command, get_system_status, display_update_status, display_system_status
from qcmd_cli.log_analysis.log_files import handle_log_analysis
from qcmd_cli.log_analysis.analyzer import analyze_log_file
from qcmd_cli.utils.ollama import is_ollama_running

# Setup session tracking
from qcmd_cli.utils.session import create_session, update_session_activity, cleanup_stale_sessions, end_session

class SimpleCompleter:
    """
    Simple command completion for the interactive shell.
    """
    def __init__(self, options):
        self.options = options
        
    def complete(self, text, state):
        """
        Return state'th completion starting with text.
        """
        response = None
        if state == 0:
            # This is the first time for this text, so build a match list
            if text:
                self.matches = [s for s in self.options if s and s.startswith(text)]
            else:
                self.matches = self.options[:]
        
        # Return the state'th item from the match list, if we have that many
        try:
            response = self.matches[state]
        except IndexError:
            return None
            
        return response

def start_interactive_shell(
    auto_mode_enabled: bool = False, 
    current_model: str = DEFAULT_MODEL, 
    current_temperature: float = 0.7, 
    max_attempts: int = 3
) -> None:
    """
    Start an interactive shell for continuous command generation.
    
    Args:
        auto_mode_enabled: Whether to run in auto mode (auto execute and fix commands)
        current_model: Model to use for generation
        current_temperature: Temperature for generation (0.0-1.0)
        max_attempts: Maximum number of fix attempts in auto mode
    """
    # Create config directory if it doesn't exist
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    # History file setup
    history_file = os.path.join(CONFIG_DIR, 'qcmd_history')
    try:
        readline.read_history_file(history_file)
        readline.set_history_length(1000)
    except (FileNotFoundError, PermissionError):
        # If history file doesn't exist or can't be read, just continue
        pass
    atexit.register(readline.write_history_file, history_file)
    
    # Setup session tracking
    session_id = create_session({
        'type': 'interactive_shell',
        'model': current_model,
        'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'auto_mode': auto_mode_enabled,
        'temperature': current_temperature
    })
    
    # Check if Ollama is running
    if not is_ollama_running():
        print(f"\n{Colors.YELLOW}Warning: Ollama API is not running. Commands will not work properly.{Colors.END}")
        print(f"{Colors.YELLOW}Start Ollama with 'ollama serve' and try again.{Colors.END}")
    
    # Display QCMD banner
    clear_screen()
    _display_banner()
    
    # Check for QCMD updates on startup
    display_update_status()
    
    # Welcome message
    print(f"\n{Colors.CYAN}Welcome to the QCMD Interactive Shell!{Colors.END}")
    print(f"Using model: {Colors.GREEN}{current_model}{Colors.END}")
    print(f"Temperature: {Colors.GREEN}{current_temperature}{Colors.END}")
    print(f"Auto mode: {Colors.GREEN}{auto_mode_enabled}{Colors.END}")
    print(f"\nEnter your command descriptions or type {Colors.YELLOW}/help{Colors.END} for more options.")
    print(f"{Colors.YELLOW}Type /exit to quit{Colors.END}")
    
    # Command history for the current session
    session_history = []
    analyze_errors = True
    
    # Cleanup stale sessions on startup
    cleanup_stale_sessions()
    
    # Define a signal handler to gracefully exit
    def signal_handler(sig, frame):
        print(f"\n{Colors.CYAN}Received signal {sig}, exiting...{Colors.END}")
        # End the session when receiving a signal
        try:
            end_session(session_id)
        except Exception:
            pass
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create a timer for periodically updating session activity
        last_activity_update = time.time()
        update_interval = 60  # Update session activity every 60 seconds
        
        # Main interactive loop
        while True:
            try:
                # Update session activity periodically
                current_time = time.time()
                if current_time - last_activity_update > update_interval:
                    update_session_activity(session_id)
                    last_activity_update = current_time
                
                # Get user input
                user_input = input(f"\n{Colors.BOLD}qcmd> {Colors.END}").strip()
                
                # Handle empty input
                if not user_input:
                    continue
                    
                # Save to readline history
                readline.add_history(user_input)
                
                # Handle special commands
                if user_input.lower() in ('/exit', '/quit'):
                    print(f"{Colors.CYAN}Goodbye!{Colors.END}")
                    # End the session when exiting
                    end_session(session_id)
                    break
                    
                elif user_input.lower() == '/help':
                    _show_shell_help()
                    continue
                    
                elif user_input.lower() == '/history':
                    # Show command history
                    if session_history:
                        print(f"\n{Colors.CYAN}Command History (this session):{Colors.END}")
                        for i, (cmd_desc, cmd) in enumerate(session_history, 1):
                            print(f"{Colors.BLUE}{i}.{Colors.END} {cmd_desc}")
                            print(f"   {Colors.GREEN}{cmd}{Colors.END}")
                    else:
                        print(f"{Colors.YELLOW}No commands in this session yet.{Colors.END}")
                    continue
                    
                elif user_input.lower() == '/models':
                    # List available models
                    models = list_models()
                    if models:
                        print(f"\n{Colors.CYAN}Available Models:{Colors.END}")
                        for i, model in enumerate(models, 1):
                            current = " (current)" if model == current_model else ""
                            print(f"{i}. {Colors.GREEN}{model}{Colors.END}{current}")
                    else:
                        print(f"{Colors.YELLOW}No models available or could not connect to Ollama.{Colors.END}")
                    continue
                    
                elif user_input.lower() == '/status':
                    # Show system status
                    print(f"\n{Colors.CYAN}Getting system status...{Colors.END}")
                    display_system_status()
                    continue
                    
                elif user_input.lower() == '/update':
                    # Check for updates
                    display_update_status()
                    continue
                    
                elif user_input.lower().startswith('/model '):
                    # Switch models
                    parts = user_input.split(maxsplit=1)
                    if len(parts) == 2:
                        try:
                            # Check if input is a number (index from listed models)
                            if parts[1].isdigit():
                                idx = int(parts[1]) - 1
                                models = list_models()
                                if 0 <= idx < len(models):
                                    current_model = models[idx]
                                    print(f"Switched to model: {Colors.GREEN}{current_model}{Colors.END}")
                                else:
                                    print(f"{Colors.YELLOW}Invalid model index.{Colors.END}")
                            else:
                                # Direct model name
                                current_model = parts[1]
                                print(f"Switched to model: {Colors.GREEN}{current_model}{Colors.END}")
                        except Exception as e:
                            print(f"{Colors.YELLOW}Error switching models: {e}{Colors.END}")
                    else:
                        print(f"{Colors.YELLOW}Usage: /model <model_name_or_index>{Colors.END}")
                    continue
                    
                elif user_input.lower().startswith('/temperature '):
                    # Set temperature
                    parts = user_input.split(maxsplit=1)
                    if len(parts) == 2:
                        try:
                            temp = float(parts[1])
                            if 0.0 <= temp <= 1.0:
                                current_temperature = temp
                                print(f"Temperature set to: {Colors.GREEN}{current_temperature}{Colors.END}")
                            else:
                                print(f"{Colors.YELLOW}Temperature must be between 0.0 and 1.0{Colors.END}")
                        except ValueError:
                            print(f"{Colors.YELLOW}Invalid temperature value. Use a number between 0.0 and 1.0{Colors.END}")
                    else:
                        print(f"{Colors.YELLOW}Usage: /temperature <value>{Colors.END}")
                    continue
                    
                elif user_input.lower() == '/auto':
                    # Enable auto mode
                    auto_mode_enabled = True
                    print(f"{Colors.GREEN}Auto mode enabled.{Colors.END}")
                    continue
                    
                elif user_input.lower() == '/manual':
                    # Disable auto mode
                    auto_mode_enabled = False
                    print(f"{Colors.GREEN}Auto mode disabled.{Colors.END}")
                    continue
                    
                elif user_input.lower() == '/analyze':
                    # Toggle error analysis
                    analyze_errors = not analyze_errors
                    status = "enabled" if analyze_errors else "disabled"
                    print(f"{Colors.GREEN}Error analysis {status}.{Colors.END}")
                    continue
                    
                elif user_input.lower() == '/logs':
                    # Find and analyze log files
                    handle_log_analysis(current_model)
                    continue
                    
                elif user_input.lower().startswith('/analyze-file '):
                    # Analyze a specific file
                    parts = user_input.split(maxsplit=1)
                    if len(parts) == 2:
                        file_path = os.path.expanduser(parts[1])
                        if os.path.isfile(file_path):
                            analyze_log_file(file_path, current_model)
                        else:
                            print(f"{Colors.YELLOW}File not found: {file_path}{Colors.END}")
                    else:
                        print(f"{Colors.YELLOW}Usage: /analyze-file <file_path>{Colors.END}")
                    continue
                    
                elif user_input.lower().startswith('/monitor '):
                    # Monitor a specific file with AI analysis
                    parts = user_input.split(maxsplit=1)
                    if len(parts) == 2:
                        file_path = os.path.expanduser(parts[1])
                        if os.path.isfile(file_path):
                            analyze_log_file(file_path, current_model, background=True)
                        else:
                            print(f"{Colors.YELLOW}File not found: {file_path}{Colors.END}")
                    else:
                        print(f"{Colors.YELLOW}Usage: /monitor <file_path>{Colors.END}")
                    continue
                    
                elif user_input.lower() == '/execute':
                    # Execute last command
                    if session_history:
                        _, last_cmd = session_history[-1]
                        print(f"\n{Colors.CYAN}Executing:{Colors.END} {Colors.GREEN}{last_cmd}{Colors.END}")
                        
                        # Confirm execution
                        confirm = input(f"Press {Colors.YELLOW}Enter{Colors.END} to execute or Ctrl+C to cancel: ")
                        
                        # Execute the command
                        exit_code, output = execute_command(last_cmd, analyze_errors, current_model)
                        
                        # Display results
                        status = f"{Colors.GREEN}Success{Colors.END}" if exit_code == 0 else f"{Colors.RED}Failed (exit code: {exit_code}){Colors.END}"
                        print(f"\n{Colors.CYAN}Status:{Colors.END} {status}")
                        
                        if analyze_errors and exit_code != 0:
                            _analyze_and_fix_error(last_cmd, output, current_model)
                    else:
                        print(f"{Colors.YELLOW}No commands in history to execute.{Colors.END}")
                    continue
                    
                # Process regular input as a command request
                print(f"\n{Colors.CYAN}Generating command...{Colors.END}")
                
                # Generate the command
                command = generate_command(user_input, current_model, current_temperature)
                
                # Display the generated command
                if command.startswith("Error:"):
                    print(f"{Colors.RED}{command}{Colors.END}")
                    continue
                    
                print(f"{Colors.GREEN}{command}{Colors.END}")
                
                # Check for potentially dangerous commands
                if is_dangerous_command(command):
                    print(f"\n{Colors.RED}WARNING: This command may be potentially dangerous!{Colors.END}")
                    print(f"{Colors.RED}Review it carefully before execution.{Colors.END}")
                    
                # Add to session history
                session_history.append((user_input, command))
                
                # Save to global history
                save_to_history(user_input)
                
                # Handle auto mode
                if auto_mode_enabled:
                    print(f"\n{Colors.CYAN}Auto-executing command...{Colors.END}")
                    
                    # Execute the command
                    exit_code, output = execute_command(command, False, current_model)
                    
                    # Display results
                    status = f"{Colors.GREEN}Success{Colors.END}" if exit_code == 0 else f"{Colors.RED}Failed (exit code: {exit_code}){Colors.END}"
                    print(f"\n{Colors.CYAN}Status:{Colors.END} {status}")
                    
                    # Handle errors in auto mode
                    if exit_code != 0:
                        _auto_fix_and_execute(command, output, current_model, max_attempts)
                else:
                    # Interactive mode with options to execute, edit, or skip
                    print(f"\n{Colors.CYAN}Options:{Colors.END}")
                    print(f"  {Colors.YELLOW}y{Colors.END} - Execute the command")
                    print(f"  {Colors.YELLOW}n{Colors.END} - Skip execution")
                    print(f"  {Colors.YELLOW}e{Colors.END} - Edit command before execution")
                    
                    while True:
                        try:
                            choice = input(f"\n{Colors.BOLD}Enter your choice (y/n/e):{Colors.END} ").strip().lower()
                            
                            if choice == 'y':
                                # Execute the command
                                exit_code, output = execute_command(command, analyze_errors, current_model)
                                
                                # Display results
                                status = f"{Colors.GREEN}Success{Colors.END}" if exit_code == 0 else f"{Colors.RED}Failed (exit code: {exit_code}){Colors.END}"
                                print(f"\n{Colors.CYAN}Status:{Colors.END} {status}")
                                
                                # Handle errors if enabled
                                if analyze_errors and exit_code != 0:
                                    _analyze_and_fix_error(command, output, current_model)
                                break
                                
                            elif choice == 'n':
                                print(f"{Colors.YELLOW}Command execution skipped.{Colors.END}")
                                break
                                
                            elif choice == 'e':
                                print(f"{Colors.CYAN}Edit the command:{Colors.END}")
                                # Display original command for reference
                                print(f"{Colors.GREEN}Original: {command}{Colors.END}")
                                
                                # Allow user to edit
                                try:
                                    # Pre-populate the input with the current command
                                    if 'readline' in sys.modules:
                                        readline.set_startup_hook(lambda: readline.insert_text(command))
                                    
                                    edited_command = input(f"{Colors.BOLD}Edit> {Colors.END}").strip()
                                    
                                    # Reset the startup hook
                                    if 'readline' in sys.modules:
                                        readline.set_startup_hook(None)
                                    
                                    if edited_command:
                                        # Update command
                                        command = edited_command
                                        print(f"\n{Colors.CYAN}Updated command:{Colors.END} {Colors.GREEN}{command}{Colors.END}")
                                        
                                        # Update session history
                                        session_history[-1] = (user_input, command)
                                        
                                        # Ask for execution confirmation
                                        sub_choice = input(f"\n{Colors.BOLD}Execute this command now? (y/n):{Colors.END} ").strip().lower()
                                        if sub_choice == 'y':
                                            # Execute the command
                                            exit_code, output = execute_command(command, analyze_errors, current_model)
                                            
                                            # Display results
                                            status = f"{Colors.GREEN}Success{Colors.END}" if exit_code == 0 else f"{Colors.RED}Failed (exit code: {exit_code}){Colors.END}"
                                            print(f"\n{Colors.CYAN}Status:{Colors.END} {status}")
                                            
                                            # Handle errors if enabled
                                            if analyze_errors and exit_code != 0:
                                                _analyze_and_fix_error(command, output, current_model)
                                    else:
                                        print(f"{Colors.YELLOW}No changes made to the command.{Colors.END}")
                                except KeyboardInterrupt:
                                    print("\nEditing cancelled")
                                finally:
                                    # Reset the startup hook
                                    if 'readline' in sys.modules:
                                        readline.set_startup_hook(None)
                                break
                                
                            else:
                                print(f"{Colors.YELLOW}Invalid choice. Please enter 'y', 'n', or 'e'.{Colors.END}")
                        except KeyboardInterrupt:
                            print("\nOperation cancelled")
                            break
                
                # Update activity after processing a command
                update_session_activity(session_id)
                last_activity_update = time.time()
                
            except KeyboardInterrupt:
                print("\nInterrupted")
                continue
                
            except EOFError:
                print(f"\n{Colors.CYAN}Goodbye!{Colors.END}")
                # End the session when exiting
                end_session(session_id)
                break
                
            except Exception as e:
                print(f"\n{Colors.RED}Error: {str(e)}{Colors.END}")
    finally:
        # End the session when exiting, even if there was an unhandled exception
        end_session(session_id)
        
        # Save history on exit
        try:
            readline.write_history_file(history_file)
        except Exception as e:
            print(f"{Colors.YELLOW}Could not save shell history: {e}{Colors.END}", file=sys.stderr)

def _show_shell_help() -> None:
    """Display help information for the interactive shell."""
    print(f"\n{Colors.CYAN}QCMD Interactive Shell Commands:{Colors.END}")
    print(f"{Colors.YELLOW}/help{Colors.END} - Show this help message")
    print(f"{Colors.YELLOW}/exit{Colors.END}, {Colors.YELLOW}/quit{Colors.END} - Exit the shell")
    print(f"{Colors.YELLOW}/history{Colors.END} - Show command history for this session")
    print(f"{Colors.YELLOW}/models{Colors.END} - List available models")
    print(f"{Colors.YELLOW}/model <n>{Colors.END} - Switch to a different model")
    print(f"{Colors.YELLOW}/status{Colors.END} - Show system status information")
    print(f"{Colors.YELLOW}/update{Colors.END} - Check for QCMD updates")
    print(f"{Colors.YELLOW}/temperature <t>{Colors.END} - Set temperature (0.0-1.0)")
    print(f"{Colors.YELLOW}/auto{Colors.END} - Enable auto mode")
    print(f"{Colors.YELLOW}/manual{Colors.END} - Disable auto mode")
    print(f"{Colors.YELLOW}/analyze{Colors.END} - Toggle error analysis")
    print(f"{Colors.YELLOW}/execute{Colors.END} - Execute last generated command (with confirmation)")
    print(f"{Colors.YELLOW}/logs{Colors.END} - Find and analyze log files")
    print(f"{Colors.YELLOW}/analyze-file <path>{Colors.END} - Analyze a specific file")
    print(f"{Colors.YELLOW}/monitor <path>{Colors.END} - Monitor a file continuously")
    
    print(f"\n{Colors.CYAN}Command Execution Options:{Colors.END}")
    print(f"When a command is generated, you'll be presented with these options:")
    print(f"  {Colors.YELLOW}y{Colors.END} - Execute the generated command")
    print(f"  {Colors.YELLOW}n{Colors.END} - Skip execution of the command")
    print(f"  {Colors.YELLOW}e{Colors.END} - Edit the command before execution")
    
    print(f"\n{Colors.CYAN}Commands:{Colors.END}")
    print("Just type a natural language description of what you want to do.")
    print("Examples:")
    print(f"  {Colors.GREEN}find all log files in /var/log{Colors.END}")
    print(f"  {Colors.GREEN}search for errors in apache logs{Colors.END}")
    print(f"  {Colors.GREEN}show top 10 processes by CPU usage{Colors.END}")

def _analyze_and_fix_error(command: str, output: str, model: str) -> None:
    """
    Analyze and provide a fix for a failed command.
    
    Args:
        command: The failed command
        output: The error output
        model: Model to use for analysis
    """
    from qcmd_cli.core.command_generator import analyze_error, fix_command
    
    print(f"\n{Colors.CYAN}Analyzing error...{Colors.END}")
    analysis = analyze_error(output, command, model)
    print(f"\n{Colors.CYAN}Analysis:{Colors.END}\n{analysis}")
    
    print(f"\n{Colors.CYAN}Suggesting fixed command...{Colors.END}")
    fixed_command = fix_command(command, output, model)
    
    if fixed_command and not fixed_command.startswith("Error:"):
        print(f"\n{Colors.GREEN}{fixed_command}{Colors.END}")
        
        # Ask if user wants to execute the fixed command
        try:
            confirm = input(f"\nExecute this command? (y/n): ").strip().lower()
            if confirm == 'y':
                exit_code, new_output = execute_command(fixed_command, False, model)
                
                # Display results
                status = f"{Colors.GREEN}Success{Colors.END}" if exit_code == 0 else f"{Colors.RED}Failed (exit code: {exit_code}){Colors.END}"
                print(f"\n{Colors.CYAN}Status:{Colors.END} {status}")
        except KeyboardInterrupt:
            print("\nCancelled")
    else:
        print(f"\n{Colors.YELLOW}Could not generate a fixed command: {fixed_command}{Colors.END}")

def _auto_fix_and_execute(command: str, output: str, model: str, max_attempts: int) -> None:
    """
    Automatically fix and execute a failed command multiple times if needed.
    
    Args:
        command: The failed command
        output: The error output
        model: Model to use for fixing
        max_attempts: Maximum number of fix attempts
    """
    from qcmd_cli.core.command_generator import fix_command
    
    original_command = command
    attempts = 1
    
    while attempts <= max_attempts:
        print(f"\n{Colors.CYAN}Auto-fix attempt {attempts}/{max_attempts}...{Colors.END}")
        
        # Generate fixed command
        fixed_command = fix_command(command, output, model)
        
        if fixed_command and not fixed_command.startswith("Error:") and fixed_command != command:
            print(f"\n{Colors.GREEN}{fixed_command}{Colors.END}")
            
            # Execute the fixed command
            print(f"\n{Colors.CYAN}Executing fixed command...{Colors.END}")
            exit_code, new_output = execute_command(fixed_command, False, model)
            
            # Display results
            status = f"{Colors.GREEN}Success{Colors.END}" if exit_code == 0 else f"{Colors.RED}Failed (exit code: {exit_code}){Colors.END}"
            print(f"\n{Colors.CYAN}Status:{Colors.END} {status}")
            
            # If successful, break the loop
            if exit_code == 0:
                break
                
            # Update for next attempt
            command = fixed_command
            output = new_output
        else:
            print(f"\n{Colors.YELLOW}No better solution found after {attempts} attempts.{Colors.END}")
            break
            
        attempts += 1
        
    if attempts > max_attempts:
        print(f"\n{Colors.YELLOW}Maximum fix attempts reached. Could not fix the command.{Colors.END}")
        
    # Provide a summary
    if exit_code == 0:
        print(f"\n{Colors.GREEN}Successfully fixed and executed the command.{Colors.END}")
    else:
        print(f"\n{Colors.YELLOW}Could not fix and execute the command after {attempts-1} attempts.{Colors.END}")
        print(f"{Colors.YELLOW}Original command: {original_command}{Colors.END}")
        print(f"{Colors.YELLOW}Last attempt: {command}{Colors.END}")

def _display_banner():
    """Display the QCMD banner."""
    print()
    print(f"╔═════════════════════════════════════════════════════════════╗")
    print(f"║                                                             ║")
    print(f"║     ██████╗  ██████╗███╗   ███╗██████╗                   ║")
    print(f"║    ██╔═══██╗██╔════╝████╗ ████║██╔══██╗                  ║")
    print(f"║    ██║   ██║██║     ██╔████╔██║██║  ██║                  ║")
    print(f"║    ██║▄▄ ██║██║     ██║╚██╔╝██║██║  ██║                  ║")
    print(f"║    ╚██████╔╝╚██████╗██║ ╚═╝ ██║██████╔╝                  ║")
    print(f"║     ╚══▀▀═╝  ╚═════╝╚═╝     ╚═╝╚═════╝                   ║")
    
    # Get QCMD version
    try:
        from importlib.metadata import version
        qcmd_version = version("ibrahimiq-qcmd")
        version_text = f"v{qcmd_version}"
    except:
        version_text = "v1.0.10"  # Fallback version
    
    print(f"║                                              {version_text}        ║")
    print(f"║                                                             ║")
    print(f"╚═════════════════════════════════════════════════════════════╝")

def auto_mode(prompt: str, model: str = DEFAULT_MODEL, max_attempts: int = 3, temperature: float = 0.7) -> None:
    """
    Run in auto-correction mode, automatically fixing errors.
    
    Args:
        prompt: The natural language prompt
        model: The model to use
        max_attempts: Maximum number of correction attempts
        temperature: Temperature parameter for generation
    """
    print(f"{Colors.CYAN}Generating command in auto-correction mode...{Colors.END}")
    
    # Generate initial command
    command = generate_command(prompt, model, temperature)
    
    if not command:
        print(f"{Colors.RED}Failed to generate a command.{Colors.END}")
        return
    
    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            print(f"\n{Colors.CYAN}Attempt {attempt}/{max_attempts}:{Colors.END}")
            
        print(f"\n{Colors.CYAN}Generated command:{Colors.END}")
        print(f"{Colors.GREEN}{command}{Colors.END}\n")
        
        # Execute the command
        print(f"{Colors.CYAN}Executing command...{Colors.END}\n")
        return_code, output = execute_command(command)
        
        if return_code == 0:
            print(f"\n{Colors.GREEN}Command executed successfully.{Colors.END}")
            if output:
                print(f"\n{Colors.BOLD}Output:{Colors.END}")
                print(output)
            return
        else:
            print(f"\n{Colors.RED}Command failed with return code {return_code}{Colors.END}")
            if output:
                print(f"\n{Colors.BOLD}Error output:{Colors.END}")
                print(output)
            
            # Don't attempt to fix if we've reached max attempts
            if attempt >= max_attempts:
                print(f"\n{Colors.YELLOW}Maximum correction attempts reached. Giving up.{Colors.END}")
                return
                
            # Try to fix the command
            print(f"\n{Colors.CYAN}Attempting to fix the command...{Colors.END}")
            command = fix_command(command, output, model)
            
            # Add a small delay to make the process more readable
            time.sleep(1)


