# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.18] - 2025-04-15

### Added
- Improved `/status` command to display active log monitors.
- Enhanced live monitoring functionality with persistent storage for active monitors.
- Added meaningful text analysis for log entries.

### Fixed
- Resolved repeated signal handling issues during live monitoring.

## [1.0.17] - 2024-04-12

### Changed
- Improved QCMD banner with better alignment and visual appeal
- Enhanced UI for a more professional appearance
- Reduced verbosity in command output for better user experience
- Streamlined display of information to users
- Updated progress bar to use a cleaner design

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