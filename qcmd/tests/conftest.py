import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

@pytest.fixture(autouse=True)
def setup_logging():
    """Create a temporary .qcmd directory for logging during tests."""
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    qcmd_dir = os.path.join(temp_dir, '.qcmd')
    os.makedirs(qcmd_dir, exist_ok=True)
    
    # Set the HOME environment variable to our temporary directory
    original_home = os.environ.get('HOME')
    os.environ['HOME'] = temp_dir
    
    yield
    
    # Cleanup
    if original_home:
        os.environ['HOME'] = original_home
    shutil.rmtree(temp_dir)

@pytest.fixture(autouse=True)
def mock_ollama_api():
    """Mock the Ollama API responses for all tests."""
    with patch('qcmd_cli.core.command_generator.requests.get') as mock_get, \
         patch('qcmd_cli.core.command_generator.requests.post') as mock_post:
        # Mock list_models response
        mock_get.return_value.json.return_value = {
            "models": [
                {"name": "qwen2.5-coder:0.5b"},
                {"name": "llama3:latest"}
            ]
        }
        mock_get.return_value.raise_for_status.return_value = None
        
        # Mock generate_command response
        mock_post.return_value.json.return_value = {
            "response": "ls -la",
            "done": True
        }
        mock_post.return_value.raise_for_status.return_value = None
        
        yield mock_get, mock_post 