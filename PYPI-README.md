# qcmd - AI-powered Command Generator

A simple command-line tool that generates shell commands using local AI models via Ollama.

**Version 1.0.1**

## Overview

**qcmd** is a powerful command-line tool that generates shell commands using AI language models via Ollama. Simply describe what you want to do in natural language, and qcmd will generate the appropriate command.

## Key Features

- **Natural Language Inputs**: Describe what you want to do in plain English
- **Auto-fix Mode**: Automatically fixes failed commands and retries
- **AI Error Analysis**: Explains errors and suggests solutions
- **Interactive Shell**: Continuous operation with command history
- **Multiple Models**: Works with any Ollama model (default: qwen2.5-coder:0.5b)
- **Safety First**: Always asks for confirmation before executing any command
- **Log Analysis**: Find and analyze system log files with real-time monitoring

## Installation

### Prerequisites

- Python 3.6 or higher
- [Ollama](https://ollama.ai/) installed and running
- At least one language model pulled (e.g., qwen2.5-coder:0.5b)

### Install from PyPI

```bash
pip install ibrahimiq-qcmd
```

Make sure Ollama is running before using qcmd:
```bash
ollama serve
```

## Basic Usage

```bash
# Generate and confirm a command
qcmd "list all files in the current directory"

# Auto-execute mode
qcmd -e "find large log files"

# Smart auto-fix mode
qcmd -A "find Python files modified today"

# Interactive shell
qcmd -s
```

## What's New in 1.0.1

- Updated documentation with improved installation instructions
- Fixed package structure for better compatibility
- Added PyPI integration for easier installation

## Full Documentation

For full documentation and source code, visit the [GitHub repository](https://github.com/aledanee/qcmd). 