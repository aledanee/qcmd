#!/usr/bin/env python3
"""
Command handling functionality for QCMD.
"""
import os
import sys
import shlex
import argparse
from typing import Dict, List, Any, Optional

# Import from other modules
from ..core.interactive_shell import start_interactive_shell, auto_mode
from ..log_analysis.log_files import handle_log_analysis, list_active_log_monitors, stop_log_monitor, view_monitor, open_session_monitor
from ..utils.system import display_system_status, check_for_updates
from ..config.settings import handle_config_command, load_config
from ..core.command_generator import generate_command, execute_command, list_models
from ..utils.history import show_history, save_to_history
from ..ui.display import print_iraq_banner, show_download_progress, print_cool_header, print_examples

# Create parser as a module-level variable so it's available to both parse_args and main
parser = argparse.ArgumentParser(
    description='Generate and execute shell commands using AI.',
    epilog='Example: qcmd "list all files in current directory recursively"'
)

def parse_args():
    """
    Parse command-line arguments.
    
    Returns:
        The parsed command-line arguments
    """
    # Basic command prompt argument
    parser.add_argument('prompt', nargs='?', default=None,
                        help='Natural language description of the command to generate')
    
    # Operation modes
    parser.add_argument('-s', '--shell', action='store_true',
                        help='Start an interactive shell for generating multiple commands')
    parser.add_argument('-e', '--execute', action='store_true',
                        help='Execute the generated command automatically')
    parser.add_argument('-a', '--auto', action='store_true',
                        help='Enable auto-correction mode')
    parser.add_argument('-t', '--temperature', type=float, default=None,
                       help='Set the temperature for generation (0.0-1.0)')
    
    # Utility commands
    parser.add_argument('--status', action='store_true',
                       help='Display system status')
    parser.add_argument('--check-updates', '--update-check', action='store_true',
                       help='Check for updates to qcmd')
    parser.add_argument('--history', action='store_true',
                       help='Show command history')
    parser.add_argument('--history-count', type=int, default=20,
                       help='Number of history entries to show')
    parser.add_argument('--search-history', type=str,
                       help='Search term for filtering history')
    
    # Log handling
    parser.add_argument('--logs', '--log', dest='logs', action='store_true',
                       help='Analyze log files')
    parser.add_argument('--log-file', type=str,
                       help='Specify a log file to analyze')
    parser.add_argument('--analyze-once', action='store_true',
                       help='Analyze the log file once (no monitoring)')
    parser.add_argument('--monitor-analyze', action='store_true',
                       help='Monitor the log file with analysis')
    parser.add_argument('--monitor-watch', action='store_true',
                       help='Monitor the log file without analysis (just watch)')
    parser.add_argument('--list-monitors', action='store_true',
                       help='List active log monitors')
    parser.add_argument('--stop-monitor', type=str,
                       help='Stop a log monitor by session ID')
    parser.add_argument('--view-monitor', type=str,
                       help='View a running monitor by session ID')
    parser.add_argument('--open-monitor', action='store_true',
                       help='Open a log monitor - will show list of active monitors and let you select one')
    parser.add_argument('--analysis-only', action='store_true',
                       help='When viewing monitors, only show analysis results without raw log lines')
    
    # Configuration options
    parser.add_argument('--model', type=str, default=None,
                       help='Specify which model to use')
    parser.add_argument('--config', type=str,
                       help='Set a configuration option (format: key=value)')
    
    # UI Customization
    parser.add_argument('--no-banner', action='store_true',
                       help='Disable the banner display')
    parser.add_argument('--no-progress', action='store_true',
                       help='Disable progress bar display')
    parser.add_argument('--compact', action='store_true',
                       help='Enable compact display mode')
    parser.add_argument('--banner-font', type=str,
                       help='Set the font to use for the banner (pyfiglet font name)')
    
    args = parser.parse_args()
    
    # Load config
    config = load_config()
    
    # Apply UI customization options to config
    if args.no_banner:
        config['ui']['show_iraq_banner'] = False
    if args.no_progress:
        config['ui']['show_progress_bar'] = False
    if args.compact:
        config['ui']['compact_mode'] = True
    if args.banner_font:
        config['ui']['banner_font'] = args.banner_font
    
    return args

def main():
    """
    Main entry point for the QCMD application.
    """
    # Initialize config directory
    os.makedirs(os.path.dirname(os.path.expanduser("~/.qcmd")), exist_ok=True)
    
    # Parse command-line arguments
    args = parse_args()
    
    # Load configuration
    config = load_config()
    
    # Set default model from config if not specified
    if args.model is None:
        args.model = config.get('model')
    
    # Handle utility commands first (no banner needed)
    
    # If checking for updates
    if args.check_updates:
        check_for_updates(force_display=True)
        return
    
    # If setting configuration via command line
    if args.config:
        parts = args.config.split('=', 1)
        if len(parts) == 2:
            key, value = parts
            handle_config_command(f"set {key} {value}")
        else:
            print(f"Usage: --config KEY=VALUE")
        return
        
    # If showing status
    if args.status:
        display_system_status()
        return
        
    # If showing history
    if args.history:
        show_history(args.history_count, args.search_history)
        return
        
    # If analyzing logs
    if args.logs:
        handle_log_analysis(args.model, args.log_file, 
                          analyze_once=args.analyze_once,
                          monitor_analyze=args.monitor_analyze,
                          monitor_watch=args.monitor_watch)
        return
    
    # If listing active log monitors
    if args.list_monitors:
        list_active_log_monitors()
        return

    # If stopping a log monitor
    if args.stop_monitor:
        stop_log_monitor(args.stop_monitor)
        return
        
    # If viewing a log monitor
    if args.view_monitor:
        view_monitor(args.view_monitor, show_analysis_only=args.analysis_only)
        return
    
    # If opening a monitor interactively
    if args.open_monitor:
        open_session_monitor(show_analysis_only=args.analysis_only)
        return
    
    # Display minimal banner for main operations
    if config.get('ui', {}).get('show_iraq_banner', True) and not args.no_banner:
        print_iraq_banner()
    
    # Show loading animation unless disabled
    if config.get('ui', {}).get('show_progress_bar', True) and not args.no_progress:
        show_download_progress()
        
    # If starting interactive shell
    if args.shell:
        print_cool_header()
        print_examples()
        start_interactive_shell(
            auto_mode_enabled=args.auto,
            current_model=args.model,
            current_temperature=args.temperature if args.temperature is not None else config.get('temperature', 0.7),
            max_attempts=config.get('max_attempts', 3)
        )
        return
        
    # If no prompt is provided and no special commands, show help
    if args.prompt is None:
        print_cool_header()
        print_examples()
        parser.print_help()
        return
        
    # Process prompt and generate command
    prompt = args.prompt
    
    # Save to history
    save_to_history(prompt)
    
    # Generate the command
    command = generate_command(
        prompt=prompt,
        model=args.model,
        temperature=args.temperature if args.temperature is not None else config.get('temperature', 0.7)
    )
    
    # Run in auto mode if requested
    if args.auto:
        auto_mode(
            prompt=prompt,
            model=args.model,
            max_attempts=config.get('max_attempts', 3),
            temperature=args.temperature if args.temperature is not None else config.get('temperature', 0.7)
        )
        return
        
    # Execute if requested, otherwise just display
    if args.execute:
        print(f"Executing: {command}\n")
        return_code, output = execute_command(command)
        
        if return_code == 0:
            print(f"✅ Command executed successfully.")
        else:
            print(f"❌ Command failed (exit code: {return_code}).")
            
        if output:
            print(f"\n{output}")
    else:
        print(f"\n{command}")

if __name__ == "__main__":
    main() 