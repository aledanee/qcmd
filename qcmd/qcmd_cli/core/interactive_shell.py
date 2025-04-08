#!/usr/bin/env python3
"""
Interactive shell functionality for QCMD.
"""
import os
import sys
import readline
import signal
import time
from typing import List, Optional, Dict, Any

# Import from other modules 
from ..core.command_generator import generate_command, execute_command, fix_command
from ..utils.history import save_to_history, load_history, show_history
from ..config.settings import DEFAULT_MODEL, load_config
from ..ui.display import Colors, print_cool_header, print_examples, display_help_command
from ..log_analysis.log_files import handle_log_analysis
from ..utils.system import display_system_status, check_for_updates

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

def start_interactive_shell(auto_mode_enabled: bool = False, current_model: str = DEFAULT_MODEL, 
                           current_temperature: float = 0.7, max_attempts: int = 3) -> None:
    """
    Start the interactive QCMD shell.
    
    Args:
        auto_mode_enabled: Whether auto-correction mode is enabled
        current_model: The model to use for command generation
        current_temperature: Temperature parameter for generation
        max_attempts: Maximum number of auto-correction attempts
    """
    # Available shell commands for autocompletion
    shell_commands = [
        '!help', '!exit', '!quit', '!clear', '!history', '!search', '!status',
        '!model', '!models', '!temp', '!temperature', '!auto on', '!auto off',
        '!max', '!update', '!logs', '!config', '!analyze', '!monitor', '!watch', '!!'
    ]
    
    # Set up command completion
    completer = SimpleCompleter(shell_commands)
    readline.set_completer(completer.complete)
    readline.parse_and_bind('tab: complete')
    
    # Register signal handlers for clean exit
    def handle_sigint(signum, frame):
        print("\nExiting QCMD interactive shell...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, handle_sigint)
    
    # Welcome message
    print(f"\n{Colors.GREEN}{Colors.BOLD}QCMD Interactive Shell{Colors.END}")
    print(f"Type a description of the command you need, or {Colors.BOLD}!help{Colors.END} for assistance.")
    print(f"Model: {Colors.CYAN}{current_model}{Colors.END}, Temperature: {Colors.CYAN}{current_temperature}{Colors.END}")
    print(f"Auto-correction mode: {Colors.CYAN}{'Enabled' if auto_mode_enabled else 'Disabled'}{Colors.END}")
    print(f"Type {Colors.BOLD}!exit{Colors.END} to quit.\n")
    
    # Main interaction loop
    last_prompt = None
    while True:
        try:
            # Get user input
            prompt = input(f"{Colors.GREEN}qcmd>{Colors.END} ").strip()
            
            # Skip empty input
            if not prompt:
                continue
                
            # Handle special commands starting with !
            if prompt.startswith('!'):
                # Extract command and arguments
                parts = prompt.split(maxsplit=1)
                command = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ''
                
                # Help command
                if command == '!help':
                    display_help_command(current_model, current_temperature, auto_mode_enabled, max_attempts)
                    continue
                    
                # Exit command
                elif command in ['!exit', '!quit']:
                    print("Exiting QCMD interactive shell...")
                    break
                    
                # Clear screen
                elif command == '!clear':
                    os.system('clear' if os.name == 'posix' else 'cls')
                    continue
                    
                # Show history
                elif command == '!history':
                    count = 20
                    if args and args.isdigit():
                        count = int(args)
                    show_history(count)
                    continue
                    
                # Search history
                elif command == '!search':
                    if not args:
                        print(f"{Colors.YELLOW}Usage: !search <term>{Colors.END}")
                        continue
                    show_history(search_term=args)
                    continue
                    
                # Show system status
                elif command == '!status':
                    display_system_status()
                    continue
                    
                # List available models
                elif command == '!models':
                    from ..core.command_generator import list_models
                    models = list_models()
                    if models:
                        print(f"\n{Colors.CYAN}Available models:{Colors.END}")
                        for model in models:
                            if model == current_model:
                                print(f"  {Colors.GREEN}{Colors.BOLD}* {model} (current){Colors.END}")
                            else:
                                print(f"  {Colors.YELLOW}- {model}{Colors.END}")
                    else:
                        print(f"{Colors.YELLOW}No models found. Make sure Ollama is running.{Colors.END}")
                    continue
                    
                # Change model
                elif command == '!model':
                    if not args:
                        print(f"{Colors.YELLOW}Current model: {current_model}{Colors.END}")
                        print(f"{Colors.YELLOW}Usage: !model <model_name>{Colors.END}")
                        continue
                    current_model = args
                    print(f"{Colors.GREEN}Model changed to: {current_model}{Colors.END}")
                    
                    # Update config
                    config = load_config()
                    config['model'] = current_model
                    from ..config.settings import save_config
                    save_config(config)
                    continue
                    
                # Set temperature
                elif command in ['!temp', '!temperature']:
                    if not args:
                        print(f"{Colors.YELLOW}Current temperature: {current_temperature}{Colors.END}")
                        print(f"{Colors.YELLOW}Usage: !temperature <value> (between 0.0 and 1.0){Colors.END}")
                        continue
                    
                    try:
                        value = float(args)
                        if 0.0 <= value <= 1.0:
                            current_temperature = value
                            print(f"{Colors.GREEN}Temperature set to: {current_temperature}{Colors.END}")
                            
                            # Update config
                            config = load_config()
                            config['temperature'] = current_temperature
                            from ..config.settings import save_config
                            save_config(config)
                        else:
                            print(f"{Colors.RED}Temperature must be between 0.0 and 1.0{Colors.END}")
                    except ValueError:
                        print(f"{Colors.RED}Invalid temperature value. Please enter a number between 0.0 and 1.0{Colors.END}")
                    continue
                    
                # Toggle auto mode
                elif command == '!auto':
                    if args.lower() in ['on', 'yes', 'true', '1']:
                        auto_mode_enabled = True
                        print(f"{Colors.GREEN}Auto-correction mode enabled{Colors.END}")
                    elif args.lower() in ['off', 'no', 'false', '0']:
                        auto_mode_enabled = False
                        print(f"{Colors.GREEN}Auto-correction mode disabled{Colors.END}")
                    else:
                        print(f"{Colors.YELLOW}Current auto-correction mode: {'Enabled' if auto_mode_enabled else 'Disabled'}{Colors.END}")
                        print(f"{Colors.YELLOW}Usage: !auto on|off{Colors.END}")
                    continue
                    
                # Set max attempts
                elif command == '!max':
                    if not args:
                        print(f"{Colors.YELLOW}Current max attempts: {max_attempts}{Colors.END}")
                        print(f"{Colors.YELLOW}Usage: !max <number>{Colors.END}")
                        continue
                    
                    try:
                        value = int(args)
                        if value > 0:
                            max_attempts = value
                            print(f"{Colors.GREEN}Max attempts set to: {max_attempts}{Colors.END}")
                            
                            # Update config
                            config = load_config()
                            config['max_attempts'] = max_attempts
                            from ..config.settings import save_config
                            save_config(config)
                        else:
                            print(f"{Colors.RED}Max attempts must be greater than 0{Colors.END}")
                    except ValueError:
                        print(f"{Colors.RED}Invalid value. Please enter a positive integer{Colors.END}")
                    continue
                    
                # Check for updates
                elif command == '!update':
                    check_for_updates(force_display=True)
                    continue
                    
                # Log analysis
                elif command == '!logs':
                    handle_log_analysis(current_model, args if args else None)
                    continue
                    
                # Config command
                elif command == '!config':
                    from ..config.settings import handle_config_command
                    handle_config_command(args)
                    continue
                    
                # Repeat last command
                elif command == '!!':
                    if last_prompt:
                        prompt = last_prompt
                        print(f"{Colors.YELLOW}Repeating: {prompt}{Colors.END}")
                    else:
                        print(f"{Colors.YELLOW}No previous command to repeat{Colors.END}")
                        continue
                
                # Unknown command
                else:
                    print(f"{Colors.RED}Unknown command: {command}{Colors.END}")
                    print(f"{Colors.YELLOW}Type !help for a list of available commands{Colors.END}")
                    continue
            
            # If we get here, it's a natural language command
            
            # Save current prompt for potential repeat
            last_prompt = prompt
            
            # Save to history
            save_to_history(prompt)
            
            # Run in auto mode if enabled
            if auto_mode_enabled:
                auto_mode(prompt, current_model, max_attempts, current_temperature)
                continue
            
            # Regular mode: generate command and ask for confirmation
            command = generate_command(prompt, current_model, current_temperature)
            
            if not command:
                print(f"{Colors.RED}Failed to generate a command.{Colors.END}")
                continue
                
            print(f"\n{Colors.CYAN}Generated command:{Colors.END}")
            print(f"{Colors.GREEN}{command}{Colors.END}\n")
            
            # Ask for confirmation
            confirmation = input(f"{Colors.BOLD}Execute this command? (y/n/e to edit): {Colors.END}").strip().lower()
            
            if confirmation == 'y':
                # Execute the command
                print(f"\n{Colors.CYAN}Executing command...{Colors.END}\n")
                return_code, output = execute_command(command)
                
                if return_code == 0:
                    print(f"\n{Colors.GREEN}Command executed successfully.{Colors.END}")
                else:
                    print(f"\n{Colors.RED}Command failed with return code {return_code}{Colors.END}")
                    
                if output:
                    print(f"\n{Colors.BOLD}Output:{Colors.END}")
                    print(output)
            elif confirmation == 'e':
                # Allow editing the command
                edited_command = input(f"{Colors.BOLD}Edit command: {Colors.END}")
                if edited_command:
                    command = edited_command
                    print(f"\n{Colors.CYAN}Executing edited command...{Colors.END}\n")
                    return_code, output = execute_command(command)
                    
                    if return_code == 0:
                        print(f"\n{Colors.GREEN}Command executed successfully.{Colors.END}")
                    else:
                        print(f"\n{Colors.RED}Command failed with return code {return_code}{Colors.END}")
                        
                    if output:
                        print(f"\n{Colors.BOLD}Output:{Colors.END}")
                        print(output)
                else:
                    print(f"{Colors.YELLOW}Command execution cancelled.{Colors.END}")
            else:
                print(f"{Colors.YELLOW}Command execution cancelled.{Colors.END}")
                
        except EOFError:
            # Handle Ctrl+D
            print("\nExiting QCMD interactive shell...")
            break
        except KeyboardInterrupt:
            # Handle Ctrl+C more gracefully
            print("\nCommand interrupted. Type !exit to quit.")
        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.END}")

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