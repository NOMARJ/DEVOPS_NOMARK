#!/bin/bash
# =============================================================================
# Skills Extraction Script for macOS
# =============================================================================
# Extracts skills, agents, and configurations from:
# - Windsurf (.windsurfrules, MCP configs)
# - Claude Desktop (project instructions)
# - Local project files (CLAUDE.md, AGENTS.md)
#
# Usage:
#   ./extract-skills.sh                    # Interactive mode
#   ./extract-skills.sh --output ~/skills  # Specify output directory
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${GREEN}[EXTRACT]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
info() { echo -e "${CYAN}[INFO]${NC} $1"; }

# Default output directory
OUTPUT_DIR="${HOME}/flowmetrics-skills"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --output|-o)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [--output DIR]"
            echo "Extracts skills from Windsurf, Claude Desktop, and local projects"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║           FlowMetrics Skills Extraction Tool                 ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Create output directory structure
log "Creating skills directory structure at: $OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"/{documents,patterns,integrations,agents,data,prompts,extracted}

# =============================================================================
# 1. Extract from Windsurf
# =============================================================================

echo ""
info "=== Extracting from Windsurf ==="

# Windsurf config locations
WINDSURF_CONFIG_DIR="${HOME}/.windsurf"
WINDSURF_GLOBAL_RULES="${HOME}/.windsurfrules"
WINDSURF_STATE="${HOME}/Library/Application Support/Windsurf"

# Global .windsurfrules
if [ -f "$WINDSURF_GLOBAL_RULES" ]; then
    log "Found global .windsurfrules"
    cp "$WINDSURF_GLOBAL_RULES" "$OUTPUT_DIR/extracted/global-windsurfrules.md"
    echo "Copied: global .windsurfrules"
else
    warn "No global .windsurfrules found at $WINDSURF_GLOBAL_RULES"
fi

# Windsurf MCP configuration
WINDSURF_MCP_CONFIG="${WINDSURF_STATE}/mcp.json"
if [ -f "$WINDSURF_MCP_CONFIG" ]; then
    log "Found Windsurf MCP config"
    cp "$WINDSURF_MCP_CONFIG" "$OUTPUT_DIR/extracted/windsurf-mcp-config.json"
fi

# Windsurf settings
WINDSURF_SETTINGS="${WINDSURF_STATE}/settings.json"
if [ -f "$WINDSURF_SETTINGS" ]; then
    log "Found Windsurf settings"
    cp "$WINDSURF_SETTINGS" "$OUTPUT_DIR/extracted/windsurf-settings.json"
fi

# =============================================================================
# 2. Extract from Claude Desktop
# =============================================================================

echo ""
info "=== Extracting from Claude Desktop ==="

CLAUDE_CONFIG_DIR="${HOME}/Library/Application Support/Claude"

# Claude Desktop config
if [ -f "$CLAUDE_CONFIG_DIR/claude_desktop_config.json" ]; then
    log "Found Claude Desktop config"
    cp "$CLAUDE_CONFIG_DIR/claude_desktop_config.json" "$OUTPUT_DIR/extracted/claude-desktop-config.json"
fi

# Claude Projects (if accessible)
CLAUDE_PROJECTS_DIR="$CLAUDE_CONFIG_DIR/projects"
if [ -d "$CLAUDE_PROJECTS_DIR" ]; then
    log "Found Claude Projects directory"
    mkdir -p "$OUTPUT_DIR/extracted/claude-projects"
    cp -r "$CLAUDE_PROJECTS_DIR"/* "$OUTPUT_DIR/extracted/claude-projects/" 2>/dev/null || true
fi

# =============================================================================
# 3. Scan for project-level files
# =============================================================================

echo ""
info "=== Scanning for project-level skills ==="

# Common project directories to scan
SCAN_DIRS=(
    "${HOME}/CascadeProjects"
    "${HOME}/Projects"
    "${HOME}/Code"
    "${HOME}/Developer"
    "${HOME}/repos"
)

FOUND_FILES=()

for scan_dir in "${SCAN_DIRS[@]}"; do
    if [ -d "$scan_dir" ]; then
        log "Scanning: $scan_dir"
        
        # Find .windsurfrules files
        while IFS= read -r file; do
            if [ -n "$file" ]; then
                project_name=$(dirname "$file" | xargs basename)
                dest="$OUTPUT_DIR/extracted/projects/${project_name}-windsurfrules.md"
                mkdir -p "$(dirname "$dest")"
                cp "$file" "$dest"
                FOUND_FILES+=("$file")
                echo "  Found: $file"
            fi
        done < <(find "$scan_dir" -maxdepth 3 -name ".windsurfrules" 2>/dev/null)
        
        # Find CLAUDE.md files
        while IFS= read -r file; do
            if [ -n "$file" ]; then
                project_name=$(dirname "$file" | xargs basename)
                dest="$OUTPUT_DIR/extracted/projects/${project_name}-CLAUDE.md"
                mkdir -p "$(dirname "$dest")"
                cp "$file" "$dest"
                FOUND_FILES+=("$file")
                echo "  Found: $file"
            fi
        done < <(find "$scan_dir" -maxdepth 3 -name "CLAUDE.md" 2>/dev/null)
        
        # Find AGENTS.md files
        while IFS= read -r file; do
            if [ -n "$file" ]; then
                project_name=$(dirname "$file" | xargs basename)
                dest="$OUTPUT_DIR/extracted/projects/${project_name}-AGENTS.md"
                mkdir -p "$(dirname "$dest")"
                cp "$file" "$dest"
                FOUND_FILES+=("$file")
                echo "  Found: $file"
            fi
        done < <(find "$scan_dir" -maxdepth 3 -name "AGENTS.md" 2>/dev/null)
        
        # Find skills directories
        while IFS= read -r dir; do
            if [ -n "$dir" ]; then
                project_name=$(dirname "$dir" | xargs basename)
                dest="$OUTPUT_DIR/extracted/projects/${project_name}-skills"
                mkdir -p "$dest"
                cp -r "$dir"/* "$dest/" 2>/dev/null || true
                echo "  Found skills dir: $dir"
            fi
        done < <(find "$scan_dir" -maxdepth 3 -type d -name "skills" 2>/dev/null)
    fi
done

# =============================================================================
# 4. Generate manifest of extracted content
# =============================================================================

echo ""
info "=== Generating extraction manifest ==="

cat > "$OUTPUT_DIR/extracted/MANIFEST.md" << 'EOF'
# Extracted Skills Manifest

This directory contains skills, configurations, and agents extracted from your development environment.

## Contents

### From Windsurf
- `global-windsurfrules.md` - Global Windsurf rules
- `windsurf-mcp-config.json` - MCP server configurations
- `windsurf-settings.json` - Windsurf IDE settings

### From Claude Desktop
- `claude-desktop-config.json` - Claude Desktop configuration
- `claude-projects/` - Claude Project instructions (if available)

### From Projects
- `projects/` - Per-project configurations
  - `*-windsurfrules.md` - Project-specific Windsurf rules
  - `*-CLAUDE.md` - Project-specific Claude context
  - `*-AGENTS.md` - Project-specific agent conventions
  - `*-skills/` - Project-specific skills

## Next Steps

1. Review extracted content in this directory
2. Run the consolidation script to organize into the standard structure:
   ```bash
   ./consolidate-skills.sh
   ```

3. Edit and categorize skills as needed
4. Generate the manifest.json for MCP discovery:
   ```bash
   ./generate-manifest.sh
   ```

EOF

# Add file listing to manifest
echo "## Extracted Files" >> "$OUTPUT_DIR/extracted/MANIFEST.md"
echo "" >> "$OUTPUT_DIR/extracted/MANIFEST.md"
echo '```' >> "$OUTPUT_DIR/extracted/MANIFEST.md"
find "$OUTPUT_DIR/extracted" -type f -name "*.md" -o -name "*.json" | sort >> "$OUTPUT_DIR/extracted/MANIFEST.md"
echo '```' >> "$OUTPUT_DIR/extracted/MANIFEST.md"

# =============================================================================
# 5. Summary
# =============================================================================

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Extraction Complete                       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Output directory: $OUTPUT_DIR"
echo ""
echo "Files extracted: ${#FOUND_FILES[@]}"
echo ""
echo "Next steps:"
echo "  1. Review: $OUTPUT_DIR/extracted/"
echo "  2. Run: ./consolidate-skills.sh"
echo "  3. Customize skills in: $OUTPUT_DIR/{documents,patterns,agents,...}"
echo ""
