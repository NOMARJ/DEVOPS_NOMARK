"""
Skills Tools for DevOps MCP
===========================
Tools for discovering and using skills (instructions, patterns, agents).
"""

import os
import json
from pathlib import Path
from typing import Any, Optional, List


class SkillsTools:
    """Skills discovery and management tools."""
    
    def __init__(self):
        # Look for skills in multiple locations
        self.skills_paths = [
            os.environ.get("SKILLS_DIR", ""),
            os.path.expanduser("~/skills"),
            os.path.expanduser("~/devops-agent/skills"),
            "./skills",
        ]
        self._manifest_cache = None
    
    def _find_skills_dir(self) -> Optional[Path]:
        """Find the first valid skills directory."""
        for path in self.skills_paths:
            if path and Path(path).exists():
                return Path(path)
        return None
    
    def _load_manifest(self) -> dict:
        """Load or generate skills manifest."""
        if self._manifest_cache:
            return self._manifest_cache
        
        skills_dir = self._find_skills_dir()
        if not skills_dir:
            return {"skills": [], "categories": []}
        
        # Check for existing manifest
        manifest_path = skills_dir / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                self._manifest_cache = json.load(f)
                return self._manifest_cache
        
        # Generate manifest from directory structure
        skills = []
        categories = set()
        
        for category_dir in skills_dir.iterdir():
            if category_dir.is_dir() and not category_dir.name.startswith("."):
                categories.add(category_dir.name)
                
                for skill_dir in category_dir.iterdir():
                    if skill_dir.is_dir():
                        skill_md = skill_dir / "SKILL.md"
                        if skill_md.exists():
                            # Parse description from first paragraph
                            content = skill_md.read_text()
                            lines = content.split("\n")
                            description = ""
                            for line in lines[1:]:  # Skip title
                                if line.strip() and not line.startswith("#"):
                                    description = line.strip()
                                    break
                            
                            skills.append({
                                "id": f"{category_dir.name}/{skill_dir.name}",
                                "name": skill_dir.name.replace("-", " ").title(),
                                "category": category_dir.name,
                                "path": str(skill_dir.relative_to(skills_dir)),
                                "description": description[:200],
                            })
        
        self._manifest_cache = {
            "skills": skills,
            "categories": sorted(categories),
        }
        return self._manifest_cache
    
    def get_manifest(self) -> dict:
        """Get the skills manifest."""
        return self._load_manifest()
    
    def get_skill_content(self, skill_id: str) -> str:
        """Get the content of a skill's SKILL.md file."""
        skills_dir = self._find_skills_dir()
        if not skills_dir:
            return f"Skills directory not found"
        
        skill_path = skills_dir / skill_id / "SKILL.md"
        if not skill_path.exists():
            # Try without category prefix
            for category in skills_dir.iterdir():
                if category.is_dir():
                    alt_path = category / skill_id / "SKILL.md"
                    if alt_path.exists():
                        skill_path = alt_path
                        break
        
        if skill_path.exists():
            return skill_path.read_text()
        
        return f"Skill not found: {skill_id}"
    
    def get_tools(self) -> dict[str, dict]:
        return {
            "skills_list": {
                "description": "List all available skills with their descriptions",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Filter by category"},
                        "search": {"type": "string", "description": "Search in name/description"},
                    },
                },
                "handler": self.list_skills,
            },
            "skills_get": {
                "description": "Get the full content of a skill (SKILL.md)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "skill_id": {"type": "string", "description": "Skill ID (e.g., 'documents/docx' or 'docx')"},
                    },
                    "required": ["skill_id"],
                },
                "handler": self.get_skill,
            },
            "skills_categories": {
                "description": "List skill categories",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
                "handler": self.list_categories,
            },
            "skills_search": {
                "description": "Search for skills by keyword",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                    },
                    "required": ["query"],
                },
                "handler": self.search_skills,
            },
            "skills_recommend": {
                "description": "Get skill recommendations for a task",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "Task description"},
                    },
                    "required": ["task"],
                },
                "handler": self.recommend_skills,
            },
        }
    
    async def list_skills(self, category: Optional[str] = None, search: Optional[str] = None) -> dict:
        """List available skills."""
        manifest = self._load_manifest()
        skills = manifest.get("skills", [])
        
        if category:
            skills = [s for s in skills if s["category"] == category]
        
        if search:
            search_lower = search.lower()
            skills = [
                s for s in skills
                if search_lower in s["name"].lower() or search_lower in s.get("description", "").lower()
            ]
        
        return {
            "skills": skills,
            "count": len(skills),
            "categories": manifest.get("categories", []),
        }
    
    async def get_skill(self, skill_id: str) -> dict:
        """Get a specific skill's content."""
        content = self.get_skill_content(skill_id)
        
        return {
            "skill_id": skill_id,
            "content": content,
        }
    
    async def list_categories(self) -> dict:
        """List skill categories."""
        manifest = self._load_manifest()
        
        # Count skills per category
        category_counts = {}
        for skill in manifest.get("skills", []):
            cat = skill["category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        return {
            "categories": [
                {"name": cat, "count": count}
                for cat, count in sorted(category_counts.items())
            ]
        }
    
    async def search_skills(self, query: str) -> dict:
        """Search skills by keyword."""
        return await self.list_skills(search=query)
    
    async def recommend_skills(self, task: str) -> dict:
        """Recommend skills based on task description."""
        manifest = self._load_manifest()
        skills = manifest.get("skills", [])
        
        task_lower = task.lower()
        
        # Simple keyword matching for recommendations
        keywords = {
            "documents": ["word", "docx", "document", "report", "letter"],
            "data": ["excel", "xlsx", "spreadsheet", "csv", "data"],
            "presentations": ["powerpoint", "pptx", "presentation", "slides"],
            "pdf": ["pdf", "form", "fill"],
            "sveltekit": ["svelte", "frontend", "component", "page", "ui"],
            "postgres": ["database", "sql", "table", "migration", "query"],
            "n8n": ["workflow", "automation", "webhook", "integration"],
            "agents": ["autonomous", "agent", "ralph", "automation"],
        }
        
        recommended = []
        for skill in skills:
            skill_cat = skill["category"]
            skill_name = skill["name"].lower()
            skill_desc = skill.get("description", "").lower()
            
            # Check if task matches any keywords for this skill's category
            for cat, kws in keywords.items():
                if cat in skill_cat or cat in skill_name:
                    for kw in kws:
                        if kw in task_lower:
                            recommended.append({
                                **skill,
                                "match_reason": f"Task mentions '{kw}'",
                            })
                            break
            
            # Also check if task words appear in skill description
            for word in task_lower.split():
                if len(word) > 3 and word in skill_desc:
                    if skill not in [r for r in recommended if r["id"] == skill["id"]]:
                        recommended.append({
                            **skill,
                            "match_reason": f"Description contains '{word}'",
                        })
        
        return {
            "task": task,
            "recommendations": recommended[:5],  # Top 5
            "count": len(recommended),
        }
