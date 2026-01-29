#!/bin/bash
# =============================================================================
# Skills Consolidation Script
# =============================================================================
# Organizes extracted skills into the standard structure and generates manifest.
#
# Usage:
#   ./consolidate-skills.sh                    # Uses ~/flowmetrics-skills
#   ./consolidate-skills.sh --dir ~/skills     # Custom directory
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${GREEN}[CONSOLIDATE]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
info() { echo -e "${CYAN}[INFO]${NC} $1"; }

# Default directory
SKILLS_DIR="${HOME}/flowmetrics-skills"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dir|-d)
            SKILLS_DIR="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║           Skills Consolidation Tool                          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Ensure directory exists
if [ ! -d "$SKILLS_DIR" ]; then
    error "Skills directory not found: $SKILLS_DIR"
    echo "Run extract-skills.sh first"
    exit 1
fi

# =============================================================================
# 1. Parse global .windsurfrules into skills
# =============================================================================

GLOBAL_RULES="$SKILLS_DIR/extracted/global-windsurfrules.md"

if [ -f "$GLOBAL_RULES" ]; then
    info "=== Parsing global .windsurfrules ==="
    
    # Create a Python script to parse and split rules
    python3 << 'PYTHON_SCRIPT'
import os
import re
import sys

skills_dir = os.environ.get('SKILLS_DIR', os.path.expanduser('~/flowmetrics-skills'))
rules_file = f"{skills_dir}/extracted/global-windsurfrules.md"

if not os.path.exists(rules_file):
    print("No global rules file found")
    sys.exit(0)

with open(rules_file, 'r') as f:
    content = f.read()

# Common section patterns to extract
patterns = {
    # Document generation
    r'(?i)(docx|word|document)': ('documents/docx', 'Word Document Generation'),
    r'(?i)(xlsx|excel|spreadsheet)': ('documents/xlsx', 'Excel Spreadsheet Generation'),
    r'(?i)(pptx|powerpoint|presentation|slides)': ('documents/pptx', 'PowerPoint Presentations'),
    r'(?i)(pdf)': ('documents/pdf', 'PDF Generation'),
    
    # Patterns
    r'(?i)(svelte|sveltekit)': ('patterns/sveltekit', 'SvelteKit Patterns'),
    r'(?i)(postgres|postgresql|database|sql)': ('patterns/postgres', 'PostgreSQL Patterns'),
    r'(?i)(python)': ('patterns/python', 'Python Patterns'),
    r'(?i)(typescript|ts)': ('patterns/typescript', 'TypeScript Patterns'),
    
    # Integrations
    r'(?i)(n8n|workflow)': ('integrations/n8n', 'n8n Workflows'),
    r'(?i)(carbone|template)': ('integrations/carbone', 'Carbone Templates'),
    r'(?i)(metabase|analytics)': ('integrations/metabase', 'Metabase Analytics'),
    r'(?i)(supabase)': ('integrations/supabase', 'Supabase Integration'),
    r'(?i)(azure)': ('integrations/azure', 'Azure Integration'),
    
    # Data processing
    r'(?i)(sftp|ftp)': ('data/sftp', 'SFTP Processing'),
    r'(?i)(csv|parsing)': ('data/csv', 'CSV Processing'),
    r'(?i)(validation|schema)': ('data/validation', 'Data Validation'),
    
    # Agents
    r'(?i)(ralph|autonomous|agent)': ('agents/ralph', 'Ralph Autonomous Agent'),
}

# Try to split content by headers
sections = re.split(r'\n#{1,2}\s+', content)

extracted = {}

for section in sections:
    if not section.strip():
        continue
    
    # Check which category this section belongs to
    for pattern, (path, name) in patterns.items():
        if re.search(pattern, section[:500]):  # Check first 500 chars
            if path not in extracted:
                extracted[path] = {
                    'name': name,
                    'content': []
                }
            extracted[path]['content'].append(section)
            break

# Write extracted skills
for path, data in extracted.items():
    full_path = f"{skills_dir}/{path}"
    os.makedirs(full_path, exist_ok=True)
    
    skill_file = f"{full_path}/SKILL.md"
    
    # Don't overwrite existing skills
    if os.path.exists(skill_file):
        skill_file = f"{full_path}/SKILL-extracted.md"
    
    with open(skill_file, 'w') as f:
        f.write(f"# {data['name']}\n\n")
        f.write("> Extracted from .windsurfrules\n\n")
        f.write('\n\n---\n\n'.join(data['content']))
    
    print(f"  Created: {path}/SKILL.md")

print(f"\nExtracted {len(extracted)} skill categories from .windsurfrules")
PYTHON_SCRIPT

fi

# =============================================================================
# 2. Process Claude Project instructions
# =============================================================================

CLAUDE_PROJECTS="$SKILLS_DIR/extracted/claude-projects"

if [ -d "$CLAUDE_PROJECTS" ]; then
    info "=== Processing Claude Project instructions ==="
    
    for project_dir in "$CLAUDE_PROJECTS"/*; do
        if [ -d "$project_dir" ]; then
            project_name=$(basename "$project_dir")
            log "Processing project: $project_name"
            
            # Look for instruction files
            for file in "$project_dir"/*.md "$project_dir"/*.txt; do
                if [ -f "$file" ]; then
                    dest="$SKILLS_DIR/extracted/claude-instructions/${project_name}-$(basename "$file")"
                    mkdir -p "$(dirname "$dest")"
                    cp "$file" "$dest"
                    echo "  Copied: $(basename "$file")"
                fi
            done
        fi
    done
fi

# =============================================================================
# 3. Create skill templates for common categories
# =============================================================================

info "=== Creating skill templates ==="

# Create template for any missing categories
CATEGORIES=(
    "documents/docx:Word Document Generation:Create and edit Word documents"
    "documents/xlsx:Excel Spreadsheet:Create spreadsheets with formulas and charts"
    "documents/pptx:PowerPoint:Create presentations"
    "documents/pdf:PDF Generation:Create and fill PDF documents"
    "patterns/sveltekit:SvelteKit:SvelteKit component and routing patterns"
    "patterns/postgres:PostgreSQL:Database design and query patterns"
    "patterns/python:Python:Python coding patterns"
    "patterns/typescript:TypeScript:TypeScript patterns"
    "integrations/n8n:n8n Workflows:Workflow automation patterns"
    "integrations/carbone:Carbone:Template-based document generation"
    "integrations/metabase:Metabase:Analytics and dashboards"
    "integrations/slack:Slack:Slack notifications and bots"
    "data/sftp:SFTP Processing:File transfer and processing"
    "data/validation:Data Validation:Schema validation patterns"
    "data/transformation:Data Transformation:ETL patterns"
    "agents/ralph:Ralph Agent:Autonomous development agent"
    "prompts/analysis:Analysis Prompts:Data analysis prompt templates"
    "prompts/writing:Writing Prompts:Content generation templates"
)

for category in "${CATEGORIES[@]}"; do
    IFS=':' read -r path name description <<< "$category"
    
    skill_dir="$SKILLS_DIR/$path"
    skill_file="$skill_dir/SKILL.md"
    
    if [ ! -f "$skill_file" ]; then
        mkdir -p "$skill_dir"
        cat > "$skill_file" << EOF
# $name

> $description

## Overview

<!-- Add overview of this skill -->

## Usage

<!-- When to use this skill -->

## Patterns

<!-- Common patterns and examples -->

## Examples

<!-- Code or configuration examples -->

## Notes

<!-- Additional notes and gotchas -->
EOF
        echo "  Created template: $path/SKILL.md"
    fi
done

# =============================================================================
# 4. Generate manifest.json
# =============================================================================

info "=== Generating manifest.json ==="

python3 << 'PYTHON_SCRIPT'
import os
import json
from datetime import datetime
from pathlib import Path

skills_dir = os.environ.get('SKILLS_DIR', os.path.expanduser('~/flowmetrics-skills'))
skills_dir = Path(skills_dir)

skills = []
categories = set()

# Scan for SKILL.md files
for skill_file in skills_dir.rglob('SKILL.md'):
    rel_path = skill_file.parent.relative_to(skills_dir)
    parts = rel_path.parts
    
    if len(parts) >= 2 and parts[0] != 'extracted':
        category = parts[0]
        skill_name = parts[1]
        
        categories.add(category)
        
        # Read first paragraph as description
        content = skill_file.read_text()
        lines = content.split('\n')
        description = ''
        for line in lines[1:]:  # Skip title
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('>'):
                description = line[:200]
                break
        
        # Extract triggers from content
        triggers = []
        title = lines[0].replace('#', '').strip().lower() if lines else skill_name
        triggers.append(skill_name)
        triggers.extend([w for w in title.split() if len(w) > 2])
        
        skills.append({
            'id': str(rel_path),
            'name': title.title() if title else skill_name.replace('-', ' ').title(),
            'category': category,
            'path': str(rel_path),
            'description': description,
            'triggers': list(set(triggers))[:5],
        })

manifest = {
    'version': '1.0.0',
    'updated_at': datetime.utcnow().isoformat() + 'Z',
    'skills': sorted(skills, key=lambda x: (x['category'], x['name'])),
    'categories': sorted(categories),
}

manifest_path = skills_dir / 'manifest.json'
with open(manifest_path, 'w') as f:
    json.dump(manifest, f, indent=2)

print(f"Generated manifest with {len(skills)} skills in {len(categories)} categories")
print(f"Saved to: {manifest_path}")
PYTHON_SCRIPT

# =============================================================================
# 5. Create index README
# =============================================================================

info "=== Creating README ==="

cat > "$SKILLS_DIR/README.md" << 'EOF'
# FlowMetrics Skills Library

A centralized collection of skills, patterns, and agents for use with Claude, Windsurf, and the DevOps MCP server.

## Structure

```
skills/
├── manifest.json           # Auto-generated skill index
├── documents/              # Document generation skills
│   ├── docx/
│   ├── xlsx/
│   ├── pptx/
│   └── pdf/
├── patterns/               # Coding patterns
│   ├── sveltekit/
│   ├── postgres/
│   ├── python/
│   └── typescript/
├── integrations/           # External service integrations
│   ├── n8n/
│   ├── carbone/
│   ├── metabase/
│   └── slack/
├── data/                   # Data processing skills
│   ├── sftp/
│   ├── validation/
│   └── transformation/
├── agents/                 # Autonomous agent configs
│   └── ralph/
├── prompts/                # Prompt templates
│   ├── analysis/
│   └── writing/
└── extracted/              # Raw extracted content
```

## Usage

### With DevOps MCP Server

The MCP server auto-discovers skills from this directory:

```bash
export SKILLS_DIR=/path/to/this/directory
python -m devops_mcp
```

Then Claude can:
- `skills_list` - List all skills
- `skills_search("excel")` - Find relevant skills
- `skills_get("documents/xlsx")` - Read skill content
- `skills_recommend("create quarterly report")` - Get suggestions

### With Windsurf

Generate a `.windsurfrules` file from skills:

```bash
./scripts/generate-windsurfrules.sh > ~/.windsurfrules
```

### With Claude Projects

Copy relevant skill content into Claude Project instructions.

## Adding Skills

1. Create a new directory under the appropriate category
2. Add a `SKILL.md` file with the skill documentation
3. Re-run `./consolidate-skills.sh` to update the manifest

### SKILL.md Template

```markdown
# Skill Name

> Brief description

## Overview

What this skill is for.

## Usage

When and how to use this skill.

## Patterns

Common patterns and approaches.

## Examples

Code or configuration examples.
```

## Maintenance

- **Extract**: `./scripts/extract-skills.sh` - Pull from Windsurf/Claude
- **Consolidate**: `./scripts/consolidate-skills.sh` - Organize and generate manifest
- **Sync**: `./scripts/sync-skills.sh` - Push to DevOps Agent VM
EOF

# =============================================================================
# 6. Summary
# =============================================================================

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  Consolidation Complete                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Skills directory: $SKILLS_DIR"
echo ""
echo "Generated files:"
echo "  - manifest.json (skill index for MCP)"
echo "  - README.md (documentation)"
echo "  - Category templates"
echo ""
echo "Next steps:"
echo "  1. Review and edit skills in each category"
echo "  2. Add your custom skills/agents"
echo "  3. Configure DevOps MCP: export SKILLS_DIR=$SKILLS_DIR"
echo "  4. Sync to DevOps Agent VM if needed"
echo ""
