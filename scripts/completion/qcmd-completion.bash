#!/usr/bin/env bash
# qcmd bash completion script

_qcmd_completion() {
    local cur prev opts base models cmds
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Basic options
    opts="--help -h --model -m --list-models --list -l --execute -e --yes -y --dry-run -d --analyze -a --auto -A --max-attempts --temperature -t --no-color --examples --save-output --history --shell"

    # Handle special cases
    case ${prev} in
        --model|-m)
            # Get available models from Ollama (if ollama is running)
            if command -v curl &> /dev/null; then
                models=$(curl -s http://127.0.0.1:11434/api/tags 2>/dev/null | grep -o '"name":"[^"]*' | sed 's/"name":"//g' 2>/dev/null)
                if [ -n "$models" ]; then
                    COMPREPLY=( $(compgen -W "${models}" -- ${cur}) )
                    return 0
                fi
            fi
            # Fallback to common models
            models="qwen2.5-coder:0.5b llama2:7b mistral:7b deepseek-coder"
            COMPREPLY=( $(compgen -W "${models}" -- ${cur}) )
            return 0
            ;;
        --save-output)
            # Complete with files
            COMPREPLY=( $(compgen -f ${cur}) )
            return 0
            ;;
        --temperature|-t)
            # Suggest common temperature values
            temps="0.1 0.2 0.5 0.7 1.0"
            COMPREPLY=( $(compgen -W "${temps}" -- ${cur}) )
            return 0
            ;;
        --max-attempts)
            # Suggest common max attempts values
            attempts="1 2 3 5 10"
            COMPREPLY=( $(compgen -W "${attempts}" -- ${cur}) )
            return 0
            ;;
    esac

    # If input starts with a dash, suggest options
    if [[ ${cur} == -* ]]; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi

    # If no option is being completed, suggest from history (last 20 most popular commands)
    QCMD_HISTORY_FILE="${HOME}/.qcmd_history"
    if [ -f "$QCMD_HISTORY_FILE" ]; then
        # Extract most common commands from history, excluding options
        cmds=$(grep -v '^-' "$QCMD_HISTORY_FILE" | sort | uniq -c | sort -nr | head -20 | sed 's/^ *[0-9]* *//' | sed 's/^"//' | sed 's/"$//')
        COMPREPLY=( $(compgen -W "${cmds}" -- ${cur}) )
    fi

    # If no completion found and we're at the beginning of the command, suggest common tasks
    if [ ${#COMPREPLY[@]} -eq 0 ] && [ "$COMP_CWORD" -eq 1 ]; then
        common_tasks=(
            "\"list all files\""
            "\"find large files\""
            "\"check disk usage\""
            "\"monitor cpu usage\""
            "\"show memory usage\""
            "\"search for files containing\""
            "\"create backup of\""
            "\"find processes using\""
            "\"compress directory\""
            "\"extract archive\""
        )
        COMPREPLY=( $(compgen -W "${common_tasks[*]}" -- ${cur}) )
    fi

    return 0
}

# Register the completion function
complete -F _qcmd_completion qcmd 