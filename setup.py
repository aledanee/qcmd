#!/usr/bin/env python3
"""
Setup script for qcmd.
"""

from setuptools import setup, find_packages
import os

# Read the contents of README.md
with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

# Read requirements.txt
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name="qcmd",
    version="1.0.0",
    description="AI-powered Command Generator using Local LLMs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="",
    author_email="",
    url="https://github.com/aledanee/qcmd",
    packages=find_packages(),
    scripts=['qcmd'],
    data_files=[
        ('share/bash-completion/completions', ['qcmd-completion.bash']),
    ],
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Topic :: Utilities",
        "Environment :: Console",
    ],
    python_requires='>=3.6',
) 