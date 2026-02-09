#!/bin/bash
# TeammateIdle hook - runs when a teammate is about to go idle
# Exit code 2 = send feedback and keep teammate working
# Exit code 0 = allow idle

# Check if there are uncommitted changes that need attention
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    echo "You have uncommitted changes. Please review and commit or discard before going idle."
    exit 2
fi

# Check if there are failing tests in the MCP server
if [ -d "devops-mcp" ]; then
    cd devops-mcp
    if command -v pytest &> /dev/null; then
        if ! pytest --quiet --no-header 2>/dev/null; then
            echo "Tests are failing in devops-mcp. Please investigate before going idle."
            exit 2
        fi
    fi
    cd ..
fi

# Check if terraform has validation errors
if [ -d "devops-agent/terraform" ]; then
    cd devops-agent/terraform
    if command -v terraform &> /dev/null; then
        if ! terraform validate -no-color 2>/dev/null; then
            echo "Terraform validation errors found. Please fix before going idle."
            exit 2
        fi
    fi
    cd ../..
fi

# All checks passed, teammate can go idle
exit 0
