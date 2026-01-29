#!/usr/bin/env python3
"""
Skill Migration Helper
======================
Extract and organize skills from various sources:
- Windsurf .windsurfrules files
- Claude Project instructions
- Existing documentation
- Code comments and docstrings

Usage:
    python migrate-skills.py --source windsurf --input ~/.windsurfrules
    python migrate-skills.py --source claude --input instructions.md
    python migrate-skills.py --source docs --input ./docs/
    python migrate-skills.py --interactive
"""

import os
import re
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class ExtractedSkill:
    """Represents a skill extracted from source."""
    name: str
    category: str
    description: str
    content: str
    source: str
    triggers: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    confidence: float = 1.0  # How confident we are this is a distinct skill


def parse_windsurfrules(content: str) -> List[ExtractedSkill]:
    """Extract skills from a .windsurfrules file."""
    skills = []
    
    # Split by ## headings
    sections = re.split(r'\n##\s+', content)
    
    for section in sections[1:]:  # Skip content before first ##
        lines = section.strip().split('\n')
        if not lines:
            continue
        
        title = lines[0].strip()
        body = '\n'.join(lines[1:]).strip()
        
        # Determine category from title
        category = categorize_skill(title, body)
        
        # Extract description (first paragraph)
        paragraphs = body.split('\n\n')
        description = paragraphs[0] if paragraphs else ""
        
        # Extract triggers (keywords that might invoke this skill)
        triggers = extract_triggers(title, body)
        
        skills.append(ExtractedSkill(
            name=title,
            category=category,
            description=description[:200],
            content=f"# {title}\n\n{body}",
            source="windsurfrules",
            triggers=triggers,
        ))
    
    return skills


def parse_claude_instructions(content: str) -> List[ExtractedSkill]:
    """Extract skills from Claude Project instructions."""
    skills = []
    
    # Look for distinct sections
    sections = re.split(r'\n(?=#{1,2}\s+[A-Z])', content)
    
    for section in sections:
        if len(section.strip()) < 50:
            continue
        
        # Extract title
        title_match = re.match(r'^#{1,2}\s+(.+)$', section, re.MULTILINE)
        if not title_match:
            continue
        
        title = title_match.group(1).strip()
        body = section[title_match.end():].strip()
        
        # Skip meta sections
        if any(skip in title.lower() for skip in ['context', 'overview', 'introduction', 'about']):
            continue
        
        category = categorize_skill(title, body)
        triggers = extract_triggers(title, body)
        
        # First paragraph as description
        paragraphs = body.split('\n\n')
        description = paragraphs[0] if paragraphs else ""
        
        skills.append(ExtractedSkill(
            name=title,
            category=category,
            description=description[:200],
            content=f"# {title}\n\n{body}",
            source="claude_instructions",
            triggers=triggers,
        ))
    
    return skills


def parse_markdown_docs(path: Path) -> List[ExtractedSkill]:
    """Extract skills from markdown documentation files."""
    skills = []
    
    for md_file in path.rglob("*.md"):
        content = md_file.read_text()
        
        # Use filename as skill name if no title
        title_match = re.match(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else md_file.stem.replace('-', ' ').title()
        
        # Get first paragraph after title
        paragraphs = re.split(r'\n\n+', content)
        description = ""
        for p in paragraphs:
            if not p.startswith('#') and len(p.strip()) > 20:
                description = p.strip()[:200]
                break
        
        category = categorize_skill(title, content)
        triggers = extract_triggers(title, content)
        
        skills.append(ExtractedSkill(
            name=title,
            category=category,
            description=description,
            content=content,
            source=str(md_file),
            triggers=triggers,
        ))
    
    return skills


def categorize_skill(title: str, content: str) -> str:
    """Determine skill category from title and content."""
    text = f"{title} {content}".lower()
    
    # Category keywords
    categories = {
        "documents": ["word", "docx", "excel", "xlsx", "powerpoint", "pptx", "pdf", "document", "report", "template"],
        "patterns": ["pattern", "convention", "style", "code", "component", "typescript", "python", "sql"],
        "integrations": ["api", "webhook", "integration", "connect", "n8n", "metabase", "stripe", "azure", "supabase"],
        "agents": ["agent", "autonomous", "ralph", "automation", "workflow"],
        "data": ["data", "validation", "transform", "csv", "sftp", "etl", "quality"],
        "prompts": ["prompt", "template", "instruction", "analysis", "writing"],
    }
    
    scores = {cat: 0 for cat in categories}
    
    for cat, keywords in categories.items():
        for kw in keywords:
            if kw in text:
                scores[cat] += 1
    
    # Return highest scoring category, default to "patterns"
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "patterns"


def extract_triggers(title: str, content: str) -> List[str]:
    """Extract trigger keywords for the skill."""
    triggers = []
    
    # Add words from title
    title_words = re.findall(r'\b[a-z]{4,}\b', title.lower())
    triggers.extend(title_words[:3])
    
    # Look for "When to Use" section
    when_match = re.search(r'when to use[:\s]*\n([\s\S]*?)(?=\n#|\Z)', content, re.IGNORECASE)
    if when_match:
        when_text = when_match.group(1)
        # Extract bullet points
        bullets = re.findall(r'[-*]\s*(.+)', when_text)
        for bullet in bullets[:3]:
            # Get key nouns
            words = re.findall(r'\b[a-z]{4,}\b', bullet.lower())
            triggers.extend(words[:2])
    
    return list(set(triggers))[:5]


def create_skill_file(skill: ExtractedSkill, output_dir: Path) -> Path:
    """Create SKILL.md file for extracted skill."""
    
    # Sanitize name for directory
    dir_name = re.sub(r'[^\w\s-]', '', skill.name.lower())
    dir_name = re.sub(r'[\s]+', '-', dir_name)
    
    skill_dir = output_dir / skill.category / dir_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    skill_path = skill_dir / "SKILL.md"
    
    # Format content
    content = skill.content
    
    # Ensure proper structure
    if not content.startswith('#'):
        content = f"# {skill.name}\n\n{content}"
    
    # Add description blockquote if not present
    if '\n>' not in content[:200]:
        lines = content.split('\n')
        header = lines[0]
        rest = '\n'.join(lines[1:])
        content = f"{header}\n\n> {skill.description}\n{rest}"
    
    # Add metadata footer
    content += f"\n\n---\n*Migrated from {skill.source} on {datetime.now().strftime('%Y-%m-%d')}*\n"
    
    skill_path.write_text(content)
    
    return skill_path


def interactive_mode(output_dir: Path):
    """Interactive skill creation mode."""
    print("\n🔧 Interactive Skill Creator")
    print("=" * 40)
    
    while True:
        print("\nOptions:")
        print("1. Create new skill")
        print("2. Import from clipboard")
        print("3. Exit")
        
        choice = input("\nChoice: ").strip()
        
        if choice == "1":
            name = input("Skill name: ").strip()
            category = input(f"Category (documents/patterns/integrations/agents/data/prompts): ").strip()
            description = input("One-line description: ").strip()
            
            print("\nEnter skill content (end with '---' on new line):")
            lines = []
            while True:
                line = input()
                if line.strip() == "---":
                    break
                lines.append(line)
            
            content = "\n".join(lines)
            
            skill = ExtractedSkill(
                name=name,
                category=category,
                description=description,
                content=f"# {name}\n\n> {description}\n\n{content}",
                source="interactive",
            )
            
            path = create_skill_file(skill, output_dir)
            print(f"\n✅ Created: {path}")
        
        elif choice == "2":
            try:
                import pyperclip
                content = pyperclip.paste()
                
                name = input("Skill name: ").strip()
                category = input("Category: ").strip()
                
                skill = ExtractedSkill(
                    name=name,
                    category=category,
                    description=content[:100],
                    content=content,
                    source="clipboard",
                )
                
                path = create_skill_file(skill, output_dir)
                print(f"\n✅ Created: {path}")
            except ImportError:
                print("Install pyperclip for clipboard support: pip install pyperclip")
        
        elif choice == "3":
            break


def main():
    parser = argparse.ArgumentParser(description="Migrate skills from various sources")
    parser.add_argument("--source", choices=["windsurf", "claude", "docs", "interactive"])
    parser.add_argument("--input", help="Input file or directory")
    parser.add_argument("--output", default="./", help="Output skills directory")
    
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if args.source == "interactive" or not args.source:
        interactive_mode(output_dir)
        return
    
    if not args.input:
        print("Error: --input required for non-interactive mode")
        return
    
    input_path = Path(args.input)
    
    if args.source == "windsurf":
        if input_path.is_file():
            content = input_path.read_text()
        else:
            # Try common locations
            for loc in [".windsurfrules", "~/.windsurfrules"]:
                p = Path(loc).expanduser()
                if p.exists():
                    content = p.read_text()
                    break
            else:
                print("Could not find .windsurfrules")
                return
        
        skills = parse_windsurfrules(content)
    
    elif args.source == "claude":
        content = input_path.read_text()
        skills = parse_claude_instructions(content)
    
    elif args.source == "docs":
        skills = parse_markdown_docs(input_path)
    
    print(f"\n📦 Extracted {len(skills)} skills")
    
    # Show preview
    for skill in skills:
        print(f"  - [{skill.category}] {skill.name}")
    
    confirm = input("\nCreate skill files? (y/n): ")
    if confirm.lower() == 'y':
        for skill in skills:
            path = create_skill_file(skill, output_dir)
            print(f"  ✅ {path}")
        
        print(f"\n🎉 Created {len(skills)} skills in {output_dir}")
        print("Run './scripts/generate-configs.py' to update manifest")


if __name__ == "__main__":
    main()
