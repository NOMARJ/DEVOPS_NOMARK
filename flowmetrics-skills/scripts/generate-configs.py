#!/usr/bin/env python3
"""
Generate configuration files from skills repository.

Outputs:
- manifest.json - Skill index for MCP server
- .windsurfrules - Combined rules for Windsurf
- claude-project-instructions.md - Instructions for Claude Projects
- CLAUDE.md - Master context file
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional

SKILLS_DIR = Path(__file__).parent.parent
OUTPUT_DIR = SKILLS_DIR


def parse_skill_md(path: Path) -> dict:
    """Parse a SKILL.md file and extract metadata."""
    content = path.read_text()
    
    # Extract title (first # heading)
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1) if title_match else path.parent.name
    
    # Extract description (first > blockquote or first paragraph)
    desc_match = re.search(r'^>\s*(.+)$', content, re.MULTILINE)
    if desc_match:
        description = desc_match.group(1)
    else:
        # First non-empty line after title
        lines = content.split('\n')
        description = ""
        for line in lines[1:]:
            line = line.strip()
            if line and not line.startswith('#'):
                description = line[:200]
                break
    
    # Extract triggers from "When to Use" section
    triggers = []
    when_match = re.search(r'##\s*When to Use\s*\n([\s\S]*?)(?=\n##|\Z)', content)
    if when_match:
        triggers_text = when_match.group(1)
        triggers = re.findall(r'[-*]\s*(.+)', triggers_text)
        triggers = [t.strip().lower() for t in triggers[:5]]
    
    # Extract prerequisites
    prereqs = []
    prereq_match = re.search(r'##\s*Prerequisites\s*\n([\s\S]*?)(?=\n##|\Z)', content)
    if prereq_match:
        prereqs_text = prereq_match.group(1)
        prereqs = re.findall(r'[-*]\s*(.+)', prereqs_text)
    
    return {
        "title": title,
        "description": description,
        "triggers": triggers,
        "prerequisites": prereqs,
        "content": content,
    }


def generate_manifest() -> dict:
    """Generate manifest.json from skills directory."""
    skills = []
    categories = set()
    
    # Walk through category directories
    for category_dir in SKILLS_DIR.iterdir():
        if not category_dir.is_dir():
            continue
        if category_dir.name.startswith('.') or category_dir.name == 'scripts':
            continue
        
        categories.add(category_dir.name)
        
        # Walk through skill directories
        for skill_dir in category_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            
            parsed = parse_skill_md(skill_md)
            
            skills.append({
                "id": f"{category_dir.name}/{skill_dir.name}",
                "name": parsed["title"],
                "category": category_dir.name,
                "path": str(skill_dir.relative_to(SKILLS_DIR)),
                "description": parsed["description"],
                "triggers": parsed["triggers"],
                "prerequisites": parsed["prerequisites"],
            })
    
    manifest = {
        "version": "1.0.0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "skills": sorted(skills, key=lambda s: s["id"]),
        "categories": sorted(categories),
        "total_skills": len(skills),
    }
    
    return manifest


def generate_windsurfrules(manifest: dict) -> str:
    """Generate .windsurfrules from manifest."""
    
    rules = []
    rules.append("# FlowMetrics Development Rules")
    rules.append("# Auto-generated from skills repository")
    rules.append(f"# Generated: {manifest['generated_at']}")
    rules.append("")
    
    # Project context
    rules.append("## Project Context")
    rules.append("")
    rules.append("FlowMetrics is a multi-tenant BPO analytics platform for Australian fund managers.")
    rules.append("Stack: SvelteKit + Python + PostgreSQL + n8n + Azure")
    rules.append("")
    
    # Critical rules
    rules.append("## Critical Rules")
    rules.append("")
    rules.append("1. **Fix Before Create**: Always check existing implementation before creating new files")
    rules.append("2. **Atomic Commits**: One commit per logical change")
    rules.append("3. **Type Safety**: Use TypeScript strict mode, Zod for validation")
    rules.append("4. **RLS Required**: All multi-tenant tables need Row Level Security")
    rules.append("")
    
    # Skills reference
    rules.append("## Available Skills")
    rules.append("")
    rules.append("Read the relevant SKILL.md before creating artifacts:")
    rules.append("")
    
    for category in manifest["categories"]:
        category_skills = [s for s in manifest["skills"] if s["category"] == category]
        if category_skills:
            rules.append(f"### {category.title()}")
            for skill in category_skills:
                rules.append(f"- `{skill['path']}/SKILL.md` - {skill['description'][:60]}...")
            rules.append("")
    
    # Patterns section
    rules.append("## Code Patterns")
    rules.append("")
    rules.append("### SvelteKit")
    rules.append("- Use `+page.server.ts` for data loading")
    rules.append("- Use Superforms for form handling")
    rules.append("- Use `$lib` alias for imports")
    rules.append("")
    rules.append("### Database")
    rules.append("- UUID primary keys: `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`")
    rules.append("- Always add `created_at` and `updated_at` timestamps")
    rules.append("- Use snake_case for column names")
    rules.append("")
    rules.append("### Python")
    rules.append("- Type hints on all functions")
    rules.append("- Use dataclasses or Pydantic for data structures")
    rules.append("- Async functions for I/O operations")
    rules.append("")
    
    return "\n".join(rules)


def generate_claude_instructions(manifest: dict) -> str:
    """Generate Claude Project instructions from manifest."""
    
    lines = []
    lines.append("# FlowMetrics Project Instructions")
    lines.append("")
    lines.append("## Context")
    lines.append("")
    lines.append("You are working on FlowMetrics, a multi-tenant BPO analytics platform for Australian fund managers.")
    lines.append("")
    lines.append("**Stack**: SvelteKit + TypeScript + Python + PostgreSQL + n8n + Azure")
    lines.append("")
    lines.append("## Critical Rule: Fix Before Create")
    lines.append("")
    lines.append("```")
    lines.append("CHECK  → Does something already exist for this task?")
    lines.append("FIX    → If exists but broken, fix it")
    lines.append("ENHANCE → If exists but incomplete, enhance it")
    lines.append("CREATE → ONLY if nothing exists at all")
    lines.append("```")
    lines.append("")
    
    # Skills by category
    lines.append("## Skills Reference")
    lines.append("")
    lines.append("When working on specific tasks, refer to these skills:")
    lines.append("")
    
    skill_table = [
        "| Task | Skill | Description |",
        "|------|-------|-------------|",
    ]
    
    for skill in manifest["skills"][:20]:  # Limit for Claude Projects
        skill_table.append(f"| {skill['triggers'][0] if skill['triggers'] else skill['category']} | `{skill['id']}` | {skill['description'][:40]}... |")
    
    lines.extend(skill_table)
    lines.append("")
    
    # Conventions
    lines.append("## Conventions")
    lines.append("")
    lines.append("### Commits")
    lines.append("- Format: `feat(scope): description` or `fix(scope): description`")
    lines.append("- One logical change per commit")
    lines.append("")
    lines.append("### Code Style")
    lines.append("- TypeScript: Strict mode, Zod validation, type imports")
    lines.append("- Python: Type hints, async/await, dataclasses")
    lines.append("- SQL: UUID PKs, snake_case, RLS policies")
    lines.append("")
    
    return "\n".join(lines)


def generate_master_claude_md(manifest: dict) -> str:
    """Generate the master CLAUDE.md file."""
    
    lines = []
    lines.append("# CLAUDE.md - FlowMetrics Project Context")
    lines.append("")
    lines.append("> This file is automatically read by Claude Code to understand the project.")
    lines.append(f"> Generated: {manifest['generated_at']}")
    lines.append("")
    
    lines.append("## Project Overview")
    lines.append("")
    lines.append("**FlowMetrics** is a multi-tenant BPO analytics platform serving Australian fund managers.")
    lines.append("")
    lines.append("- **Business**: Process distribution flow data from wealth platforms (Asgard, Netwealth, Hub24)")
    lines.append("- **Clients**: Mid-market fund managers ($20-40k annual contracts)")
    lines.append("- **Differentiator**: Self-service client portals + BPO operations oversight")
    lines.append("")
    
    lines.append("## Tech Stack")
    lines.append("")
    lines.append("| Layer | Technology |")
    lines.append("|-------|------------|")
    lines.append("| Frontend | SvelteKit + TypeScript + Tailwind CSS |")
    lines.append("| Backend | Python (Azure Functions) |")
    lines.append("| Database | PostgreSQL with Row-Level Security |")
    lines.append("| Workflows | n8n (self-hosted) |")
    lines.append("| Analytics | Self-hosted Metabase |")
    lines.append("| Infrastructure | Azure (Container Apps, Storage, Key Vault) |")
    lines.append("| Reports | Carbone (template-based generation) |")
    lines.append("")
    
    lines.append("## ⚠️ Critical: Fix Before Create")
    lines.append("")
    lines.append("```")
    lines.append("CHECK  → Does something already exist?")
    lines.append("FIX    → If broken, fix it")
    lines.append("ENHANCE → If incomplete, enhance it")
    lines.append("CREATE → ONLY if nothing exists")
    lines.append("```")
    lines.append("")
    lines.append("**Always search the codebase before creating new files.**")
    lines.append("")
    
    lines.append("## Skills Available")
    lines.append("")
    lines.append(f"This project has **{manifest['total_skills']} skills** across {len(manifest['categories'])} categories:")
    lines.append("")
    
    for category in manifest["categories"]:
        category_skills = [s for s in manifest["skills"] if s["category"] == category]
        lines.append(f"### {category.title()} ({len(category_skills)} skills)")
        for skill in category_skills:
            lines.append(f"- **{skill['name']}** (`{skill['path']}/SKILL.md`): {skill['description'][:50]}...")
        lines.append("")
    
    lines.append("## How to Use Skills")
    lines.append("")
    lines.append("1. **Before creating documents**: Read `documents/*/SKILL.md`")
    lines.append("2. **Before writing code**: Read `patterns/*/SKILL.md`")
    lines.append("3. **Before integrating services**: Read `integrations/*/SKILL.md`")
    lines.append("4. **For autonomous tasks**: Read `agents/*/SKILL.md`")
    lines.append("")
    
    lines.append("## Repository Structure")
    lines.append("")
    lines.append("```")
    lines.append("├── apps/")
    lines.append("│   ├── admin-portal/        # BPO staff portal (SvelteKit)")
    lines.append("│   └── client-portal/       # Client-facing portal (SvelteKit)")
    lines.append("├── packages/")
    lines.append("│   ├── shared/              # Shared TypeScript utilities")
    lines.append("│   └── database/            # Database types and migrations")
    lines.append("├── functions/               # Azure Functions (Python)")
    lines.append("├── infrastructure/          # Terraform IaC")
    lines.append("├── skills/                  # This skills repository")
    lines.append("└── ralph/                   # Autonomous development PRDs")
    lines.append("```")
    lines.append("")
    
    lines.append("## Key Patterns")
    lines.append("")
    lines.append("### Multi-Tenancy")
    lines.append("- Every table has `tenant_id` column")
    lines.append("- RLS policies enforce isolation")
    lines.append("- Set `app.current_tenant` before queries")
    lines.append("")
    lines.append("### API Design")
    lines.append("- RESTful endpoints in `/api/*`")
    lines.append("- Zod validation on all inputs")
    lines.append("- Consistent error format: `{error: {code, message, details}}`")
    lines.append("")
    lines.append("### Testing")
    lines.append("- Unit tests: `*.test.ts` co-located with code")
    lines.append("- Integration tests: `tests/integration/`")
    lines.append("- Use test tenant for database tests")
    lines.append("")
    
    return "\n".join(lines)


def main():
    """Generate all config files."""
    print("🔍 Scanning skills directory...")
    manifest = generate_manifest()
    
    print(f"📦 Found {manifest['total_skills']} skills in {len(manifest['categories'])} categories")
    
    # Write manifest.json
    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"✅ Generated {manifest_path}")
    
    # Write .windsurfrules
    windsurfrules = generate_windsurfrules(manifest)
    windsurfrules_path = OUTPUT_DIR / ".windsurfrules"
    with open(windsurfrules_path, "w") as f:
        f.write(windsurfrules)
    print(f"✅ Generated {windsurfrules_path}")
    
    # Write claude-project-instructions.md
    claude_instructions = generate_claude_instructions(manifest)
    claude_path = OUTPUT_DIR / "claude-project-instructions.md"
    with open(claude_path, "w") as f:
        f.write(claude_instructions)
    print(f"✅ Generated {claude_path}")
    
    # Write CLAUDE.md
    claude_md = generate_master_claude_md(manifest)
    claude_md_path = OUTPUT_DIR / "CLAUDE.md"
    with open(claude_md_path, "w") as f:
        f.write(claude_md)
    print(f"✅ Generated {claude_md_path}")
    
    print("")
    print("🎉 Done! Copy these files to your projects:")
    print(f"   - {windsurfrules_path} → Your project root (for Windsurf)")
    print(f"   - {claude_path} → Claude Project instructions")
    print(f"   - {manifest_path} → Set SKILLS_DIR for MCP server")


if __name__ == "__main__":
    main()
