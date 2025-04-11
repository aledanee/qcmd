#!/usr/bin/env python3
"""
Version bumping script for QCMD.

This script updates the version in the .env file and optionally in other files
to maintain backward compatibility.
"""
import os
import re
import argparse
from pathlib import Path

def find_project_root() -> Path:
    """Find the project root directory (where .env and pyproject.toml are located)."""
    current_dir = Path(__file__).parent.absolute()
    return current_dir

def read_current_version() -> str:
    """Read the current version from .env file."""
    env_path = find_project_root() / ".env"
    if not env_path.exists():
        raise FileNotFoundError(f".env file not found at {env_path}")
        
    with open(env_path, 'r') as f:
        for line in f:
            match = re.match(r'^QCMD_VERSION=(.+)$', line.strip())
            if match:
                return match.group(1)
                
    # If not found, look in __init__.py as fallback
    init_path = find_project_root() / "qcmd_cli" / "__init__.py"
    if init_path.exists():
        with open(init_path, 'r') as f:
            content = f.read()
            match = re.search(r'__version__\s*=\s*["\']([0-9]+\.[0-9]+\.[0-9]+)["\']', content)
            if match:
                return match.group(1)
    
    raise ValueError("Could not find current version in .env or __init__.py")

def bump_version(current_version: str, bump_type: str) -> str:
    """
    Bump the version number based on the bump type.
    
    Args:
        current_version: Current version string in format x.y.z
        bump_type: Type of bump: 'major', 'minor', or 'patch'
        
    Returns:
        New version string
    """
    # Parse the current version
    try:
        major, minor, patch = map(int, current_version.split('.'))
    except ValueError:
        raise ValueError(f"Invalid version format: {current_version}. Expected format: x.y.z")
    
    # Bump the appropriate part
    if bump_type == 'major':
        major += 1
        minor = 0
        patch = 0
    elif bump_type == 'minor':
        minor += 1
        patch = 0
    elif bump_type == 'patch':
        patch += 1
    else:
        raise ValueError(f"Invalid bump type: {bump_type}. Must be 'major', 'minor', or 'patch'")
    
    # Return the new version string
    return f"{major}.{minor}.{patch}"

def update_env_file(new_version: str) -> None:
    """Update the version in the .env file."""
    env_path = find_project_root() / ".env"
    if not env_path.exists():
        # Create the file if it doesn't exist
        with open(env_path, 'w') as f:
            f.write(f"# QCMD Environment Variables\n")
            f.write(f"QCMD_VERSION={new_version}\n")
        return
    
    # Read the current content
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Check if the version line exists
    version_updated = False
    for i, line in enumerate(lines):
        if line.strip().startswith('QCMD_VERSION='):
            lines[i] = f"QCMD_VERSION={new_version}\n"
            version_updated = True
            break
    
    # If not found, add it
    if not version_updated:
        lines.append(f"QCMD_VERSION={new_version}\n")
    
    # Write the updated content
    with open(env_path, 'w') as f:
        f.writelines(lines)

def update_pyproject_toml(new_version: str) -> None:
    """Update the version in pyproject.toml for backward compatibility."""
    toml_path = find_project_root() / "pyproject.toml"
    if not toml_path.exists():
        print(f"Warning: pyproject.toml not found at {toml_path}")
        return
    
    # Read the current content
    with open(toml_path, 'r') as f:
        lines = f.readlines()
    
    # Update the version line
    version_updated = False
    for i, line in enumerate(lines):
        if re.match(r'version\s*=\s*["\']\d+\.\d+\.\d+["\']', line.strip()):
            lines[i] = re.sub(r'(version\s*=\s*["\']\d+\.\d+\.\d+["\'])', f'version = "{new_version}"', line)
            version_updated = True
            break
    
    if not version_updated:
        print(f"Warning: Could not find version line in pyproject.toml")
        return
    
    # Write the updated content
    with open(toml_path, 'w') as f:
        f.writelines(lines)

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Bump the QCMD version number")
    parser.add_argument('bump_type', choices=['major', 'minor', 'patch'],
                        help="Type of version bump to perform")
    parser.add_argument('--legacy', action='store_true',
                        help="Also update version in legacy files for backward compatibility")
    parser.add_argument('--version', action='store_true',
                        help="Show the current version and exit")
    parser.add_argument('--set', metavar='VERSION',
                        help="Set the version to a specific value")
    
    args = parser.parse_args()
    
    try:
        current_version = read_current_version()
        
        if args.version:
            print(f"Current version: {current_version}")
            return
        
        if args.set:
            # Validate the format
            if not re.match(r'^\d+\.\d+\.\d+$', args.set):
                print(f"Error: Invalid version format: {args.set}. Expected format: x.y.z")
                return
            new_version = args.set
        else:
            new_version = bump_version(current_version, args.bump_type)
        
        print(f"Bumping version: {current_version} -> {new_version}")
        
        # Update the .env file
        update_env_file(new_version)
        print(f"Updated version in .env")
        
        # Update legacy files if requested
        if args.legacy:
            update_pyproject_toml(new_version)
            print(f"Updated version in pyproject.toml")
            
        print(f"Version bump complete!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 