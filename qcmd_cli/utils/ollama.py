def is_ollama_running():
    """
    Check if the Ollama API is running and accessible.
    
    Returns:
        bool: True if the Ollama API is running, False otherwise
    """
    from qcmd_cli.config.constants import OLLAMA_API
    import requests
    
    try:
        response = requests.get(f"{OLLAMA_API}/tags", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False 