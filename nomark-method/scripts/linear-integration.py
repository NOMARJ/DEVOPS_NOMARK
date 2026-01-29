#!/usr/bin/env python3
"""
NOMARK DevOps - Linear Integration

Syncs PRDs to Linear using label-based hierarchy, and enables
triggering NOMARK tasks by moving cards in Linear.

Linear Hierarchy (mapped from Jira concepts):
- Initiatives: Multi-repo coordination (when multiple projects work together)
- Projects: 1:1 with repo registration (each registered repo = 1 Linear Project)
- Issues + "Feature" label: Features/Epics (main deliverables)
  - Sub-issues: Stories (individual tasks under a Feature)

Labels:
- Feature (purple): Main feature/epic being built
- Story (blue): Individual user stories/tasks
- Bug (red): Production bugs (future: Sentry integration)
- Test (yellow): Test-related work (future: automated testing)
- Improvement (blue): Enhancements to existing functionality

Workflow:
1. PRD submitted → Creates Feature issue + Story sub-issues in Linear
2. Move story to "In Progress" → NOMARK starts working
3. Progress streams to issue comments
4. Preview URLs posted to comments
5. PR created → Story moved to "In Review"
"""

import os
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Linear API configuration
LINEAR_API_URL = "https://api.linear.app/graphql"
LINEAR_API_KEY = os.environ.get("LINEAR_API_KEY")

# File paths
PROJECTS_FILE = Path.home() / "config" / "projects.json"
LINEAR_MAPPING_FILE = Path.home() / "config" / "linear-mapping.json"


class LinearClient:
    """Client for Linear GraphQL API."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or LINEAR_API_KEY
        if not self.api_key:
            raise ValueError("LINEAR_API_KEY not set")

        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }

    async def _query(self, query: str, variables: Dict = None) -> Dict:
        """Execute a GraphQL query."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                LINEAR_API_URL,
                headers=self.headers,
                json={"query": query, "variables": variables or {}}
            )
            response.raise_for_status()
            result = response.json()

            if "errors" in result:
                logger.error(f"Linear API errors: {result['errors']}")
                raise Exception(f"Linear API error: {result['errors'][0]['message']}")

            return result.get("data", {})

    # =========================================================================
    # Team & Workspace
    # =========================================================================

    async def get_teams(self) -> List[Dict]:
        """Get all teams in the workspace."""
        query = """
        query {
            teams {
                nodes {
                    id
                    name
                    key
                }
            }
        }
        """
        result = await self._query(query)
        return result.get("teams", {}).get("nodes", [])

    async def get_team_by_name(self, name: str) -> Optional[Dict]:
        """Get a team by name."""
        teams = await self.get_teams()
        for team in teams:
            if team["name"].lower() == name.lower():
                return team
        return None

    # =========================================================================
    # Projects
    # =========================================================================

    async def get_projects(self, team_id: str) -> List[Dict]:
        """Get all projects for a team."""
        query = """
        query($teamId: String!) {
            team(id: $teamId) {
                projects {
                    nodes {
                        id
                        name
                        description
                        state
                    }
                }
            }
        }
        """
        result = await self._query(query, {"teamId": team_id})
        return result.get("team", {}).get("projects", {}).get("nodes", [])

    async def create_project(self, team_id: str, name: str, description: str = "") -> Dict:
        """Create a new project."""
        mutation = """
        mutation($teamId: String!, $name: String!, $description: String) {
            projectCreate(input: {
                teamIds: [$teamId]
                name: $name
                description: $description
            }) {
                success
                project {
                    id
                    name
                }
            }
        }
        """
        result = await self._query(mutation, {
            "teamId": team_id,
            "name": name,
            "description": description
        })
        return result.get("projectCreate", {}).get("project", {})

    async def get_or_create_project(self, team_id: str, name: str, description: str = "") -> Dict:
        """Get existing project or create new one."""
        projects = await self.get_projects(team_id)
        for project in projects:
            if project["name"].lower() == name.lower():
                return project

        return await self.create_project(team_id, name, description)

    # =========================================================================
    # Workflow States
    # =========================================================================

    async def get_workflow_states(self, team_id: str) -> List[Dict]:
        """Get workflow states for a team."""
        query = """
        query($teamId: String!) {
            team(id: $teamId) {
                states {
                    nodes {
                        id
                        name
                        type
                        position
                    }
                }
            }
        }
        """
        result = await self._query(query, {"teamId": team_id})
        states = result.get("team", {}).get("states", {}).get("nodes", [])
        return sorted(states, key=lambda x: x.get("position", 0))

    async def get_state_by_name(self, team_id: str, name: str) -> Optional[Dict]:
        """Get a workflow state by name."""
        states = await self.get_workflow_states(team_id)
        for state in states:
            if state["name"].lower() == name.lower():
                return state
        return None

    # =========================================================================
    # Issues
    # =========================================================================

    async def create_issue(
        self,
        team_id: str,
        title: str,
        description: str = "",
        project_id: str = None,
        parent_id: str = None,
        state_id: str = None,
        priority: int = 0,
        labels: List[str] = None
    ) -> Dict:
        """Create a new issue."""
        mutation = """
        mutation($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    identifier
                    title
                    url
                }
            }
        }
        """

        input_data = {
            "teamId": team_id,
            "title": title,
            "description": description,
            "priority": priority
        }

        if project_id:
            input_data["projectId"] = project_id
        if parent_id:
            input_data["parentId"] = parent_id
        if state_id:
            input_data["stateId"] = state_id
        if labels:
            input_data["labelIds"] = labels

        result = await self._query(mutation, {"input": input_data})
        return result.get("issueCreate", {}).get("issue", {})

    async def update_issue(
        self,
        issue_id: str,
        state_id: str = None,
        title: str = None,
        description: str = None
    ) -> Dict:
        """Update an issue."""
        mutation = """
        mutation($id: String!, $input: IssueUpdateInput!) {
            issueUpdate(id: $id, input: $input) {
                success
                issue {
                    id
                    identifier
                    title
                    state {
                        name
                    }
                }
            }
        }
        """

        input_data = {}
        if state_id:
            input_data["stateId"] = state_id
        if title:
            input_data["title"] = title
        if description:
            input_data["description"] = description

        result = await self._query(mutation, {"id": issue_id, "input": input_data})
        return result.get("issueUpdate", {}).get("issue", {})

    async def get_issue(self, issue_id: str) -> Dict:
        """Get an issue by ID."""
        query = """
        query($id: String!) {
            issue(id: $id) {
                id
                identifier
                title
                description
                url
                state {
                    id
                    name
                    type
                }
                project {
                    id
                    name
                }
                parent {
                    id
                    identifier
                }
                children {
                    nodes {
                        id
                        identifier
                        title
                        state {
                            name
                        }
                    }
                }
            }
        }
        """
        result = await self._query(query, {"id": issue_id})
        return result.get("issue", {})

    async def get_issue_by_identifier(self, identifier: str) -> Dict:
        """Get an issue by its identifier (e.g., 'NOMARK-123')."""
        query = """
        query($filter: IssueFilter!) {
            issues(filter: $filter) {
                nodes {
                    id
                    identifier
                    title
                    description
                    url
                    state {
                        id
                        name
                        type
                    }
                    project {
                        id
                        name
                    }
                }
            }
        }
        """
        # Parse identifier to get number
        parts = identifier.split("-")
        if len(parts) == 2:
            result = await self._query(query, {
                "filter": {"number": {"eq": int(parts[1])}}
            })
            issues = result.get("issues", {}).get("nodes", [])
            for issue in issues:
                if issue["identifier"] == identifier:
                    return issue
        return {}

    # =========================================================================
    # Comments
    # =========================================================================

    async def create_comment(self, issue_id: str, body: str) -> Dict:
        """Add a comment to an issue."""
        mutation = """
        mutation($issueId: String!, $body: String!) {
            commentCreate(input: {
                issueId: $issueId
                body: $body
            }) {
                success
                comment {
                    id
                    body
                    createdAt
                }
            }
        }
        """
        result = await self._query(mutation, {"issueId": issue_id, "body": body})
        return result.get("commentCreate", {}).get("comment", {})

    # =========================================================================
    # Labels
    # =========================================================================

    async def get_labels(self, team_id: str) -> List[Dict]:
        """Get all labels for a team."""
        query = """
        query($teamId: String!) {
            team(id: $teamId) {
                labels {
                    nodes {
                        id
                        name
                        color
                    }
                }
            }
        }
        """
        result = await self._query(query, {"teamId": team_id})
        return result.get("team", {}).get("labels", {}).get("nodes", [])

    async def create_label(self, team_id: str, name: str, color: str = "#6B7280") -> Dict:
        """Create a label."""
        mutation = """
        mutation($teamId: String!, $name: String!, $color: String!) {
            issueLabelCreate(input: {
                teamId: $teamId
                name: $name
                color: $color
            }) {
                success
                issueLabel {
                    id
                    name
                }
            }
        }
        """
        result = await self._query(mutation, {
            "teamId": team_id,
            "name": name,
            "color": color
        })
        return result.get("issueLabelCreate", {}).get("issueLabel", {})

    async def get_or_create_label(self, team_id: str, name: str, color: str = "#6B7280") -> Dict:
        """Get existing label or create new one."""
        labels = await self.get_labels(team_id)
        for label in labels:
            if label["name"].lower() == name.lower():
                return label
        return await self.create_label(team_id, name, color)

    async def setup_nomark_labels(self, team_id: str) -> Dict[str, Dict]:
        """
        Ensure all NOMARK labels exist in the team.

        Returns dict mapping label name to label info.
        """
        label_definitions = {
            "Feature": "#A855F7",      # Purple - main features/epics
            "Story": "#3B82F6",        # Blue - individual stories
            "Bug": "#EF4444",          # Red - production bugs
            "Test": "#EAB308",         # Yellow - test-related work
            "Improvement": "#3B82F6",  # Blue - enhancements
            "nomark-devops": "#8B5CF6" # Purple - NOMARK automation marker
        }

        labels = {}
        for name, color in label_definitions.items():
            label = await self.get_or_create_label(team_id, name, color)
            labels[name] = label
            logger.info(f"Label ready: {name} ({label.get('id', 'exists')})")

        return labels


# =============================================================================
# PRD to Linear Sync
# =============================================================================

class PRDLinearSync:
    """
    Syncs PRDs to Linear using label-based hierarchy.

    Hierarchy:
    - Project (1:1 with repo)
      - Feature-labeled Issue (the main deliverable)
        - Story sub-issues (individual tasks)
    """

    def __init__(self, team_name: str = "NOMARK"):
        self.client = LinearClient()
        self.team_name = team_name
        self.team_id = None
        self.labels = {}  # Cached labels
        self.mapping = self._load_mapping()

    def _load_mapping(self) -> Dict:
        """Load Linear ID mappings."""
        if LINEAR_MAPPING_FILE.exists():
            with open(LINEAR_MAPPING_FILE) as f:
                return json.load(f)
        return {"projects": {}, "prds": {}, "stories": {}}

    def _save_mapping(self):
        """Save Linear ID mappings."""
        LINEAR_MAPPING_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LINEAR_MAPPING_FILE, "w") as f:
            json.dump(self.mapping, f, indent=2)

    async def initialize(self):
        """Initialize by getting team ID and setting up labels."""
        team = await self.client.get_team_by_name(self.team_name)
        if not team:
            raise Exception(f"Team '{self.team_name}' not found in Linear")
        self.team_id = team["id"]
        logger.info(f"Initialized with team: {self.team_name} ({self.team_id})")

        # Setup/cache all NOMARK labels
        self.labels = await self.client.setup_nomark_labels(self.team_id)

    async def sync_project(self, project_id: str, project_info: Dict) -> Dict:
        """Ensure a Linear project exists for a NOMARK project."""
        if not self.team_id:
            await self.initialize()

        # Check if already mapped
        if project_id in self.mapping["projects"]:
            return self.mapping["projects"][project_id]

        # Create or get project in Linear
        project = await self.client.get_or_create_project(
            team_id=self.team_id,
            name=project_info.get("name", project_id),
            description=project_info.get("description", f"NOMARK project: {project_id}")
        )

        # Save mapping
        self.mapping["projects"][project_id] = {
            "linear_id": project["id"],
            "name": project["name"]
        }
        self._save_mapping()

        logger.info(f"Synced project '{project_id}' to Linear: {project['name']}")
        return self.mapping["projects"][project_id]

    async def sync_prd(
        self,
        project_id: str,
        prd_data: Dict,
        prd_id: str = None
    ) -> Dict:
        """
        Sync a PRD to Linear as a Feature with Story sub-issues.

        Args:
            project_id: NOMARK project ID
            prd_data: PRD JSON data with title, summary, tasks
            prd_id: Optional unique ID for the PRD (defaults to timestamp)

        Returns:
            Dict with feature and story issue IDs
        """
        if not self.team_id:
            await self.initialize()

        prd_id = prd_id or datetime.now().strftime("%Y%m%d-%H%M%S")

        # Load projects config
        with open(PROJECTS_FILE) as f:
            projects_config = json.load(f)

        project_info = next(
            (p for p in projects_config.get("projects", []) if p["id"] == project_id),
            {"id": project_id, "name": project_id}
        )

        # Ensure project exists in Linear
        project_mapping = await self.sync_project(project_id, project_info)
        linear_project_id = project_mapping["linear_id"]

        # Get workflow states
        states = await self.client.get_workflow_states(self.team_id)
        backlog_state = next((s for s in states if s["type"] == "backlog"), states[0])

        # Get labels (should be cached from initialize)
        if not self.labels:
            self.labels = await self.client.setup_nomark_labels(self.team_id)

        feature_label = self.labels.get("Feature", {})
        story_label = self.labels.get("Story", {})
        nomark_label = self.labels.get("nomark-devops", {})

        # Create Feature issue for the PRD
        prd_title = prd_data.get("title", "Untitled Feature")
        prd_summary = prd_data.get("summary", "")

        feature_description = f"""## {prd_title}

{prd_summary}

---
**NOMARK DevOps Integration**
- Project: `{project_id}`
- PRD ID: `{prd_id}`
- Created: {datetime.now().isoformat()}

_Move stories to "In Progress" to trigger NOMARK automation._
"""

        # Create Feature issue with Feature + nomark-devops labels
        feature_labels = [l["id"] for l in [feature_label, nomark_label] if l.get("id")]

        feature_issue = await self.client.create_issue(
            team_id=self.team_id,
            title=prd_title,
            description=feature_description,
            project_id=linear_project_id,
            state_id=backlog_state["id"],
            priority=2,  # Medium-high priority
            labels=feature_labels
        )

        logger.info(f"Created Feature: {feature_issue['identifier']} - {feature_issue['title']}")

        # Create sub-issues (Stories) for each task
        stories = prd_data.get("tasks", [])
        story_issues = []

        # Story labels: Story + nomark-devops
        story_labels = [l["id"] for l in [story_label, nomark_label] if l.get("id")]

        for i, story in enumerate(stories, 1):
            story_title = story.get("title", f"Story {i}")
            story_description = story.get("description", "")
            acceptance_criteria = story.get("acceptance_criteria", [])

            # Build description with acceptance criteria
            issue_description = f"""{story_description}

## Acceptance Criteria
{chr(10).join(f"- [ ] {ac}" for ac in acceptance_criteria) if acceptance_criteria else "- [ ] Implementation complete"}

---
**Story {i} of {len(stories)}**
Feature: {feature_issue['identifier']}

_Move to "In Progress" to start NOMARK automation._
"""

            issue = await self.client.create_issue(
                team_id=self.team_id,
                title=story_title,
                description=issue_description,
                project_id=linear_project_id,
                parent_id=feature_issue["id"],
                state_id=backlog_state["id"],
                priority=3,  # Medium priority
                labels=story_labels
            )

            story_issues.append({
                "linear_id": issue["id"],
                "identifier": issue["identifier"],
                "title": issue["title"],
                "url": issue["url"],
                "story_index": i - 1
            })

            logger.info(f"  Created Story: {issue['identifier']} - {story_title}")

        # Save mapping (using feature_id instead of epic_id for clarity)
        self.mapping["prds"][prd_id] = {
            "project_id": project_id,
            "linear_feature_id": feature_issue["id"],
            "feature_identifier": feature_issue["identifier"],
            "feature_url": feature_issue["url"],
            # Keep legacy fields for backwards compatibility
            "linear_epic_id": feature_issue["id"],
            "epic_identifier": feature_issue["identifier"],
            "epic_url": feature_issue["url"],
            "title": prd_title,
            "stories": story_issues,
            "created_at": datetime.now().isoformat()
        }
        self._save_mapping()

        return {
            "prd_id": prd_id,
            "feature": {
                "id": feature_issue["id"],
                "identifier": feature_issue["identifier"],
                "url": feature_issue["url"],
                "title": feature_issue["title"]
            },
            # Keep "epic" for backwards compatibility
            "epic": {
                "id": feature_issue["id"],
                "identifier": feature_issue["identifier"],
                "url": feature_issue["url"],
                "title": feature_issue["title"]
            },
            "stories": story_issues
        }

    async def update_story_status(
        self,
        prd_id: str,
        story_index: int,
        status: str
    ) -> Dict:
        """
        Update a story's status in Linear.

        Args:
            prd_id: PRD ID
            story_index: Story index in the PRD
            status: One of 'backlog', 'in_progress', 'in_review', 'done'
        """
        if not self.team_id:
            await self.initialize()

        prd_mapping = self.mapping["prds"].get(prd_id)
        if not prd_mapping:
            raise Exception(f"PRD '{prd_id}' not found in mapping")

        story = next(
            (s for s in prd_mapping["stories"] if s["story_index"] == story_index),
            None
        )
        if not story:
            raise Exception(f"Story {story_index} not found in PRD '{prd_id}'")

        # Get workflow states
        states = await self.client.get_workflow_states(self.team_id)

        # Map status to state type
        status_map = {
            "backlog": "backlog",
            "pending": "backlog",
            "in_progress": "started",
            "in_review": "started",
            "done": "completed",
            "completed": "completed"
        }

        target_type = status_map.get(status.lower(), "backlog")
        target_state = next((s for s in states if s["type"] == target_type), states[0])

        # Update issue
        updated = await self.client.update_issue(
            issue_id=story["linear_id"],
            state_id=target_state["id"]
        )

        logger.info(f"Updated {story['identifier']} to '{target_state['name']}'")
        return updated

    async def post_progress(
        self,
        prd_id: str,
        story_index: int,
        message: str
    ):
        """Post a progress update as a comment on a story."""
        prd_mapping = self.mapping["prds"].get(prd_id)
        if not prd_mapping:
            logger.warning(f"PRD '{prd_id}' not found, skipping comment")
            return

        story = next(
            (s for s in prd_mapping["stories"] if s["story_index"] == story_index),
            None
        )
        if not story:
            logger.warning(f"Story {story_index} not found, skipping comment")
            return

        comment = await self.client.create_comment(
            issue_id=story["linear_id"],
            body=message
        )

        logger.info(f"Posted comment to {story['identifier']}")
        return comment

    async def post_preview_url(
        self,
        prd_id: str,
        preview_url: str
    ):
        """Post preview URL to the Feature issue."""
        prd_mapping = self.mapping["prds"].get(prd_id)
        if not prd_mapping:
            return

        message = f"""## Preview Available

**URL:** {preview_url}

_Click to see the live preview of current changes._
"""

        # Use feature_id if available, fall back to legacy epic_id
        feature_id = prd_mapping.get("linear_feature_id") or prd_mapping.get("linear_epic_id")
        await self.client.create_comment(
            issue_id=feature_id,
            body=message
        )

    async def post_pr_url(
        self,
        prd_id: str,
        story_index: int,
        pr_url: str,
        pr_title: str = None
    ):
        """Post PR URL to a story and update its status."""
        prd_mapping = self.mapping["prds"].get(prd_id)
        if not prd_mapping:
            return

        story = next(
            (s for s in prd_mapping["stories"] if s["story_index"] == story_index),
            None
        )
        if not story:
            return

        message = f"""## Pull Request Created

**PR:** [{pr_title or 'View PR'}]({pr_url})

_Story implementation complete. Ready for review._
"""

        await self.client.create_comment(
            issue_id=story["linear_id"],
            body=message
        )

        # Update status to "in review"
        await self.update_story_status(prd_id, story_index, "in_review")

    # =========================================================================
    # Reverse Sync: Linear → NOMARK
    # =========================================================================

    async def get_project_issues(self, project_id: str) -> List[Dict]:
        """Get all issues (including epics) for a Linear project."""
        query = """
        query($projectId: String!) {
            project(id: $projectId) {
                id
                name
                issues {
                    nodes {
                        id
                        identifier
                        title
                        description
                        url
                        state {
                            id
                            name
                            type
                        }
                        parent {
                            id
                            identifier
                            title
                        }
                        children {
                            nodes {
                                id
                                identifier
                                title
                                description
                                url
                                state {
                                    id
                                    name
                                    type
                                }
                            }
                        }
                        labels {
                            nodes {
                                id
                                name
                            }
                        }
                    }
                }
            }
        }
        """
        result = await self.client._query(query, {"projectId": project_id})
        return result.get("project", {}).get("issues", {}).get("nodes", [])

    async def sync_from_linear(
        self,
        nomark_project_id: str,
        linear_project_name: str = None
    ) -> Dict:
        """
        Import existing Linear epics/issues into NOMARK mapping.

        This enables the "Linear-first" workflow where you create epics
        and issues directly in Linear, then sync them to NOMARK for automation.

        Args:
            nomark_project_id: The NOMARK project ID (from projects.json)
            linear_project_name: Optional Linear project name (defaults to project name)

        Returns:
            Dict with import results
        """
        if not self.team_id:
            await self.initialize()

        # Load projects config
        with open(PROJECTS_FILE) as f:
            projects_config = json.load(f)

        project_info = next(
            (p for p in projects_config.get("projects", []) if p["id"] == nomark_project_id),
            None
        )

        if not project_info:
            raise Exception(f"Project '{nomark_project_id}' not found in projects.json")

        # Find the Linear project
        linear_name = linear_project_name or project_info.get("name", nomark_project_id)
        projects = await self.client.get_projects(self.team_id)

        linear_project = next(
            (p for p in projects if p["name"].lower() == linear_name.lower()),
            None
        )

        if not linear_project:
            raise Exception(f"Linear project '{linear_name}' not found")

        linear_project_id = linear_project["id"]

        # Save project mapping if not exists
        if nomark_project_id not in self.mapping["projects"]:
            self.mapping["projects"][nomark_project_id] = {
                "linear_id": linear_project_id,
                "name": linear_project["name"]
            }

        # Get all issues in the project
        issues = await self.get_project_issues(linear_project_id)

        # Find Features (issues with children, or with Feature label)
        features_imported = []
        stories_imported = []

        for issue in issues:
            children = issue.get("children", {}).get("nodes", [])
            issue_labels = [label["name"].lower() for label in issue.get("labels", {}).get("nodes", [])]

            # An issue is a Feature if it has:
            # - Children (sub-issues), OR
            # - Feature label, OR
            # - Legacy [PRD] or [Epic] prefix (backwards compatibility)
            is_feature = (
                len(children) > 0 or
                "feature" in issue_labels or
                issue["title"].startswith("[PRD]") or
                issue["title"].startswith("[Epic]") or
                any(l in ["epic", "prd"] for l in issue_labels)
            )

            if is_feature and issue.get("parent") is None:
                # This is a top-level Feature
                prd_id = f"linear-{issue['identifier'].lower()}"

                # Skip if already imported
                if prd_id in self.mapping["prds"]:
                    logger.info(f"Skipping {issue['identifier']} - already imported")
                    continue

                # Create PRD mapping from this Feature
                stories = []
                for i, child in enumerate(children):
                    stories.append({
                        "linear_id": child["id"],
                        "identifier": child["identifier"],
                        "title": child["title"],
                        "url": child.get("url", ""),
                        "story_index": i
                    })
                    stories_imported.append(child["identifier"])

                # Clean title of legacy prefixes
                clean_title = issue["title"].replace("[PRD] ", "").replace("[Epic] ", "")

                self.mapping["prds"][prd_id] = {
                    "project_id": nomark_project_id,
                    "linear_feature_id": issue["id"],
                    "feature_identifier": issue["identifier"],
                    "feature_url": issue.get("url", ""),
                    # Keep legacy fields for backwards compatibility
                    "linear_epic_id": issue["id"],
                    "epic_identifier": issue["identifier"],
                    "epic_url": issue.get("url", ""),
                    "title": clean_title,
                    "stories": stories,
                    "created_at": datetime.now().isoformat(),
                    "imported_from_linear": True
                }

                features_imported.append(issue["identifier"])
                logger.info(f"Imported Feature: {issue['identifier']} with {len(children)} stories")

            elif issue.get("parent") is None and not is_feature:
                # Standalone issue (no parent, no children) - treat as single-story PRD
                prd_id = f"linear-{issue['identifier'].lower()}"

                if prd_id in self.mapping["prds"]:
                    continue

                self.mapping["prds"][prd_id] = {
                    "project_id": nomark_project_id,
                    "linear_epic_id": issue["id"],
                    "epic_identifier": issue["identifier"],
                    "epic_url": issue.get("url", ""),
                    "title": issue["title"],
                    "stories": [{
                        "linear_id": issue["id"],
                        "identifier": issue["identifier"],
                        "title": issue["title"],
                        "url": issue.get("url", ""),
                        "story_index": 0
                    }],
                    "created_at": datetime.now().isoformat(),
                    "imported_from_linear": True
                }

                stories_imported.append(issue["identifier"])
                logger.info(f"Imported standalone issue: {issue['identifier']}")

        self._save_mapping()

        # Add appropriate labels to imported issues
        try:
            # Setup labels if not already done
            if not self.labels:
                self.labels = await self.client.setup_nomark_labels(self.team_id)

            feature_label = self.labels.get("Feature", {})
            story_label = self.labels.get("Story", {})
            nomark_label = self.labels.get("nomark-devops", {})

            for prd_id, prd_data in self.mapping["prds"].items():
                if prd_data.get("imported_from_linear"):
                    # Add Feature + nomark-devops labels to feature issue
                    feature_id = prd_data.get("linear_feature_id") or prd_data.get("linear_epic_id")
                    if feature_label.get("id"):
                        await self._add_label_to_issue(feature_id, feature_label["id"])
                    if nomark_label.get("id"):
                        await self._add_label_to_issue(feature_id, nomark_label["id"])

                    # Add Story + nomark-devops labels to stories
                    for story in prd_data["stories"]:
                        if story_label.get("id"):
                            await self._add_label_to_issue(story["linear_id"], story_label["id"])
                        if nomark_label.get("id"):
                            await self._add_label_to_issue(story["linear_id"], nomark_label["id"])
        except Exception as e:
            logger.warning(f"Failed to add labels: {e}")

        return {
            "project": nomark_project_id,
            "linear_project": linear_project["name"],
            "features_imported": features_imported,
            "stories_imported": stories_imported,
            "total_features": len(features_imported),
            "total_stories": len(stories_imported),
            # Legacy fields for backwards compatibility
            "epics_imported": features_imported,
            "total_epics": len(features_imported)
        }

    async def _add_label_to_issue(self, issue_id: str, label_id: str):
        """Add a label to an issue."""
        mutation = """
        mutation($id: String!, $labelIds: [String!]!) {
            issueUpdate(id: $id, input: { labelIds: $labelIds }) {
                success
            }
        }
        """
        try:
            # Get existing labels first
            issue = await self.client.get_issue(issue_id)
            existing_labels = [l.get("id") for l in issue.get("labels", {}).get("nodes", [])]

            if label_id not in existing_labels:
                existing_labels.append(label_id)
                await self.client._query(mutation, {"id": issue_id, "labelIds": existing_labels})
        except Exception as e:
            logger.warning(f"Failed to add label to {issue_id}: {e}")

    async def track_new_issue(self, issue_data: Dict) -> Optional[Dict]:
        """
        Track a newly created Linear issue if it belongs to a NOMARK project.

        Called from webhook when an issue is created.

        Args:
            issue_data: Issue data from Linear webhook

        Returns:
            Tracking info if tracked, None otherwise
        """
        if not self.team_id:
            await self.initialize()

        project = issue_data.get("project")
        if not project:
            return None

        linear_project_id = project.get("id")

        # Find the NOMARK project for this Linear project
        nomark_project_id = None
        for proj_id, proj_data in self.mapping.get("projects", {}).items():
            if proj_data.get("linear_id") == linear_project_id:
                nomark_project_id = proj_id
                break

        if not nomark_project_id:
            return None

        issue_id = issue_data.get("id")
        identifier = issue_data.get("identifier")
        title = issue_data.get("title", "")
        parent = issue_data.get("parent")

        # Check if this is a sub-issue of an existing Feature
        if parent:
            parent_id = parent.get("id")

            # Find the Feature in our mapping
            for prd_id, prd_data in self.mapping.get("prds", {}).items():
                feature_id = prd_data.get("linear_feature_id") or prd_data.get("linear_epic_id")
                if feature_id == parent_id:
                    # Add this as a new story to the existing PRD
                    existing_stories = prd_data.get("stories", [])
                    next_index = max([s["story_index"] for s in existing_stories], default=-1) + 1

                    new_story = {
                        "linear_id": issue_id,
                        "identifier": identifier,
                        "title": title,
                        "url": issue_data.get("url", ""),
                        "story_index": next_index
                    }

                    prd_data["stories"].append(new_story)
                    self._save_mapping()

                    logger.info(f"Added new story {identifier} to PRD {prd_id}")

                    return {
                        "tracked": True,
                        "type": "story",
                        "prd_id": prd_id,
                        "story_index": next_index,
                        "identifier": identifier
                    }

        # This is a new top-level issue - create a new PRD entry as a Feature
        prd_id = f"linear-{identifier.lower()}"

        # Clean title of legacy prefixes
        clean_title = title.replace("[PRD] ", "").replace("[Epic] ", "")

        if prd_id not in self.mapping["prds"]:
            self.mapping["prds"][prd_id] = {
                "project_id": nomark_project_id,
                "linear_feature_id": issue_id,
                "feature_identifier": identifier,
                "feature_url": issue_data.get("url", ""),
                # Keep legacy fields for backwards compatibility
                "linear_epic_id": issue_id,
                "epic_identifier": identifier,
                "epic_url": issue_data.get("url", ""),
                "title": clean_title,
                "stories": [{
                    "linear_id": issue_id,
                    "identifier": identifier,
                    "title": title,
                    "url": issue_data.get("url", ""),
                    "story_index": 0
                }],
                "created_at": datetime.now().isoformat(),
                "imported_from_linear": True
            }
            self._save_mapping()

            logger.info(f"Created new Feature {prd_id} from Linear issue {identifier}")

            return {
                "tracked": True,
                "type": "feature",
                "prd_id": prd_id,
                "identifier": identifier
            }

        return None


# =============================================================================
# Webhook Handler for Linear Events
# =============================================================================

async def handle_linear_webhook(payload: Dict) -> Dict:
    """
    Handle Linear webhook events.

    When an issue moves to "In Progress", trigger NOMARK automation.
    """
    action = payload.get("action")
    event_type = payload.get("type")
    data = payload.get("data", {})

    logger.info(f"Linear webhook: {event_type} - {action}")

    if event_type != "Issue" or action != "update":
        return {"status": "ignored", "reason": "Not an issue update"}

    # Check if state changed to "started" (In Progress)
    updated_from = payload.get("updatedFrom", {})
    if "stateId" not in updated_from:
        return {"status": "ignored", "reason": "No state change"}

    # Get issue details
    issue_id = data.get("id")
    state = data.get("state", {})

    if state.get("type") != "started":
        return {"status": "ignored", "reason": "Not moving to In Progress"}

    # Check if this is a NOMARK-tracked issue
    sync = PRDLinearSync()
    await sync.initialize()

    # Find the PRD and story for this issue
    for prd_id, prd_data in sync.mapping.get("prds", {}).items():
        for story in prd_data.get("stories", []):
            if story["linear_id"] == issue_id:
                logger.info(f"Found NOMARK story: {story['identifier']} in PRD {prd_id}")

                return {
                    "status": "trigger",
                    "prd_id": prd_id,
                    "project_id": prd_data["project_id"],
                    "story_index": story["story_index"],
                    "story_title": story["title"],
                    "identifier": story["identifier"]
                }

    return {"status": "ignored", "reason": "Issue not tracked by NOMARK"}


# =============================================================================
# CLI Interface
# =============================================================================

async def main():
    """CLI interface for testing."""
    import sys

    if len(sys.argv) < 2:
        print("""
NOMARK Linear Integration

Usage:
  linear-integration.py sync-project <project-id>
  linear-integration.py sync-prd <project-id> <prd-json-path>
  linear-integration.py update-status <prd-id> <story-index> <status>
  linear-integration.py post-comment <prd-id> <story-index> <message>
  linear-integration.py list-projects
  linear-integration.py list-prds

  # Reverse sync (Linear → NOMARK):
  linear-integration.py import <nomark-project-id> [linear-project-name]
  linear-integration.py import-all
        """)
        return

    command = sys.argv[1]
    sync = PRDLinearSync()

    if command == "sync-project":
        project_id = sys.argv[2]
        with open(PROJECTS_FILE) as f:
            projects = json.load(f)
        project_info = next(
            (p for p in projects.get("projects", []) if p["id"] == project_id),
            {"id": project_id, "name": project_id}
        )
        result = await sync.sync_project(project_id, project_info)
        print(json.dumps(result, indent=2))

    elif command == "sync-prd":
        project_id = sys.argv[2]
        prd_path = sys.argv[3]
        with open(prd_path) as f:
            prd_data = json.load(f)
        result = await sync.sync_prd(project_id, prd_data)
        print(json.dumps(result, indent=2))

    elif command == "update-status":
        prd_id = sys.argv[2]
        story_index = int(sys.argv[3])
        status = sys.argv[4]
        result = await sync.update_story_status(prd_id, story_index, status)
        print(json.dumps(result, indent=2))

    elif command == "post-comment":
        prd_id = sys.argv[2]
        story_index = int(sys.argv[3])
        message = sys.argv[4]
        result = await sync.post_progress(prd_id, story_index, message)
        print(json.dumps(result, indent=2))

    elif command == "list-projects":
        await sync.initialize()
        projects = await sync.client.get_projects(sync.team_id)
        print(json.dumps(projects, indent=2))

    elif command == "list-prds":
        print(json.dumps(sync.mapping.get("prds", {}), indent=2))

    elif command == "import":
        # Import Linear issues into NOMARK mapping
        nomark_project_id = sys.argv[2]
        linear_project_name = sys.argv[3] if len(sys.argv) > 3 else None
        result = await sync.sync_from_linear(nomark_project_id, linear_project_name)
        print(json.dumps(result, indent=2))

    elif command == "import-all":
        # Import all registered projects from Linear
        with open(PROJECTS_FILE) as f:
            projects_config = json.load(f)

        results = []
        for project in projects_config.get("projects", []):
            project_id = project["id"]
            try:
                result = await sync.sync_from_linear(project_id)
                results.append({"project": project_id, "status": "success", **result})
                print(f"✓ Imported {project_id}: {result['total_features']} features, {result['total_stories']} stories")
            except Exception as e:
                results.append({"project": project_id, "status": "error", "error": str(e)})
                print(f"✗ Failed {project_id}: {e}")

        print(json.dumps(results, indent=2))

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main())
