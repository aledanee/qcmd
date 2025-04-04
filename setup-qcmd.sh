#!/bin/bash
# Setup script for qcmd

set -e  # Exit on error

# Color output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BLUE}${BOLD}qcmd Setup Script${NC}"
echo -e "${BLUE}===================${NC}"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed. Please install Python 3 and try again.${NC}"
    exit 1
fi

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}Warning: Ollama is not found in your PATH. Make sure it's installed and running.${NC}"
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Make qcmd executable
echo -e "${GREEN}Making qcmd executable...${NC}"
chmod +x qcmd

# Check if we have sudo access (only needed for system-wide installation)
HAS_SUDO=0
if command -v sudo &> /dev/null && sudo -n true 2>/dev/null; then
    HAS_SUDO=1
fi

# Prompt for installation type
echo
echo -e "${BLUE}Installation Options:${NC}"
echo -e "1) User-local installation (recommended)"
echo -e "2) System-wide installation (requires sudo)"
echo
read -p "Select installation type [1/2]: " INSTALL_TYPE

if [ "$INSTALL_TYPE" = "2" ] && [ $HAS_SUDO -eq 0 ]; then
    echo -e "${YELLOW}Warning: System-wide installation selected but sudo is not available.${NC}"
    echo -e "${YELLOW}Falling back to user-local installation.${NC}"
    INSTALL_TYPE="1"
fi

# User-local installation
if [ "$INSTALL_TYPE" = "1" ]; then
    echo -e "${GREEN}Performing user-local installation...${NC}"
    
    # Create bin directory if it doesn't exist
    mkdir -p "$HOME/.local/bin"
    
    # Copy qcmd to bin directory
    echo -e "${GREEN}Copying qcmd to ~/.local/bin...${NC}"
    cp qcmd "$HOME/.local/bin/"
    
    # Add to PATH if not already there
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo -e "${YELLOW}Adding ~/.local/bin to your PATH...${NC}"
        
        # Detect shell and update appropriate config file
        SHELL_NAME=$(basename "$SHELL")
        if [ "$SHELL_NAME" = "bash" ]; then
            CONFIG_FILE="$HOME/.bashrc"
        elif [ "$SHELL_NAME" = "zsh" ]; then
            CONFIG_FILE="$HOME/.zshrc"
        else
            CONFIG_FILE="$HOME/.profile"
        fi
        
        echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$CONFIG_FILE"
        echo -e "${YELLOW}Added PATH to $CONFIG_FILE. Please restart your terminal or run:${NC}"
        echo -e "${BOLD}source $CONFIG_FILE${NC}"
    fi
    
    # Set up bash completion
    echo -e "${GREEN}Setting up command completion...${NC}"
    mkdir -p "$HOME/.bash_completion.d"
    cp qcmd-completion.bash "$HOME/.bash_completion.d/qcmd"
    
    # Add completion source to shell config if not already there
    if ! grep -q "bash_completion.d/qcmd" "$CONFIG_FILE"; then
        echo "# qcmd completion" >> "$CONFIG_FILE"
        echo "if [ -f \"\$HOME/.bash_completion.d/qcmd\" ]; then" >> "$CONFIG_FILE"
        echo "    source \"\$HOME/.bash_completion.d/qcmd\"" >> "$CONFIG_FILE"
        echo "fi" >> "$CONFIG_FILE"
    fi
    
    echo -e "${GREEN}${BOLD}qcmd has been installed to ~/.local/bin${NC}"
    
# System-wide installation
else
    echo -e "${GREEN}Performing system-wide installation...${NC}"
    
    # Copy qcmd to /usr/local/bin
    echo -e "${GREEN}Copying qcmd to /usr/local/bin...${NC}"
    sudo cp qcmd /usr/local/bin/
    sudo chmod +x /usr/local/bin/qcmd
    
    # Set up bash completion
    echo -e "${GREEN}Setting up command completion...${NC}"
    sudo cp qcmd-completion.bash /etc/bash_completion.d/qcmd
    
    echo -e "${GREEN}${BOLD}qcmd has been installed system-wide${NC}"
fi

echo
echo -e "${GREEN}${BOLD}Installation complete!${NC}"
echo -e "${BLUE}To get started, try:${NC}"
echo -e "  ${BOLD}qcmd \"list files in current directory\"${NC}"
echo -e "  ${BOLD}qcmd -A \"find large files\"${NC}"
echo -e "  ${BOLD}qcmd -s${NC} (for interactive shell)"
echo
echo -e "${YELLOW}NOTE: For tab completion to work, you may need to restart your terminal.${NC}" 