#!/bin/bash
# TaskCompleted hook - runs when a task is being marked complete
# Exit code 2 = prevent completion and send feedback
# Exit code 0 = allow completion

ERRORS=""

# Check for Python linting issues
if [ -d "devops-mcp" ]; then
    if command -v black &> /dev/null; then
        if ! black --check --quiet devops-mcp/ 2>/dev/null; then
            ERRORS="${ERRORS}\n- Black formatting issues in devops-mcp/. Run: black devops-mcp/"
        fi
    fi

    if command -v ruff &> /dev/null; then
        if ! ruff check --quiet devops-mcp/ 2>/dev/null; then
            ERRORS="${ERRORS}\n- Ruff linting issues in devops-mcp/. Run: ruff check devops-mcp/"
        fi
    fi
fi

# Check for shell script syntax errors in modified files
for script in $(git diff --name-only HEAD 2>/dev/null | grep '\.sh$'); do
    if [ -f "$script" ]; then
        if ! bash -n "$script" 2>/dev/null; then
            ERRORS="${ERRORS}\n- Shell syntax error in $script"
        fi
    fi
done

# Check for invalid JSON in modified workflow files
for jsonfile in $(git diff --name-only HEAD 2>/dev/null | grep '\.json$'); do
    if [ -f "$jsonfile" ]; then
        if ! python3 -m json.tool "$jsonfile" > /dev/null 2>&1; then
            ERRORS="${ERRORS}\n- Invalid JSON in $jsonfile"
        fi
    fi
done

# Check for accidentally committed secrets
for file in $(git diff --cached --name-only 2>/dev/null); do
    if [ -f "$file" ]; then
        if grep -qiE "(password|secret|api_key|private_key)\s*[:=]\s*['\"][^'\"]+['\"]" "$file" 2>/dev/null; then
            ERRORS="${ERRORS}\n- Possible hardcoded secret in $file"
        fi
    fi
done

if [ -n "$ERRORS" ]; then
    echo "Task cannot be completed. Fix these issues first:"
    echo -e "$ERRORS"
    exit 2
fi

# All checks passed
exit 0
