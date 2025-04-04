# qcmd - AI-powered Command Generator

A simple command-line tool that generates shell commands using local AI models via Ollama.

![qcmd demo](https://raw.githubusercontent.com/aledanee/qcmd/main/docs/qcmd-demo.gif)

## Overview

**qcmd** is a powerful command-line tool that generates shell commands using AI language models via Ollama. Simply describe what you want to do in natural language, and qcmd will generate the appropriate command.

### Key Features

- **Natural Language Inputs**: Describe what you want to do in plain English
- **Auto-fix Mode**: Automatically fixes failed commands and retries
- **AI Error Analysis**: Explains errors and suggests solutions
- **Interactive Shell**: Continuous operation with command history
- **Tab Completion**: Context-aware suggestions for commands and arguments
- **Multiple Models**: Works with any Ollama model (default: qwen2.5-coder:0.5b)
- **Safety First**: Always asks for confirmation before executing any command (except in auto mode)
- **Log Analysis**: Find and analyze system log files with real-time monitoring
- **File Monitoring**: Analyze and continuously monitor any file with AI

## Installation

### Prerequisites

- Python 3.6 or higher
- [Ollama](https://ollama.ai/) installed and running
- At least one language model pulled (e.g., qwen2.5-coder:0.5b)

### Quick Install

```bash
git clone https://github.com/aledanee/qcmd.git
cd qcmd
chmod +x setup-qcmd.sh
./setup-qcmd.sh
```

The setup script will guide you through:
- User-local installation (recommended)
- System-wide installation (requires sudo)
- Setting up tab completion

Make sure Ollama is running before using qcmd:
```bash
ollama serve
```

## Basic Usage

### Generate a Command

```bash
qcmd "list all files in the current directory"
```

This will generate a command like `ls -la` and ask if you want to execute it.

### Auto-Execute Mode

```bash
qcmd -e "find large log files"
```

### Smart Auto Mode

```bash
qcmd -A "find Python files modified today"
```

The auto mode will automatically generate, execute, and fix commands without requiring confirmation. It will attempt to fix failed commands up to a maximum number of attempts.

### Log Analysis

```bash
qcmd --logs
```

Finds log files on your system, allows you to select one, and provides AI-powered analysis of the log content. Can monitor logs in real-time with continuous analysis of new entries.

### View All Log Files

```bash
qcmd --all-logs
```

Displays a comprehensive list of all log files found on your system in a single view. Select any log file to analyze or monitor it.

### Analyze Specific File

```bash
qcmd --analyze-file /path/to/file.log
```

Directly analyze a specific file using AI to identify patterns, errors, and issues.

### Monitor File with AI

```bash
qcmd --monitor /path/to/file.log
```

Continuously monitor a specific file, analyzing new content as it's added in real-time with AI.

### Interactive Shell

```bash
qcmd -s
```

Start an interactive shell for continuous command generation with history and completion.

## Safety Features

qcmd prioritizes safety in normal mode and never executes commands without explicit user confirmation:

- **Always Confirms**: Every command requires confirmation before execution (except in auto mode)
- **Dangerous Command Detection**: Warns about potentially destructive commands
- **Auto-Fix Confirmation**: Asks before attempting to fix failed commands (in normal mode)
- **Simplified Confirmation**: Use `-y` for a streamlined "press Enter to confirm" prompt

## Full Documentation

For detailed documentation, see the [documentation page](./qcmd-docs.html) or run:

```bash
qcmd --help
```

## Command-Line Options

### Main Arguments
- `prompt`: Natural language description of the command you want

### Model Selection
- `--model`, `-m`: Model to use (default: qwen2.5-coder:0.5b)
- `--list`, `-l`: List available models and exit
- `--list-models`: Same as --list, shows available models

### Execution Options
- `--execute`, `-e`: Execute the generated command after confirmation
- `--yes`, `-y`: Use simplified confirmation (just press Enter to execute)
- `--dry-run`, `-d`: Just show the command without executing
- `--analyze`, `-a`: Analyze errors if command execution fails
- `--auto`, `-A`: Auto mode: automatically generate, execute, and fix errors without confirmation
- `--max-attempts`: Maximum number of fix attempts in auto mode (default: 3)

### Log Analysis Options
- `--logs`: Find and analyze system log files
- `--all-logs`: Show all available log files in a single list
- `--analyze-file FILE`: Analyze a specific file
- `--monitor FILE`: Monitor a specific file continuously with AI analysis

### Shell Options
- `--shell`, `-s`: Start an interactive shell
- `--history`: Show command history
- `--history-count`: Number of history entries to show (default: 20)

### Generation Options
- `--temperature`, `-t`: Temperature for generation (0.0-1.0, higher=more creative)

### Output Options
- `--no-color`: Disable colored output
- `--examples`: Show detailed usage examples
- `--save-output`: Save command output to a file

### Configuration Options
- `--set-timeout SECONDS`: Set API request timeout in seconds
- `--no-timeout`: Disable API request timeout
- `--save-config`: Save current settings as default configuration
- `--reset-config`: Reset configuration to defaults
- `--config-path`: Show the path to the configuration file
- `--add-favorite-log PATH`: Add a log file to favorites

## Interactive Shell Commands

Inside the interactive shell, use:

- `/help` - Show help message
- `/exit`, `/quit` - Exit the shell
- `/history` - Show command history
- `/models` - List available models
- `/model <name>` - Switch to a different model
- `/temperature <t>` - Set temperature (0.0-1.0)
- `/auto` - Enable auto mode
- `/manual` - Disable auto mode
- `/analyze` - Toggle error analysis
- `/execute` - Execute last generated command (with confirmation)
- `/dry-run` - Generate without executing
- `/logs` - Find and analyze log files
- `/all-logs` - Show all available log files in a single list
- `/analyze-file <path>` - Analyze a specific file
- `/monitor <path>` - Monitor a file continuously with AI analysis

## Examples

### Basic Command Generation
```bash
qcmd "list all files in the current directory"
qcmd "find large log files"
```

### Auto-Execute Commands
```bash
qcmd -e "check disk space usage"
qcmd --execute "show current directory"
```

### Using Different Models
```bash
qcmd -m llama2:7b "restart the nginx service"
qcmd --model deepseek-coder "create a backup of config files"
```

### Adjusting Creativity
```bash
qcmd -t 0.7 "find all JPG images"
qcmd --temperature 0.9 "monitor network traffic"
```

### AI Error Analysis
```bash
qcmd --analyze "find files larger than 1GB"
qcmd -a -m llama2:7b "create a tar archive of logs"
```

### Auto Mode (Auto-Execute with Error Fixing)
```bash
qcmd --auto "find Python files modified today"
qcmd -A "search logs for errors"
qcmd -A -m llama2:7b "get system information"
```

### Log Analysis
```bash
qcmd --logs
qcmd --logs -m llama2:7b
qcmd --all-logs
qcmd --analyze-file /var/log/syslog
qcmd --monitor /var/log/auth.log
```
In interactive shell mode:
```
/logs
/all-logs
/analyze-file /var/log/syslog
/monitor /path/to/application.log
```

## License

MIT

## Contributing

Contributions are welcome! Here's how you can help:

1. **Report bugs or suggest features** by opening issues
2. **Submit pull requests** for bug fixes or new features
3. **Improve documentation** or add examples
4. **Share your use cases** and how you're using qcmd

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/aledanee/qcmd.git
   cd qcmd
   ```

2. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Make your changes and test them thoroughly

4. Submit a pull request with a clear description of your changes

### Code Style

- Follow PEP 8 guidelines
- Add docstrings for new functions and classes
- Include type hints for function parameters and return values
- Write tests for new functionality

## Acknowledgments

- Powered by [Ollama](https://ollama.ai/) and local language models
- Default model: qwen2.5-coder:0.5b 