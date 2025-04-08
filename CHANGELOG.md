# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added configurable command execution timeout (PR #1)
- Added automatic error analysis when commands fail
- Added more detailed dependency specifications

### Changed
- Improved error handling in command execution
- Enhanced timeout handling with graceful termination
- Better error reporting for common command execution failures

## [1.0.0] - 2024-04-04

### Added
- Initial release of qcmd
- Command generation using Ollama and local LLMs
- Interactive shell mode
- Command history management
- Error analysis and auto-fixing
- Log file analysis and monitoring
- Configuration management
- Tab completion support
- Multiple model support
- Safety features for dangerous command detection 