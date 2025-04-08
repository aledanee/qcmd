#!/bin/bash
# Script to publish qcmd to GitHub

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BLUE}${BOLD}qcmd Publishing Script${NC}"
echo -e "${BLUE}=========================${NC}"
echo

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo -e "${RED}Error: Git is not installed. Please install Git and try again.${NC}"
    exit 1
fi

# Initialize git repository if needed
if [ ! -d .git ]; then
    echo -e "${GREEN}Initializing Git repository...${NC}"
    git init
    
    # Ask for user info if not set
    if [ -z "$(git config --global user.name)" ]; then
        echo -e "${YELLOW}Git user name not set. Please enter your name:${NC}"
        read -r GIT_NAME
        git config --global user.name "$GIT_NAME"
    fi
    
    if [ -z "$(git config --global user.email)" ]; then
        echo -e "${YELLOW}Git user email not set. Please enter your email:${NC}"
        read -r GIT_EMAIL
        git config --global user.email "$GIT_EMAIL"
    fi
else
    echo -e "${GREEN}Git repository already initialized.${NC}"
fi

# Check if remote already exists
REMOTE_EXISTS=$(git remote -v | grep -c origin)
if [ "$REMOTE_EXISTS" -eq 0 ]; then
    echo -e "${GREEN}Adding remote repository...${NC}"
    git remote add origin https://github.com/aledanee/qcmd.git
else
    echo -e "${GREEN}Remote repository already configured.${NC}"
fi

# Add all files
echo -e "${GREEN}Adding files to Git...${NC}"
git add .

# Create initial commit
echo -e "${GREEN}Creating commit...${NC}"
git commit -m "Initial release of qcmd v1.0.0"

# Create a 'main' branch if on 'master'
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" = "master" ]; then
    echo -e "${GREEN}Renaming master branch to main...${NC}"
    git branch -M main
fi

# Push to GitHub
echo -e "${GREEN}Pushing to GitHub...${NC}"
echo -e "${YELLOW}Note: You will need to provide your GitHub credentials${NC}"
git push -u origin main

echo -e "${GREEN}${BOLD}Done! The qcmd repository has been published to GitHub.${NC}"
echo
echo -e "${BLUE}Next steps:${NC}"
echo -e "1. Create a PyPI account if you don't have one: ${BOLD}https://pypi.org/account/register/${NC}"
echo -e "2. Build and upload to PyPI with: ${BOLD}python setup.py sdist bdist_wheel && pip install twine && twine upload dist/*${NC}"
echo 