"""
GitHub Tools for DevOps MCP
===========================
Tools for managing GitHub repositories, PRs, issues, and actions.
"""

import os
from typing import Any, Optional, List


class GitHubTools:
    """GitHub management tools."""
    
    def __init__(self):
        self.token = os.environ.get("GITHUB_TOKEN")
        self._client = None
    
    def is_configured(self) -> bool:
        """Check if GitHub is properly configured."""
        return bool(self.token)
    
    def _get_client(self):
        """Get GitHub client (lazy loaded)."""
        if self._client is None:
            from github import Github
            self._client = Github(self.token)
        return self._client
    
    def get_tools(self) -> dict[str, dict]:
        """Return all GitHub tools."""
        return {
            "github_repo_list": {
                "description": "List repositories for a user or organization",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "User or org name (default: authenticated user)"},
                        "type": {"type": "string", "enum": ["all", "owner", "member"], "default": "all"},
                    },
                },
                "handler": self.list_repos,
            },
            "github_repo_info": {
                "description": "Get information about a repository",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                    },
                    "required": ["owner", "repo"],
                },
                "handler": self.get_repo_info,
            },
            "github_pr_list": {
                "description": "List pull requests for a repository",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"},
                        "limit": {"type": "integer", "description": "Max PRs to return", "default": 20},
                    },
                    "required": ["owner", "repo"],
                },
                "handler": self.list_prs,
            },
            "github_pr_create": {
                "description": "Create a pull request",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "title": {"type": "string", "description": "PR title"},
                        "body": {"type": "string", "description": "PR description"},
                        "head": {"type": "string", "description": "Source branch"},
                        "base": {"type": "string", "description": "Target branch", "default": "main"},
                        "draft": {"type": "boolean", "description": "Create as draft", "default": False},
                    },
                    "required": ["owner", "repo", "title", "head"],
                },
                "handler": self.create_pr,
            },
            "github_pr_merge": {
                "description": "Merge a pull request",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "pr_number": {"type": "integer", "description": "PR number"},
                        "merge_method": {"type": "string", "enum": ["merge", "squash", "rebase"], "default": "squash"},
                    },
                    "required": ["owner", "repo", "pr_number"],
                },
                "handler": self.merge_pr,
            },
            "github_issue_list": {
                "description": "List issues for a repository",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"},
                        "labels": {"type": "array", "items": {"type": "string"}, "description": "Filter by labels"},
                        "limit": {"type": "integer", "description": "Max issues to return", "default": 20},
                    },
                    "required": ["owner", "repo"],
                },
                "handler": self.list_issues,
            },
            "github_issue_create": {
                "description": "Create an issue",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "title": {"type": "string", "description": "Issue title"},
                        "body": {"type": "string", "description": "Issue body"},
                        "labels": {"type": "array", "items": {"type": "string"}, "description": "Labels to add"},
                        "assignees": {"type": "array", "items": {"type": "string"}, "description": "Assignees"},
                    },
                    "required": ["owner", "repo", "title"],
                },
                "handler": self.create_issue,
            },
            "github_actions_list": {
                "description": "List recent workflow runs",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "workflow": {"type": "string", "description": "Workflow file name (optional)"},
                        "status": {"type": "string", "enum": ["completed", "in_progress", "queued"]},
                        "limit": {"type": "integer", "description": "Max runs to return", "default": 10},
                    },
                    "required": ["owner", "repo"],
                },
                "handler": self.list_workflow_runs,
            },
            "github_actions_trigger": {
                "description": "Trigger a workflow dispatch event",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "workflow": {"type": "string", "description": "Workflow file name"},
                        "ref": {"type": "string", "description": "Branch or tag", "default": "main"},
                        "inputs": {"type": "object", "description": "Workflow inputs"},
                    },
                    "required": ["owner", "repo", "workflow"],
                },
                "handler": self.trigger_workflow,
            },
            "github_branch_list": {
                "description": "List branches for a repository",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                    },
                    "required": ["owner", "repo"],
                },
                "handler": self.list_branches,
            },
            "github_file_content": {
                "description": "Get content of a file from a repository",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "path": {"type": "string", "description": "File path"},
                        "ref": {"type": "string", "description": "Branch, tag, or commit", "default": "main"},
                    },
                    "required": ["owner", "repo", "path"],
                },
                "handler": self.get_file_content,
            },
        }
    
    async def list_repos(self, owner: Optional[str] = None, type: str = "all") -> dict:
        """List repositories."""
        client = self._get_client()
        
        if owner:
            user = client.get_user(owner)
            repos = user.get_repos(type=type)
        else:
            repos = client.get_user().get_repos(type=type)
        
        result = []
        for repo in repos[:50]:  # Limit to 50
            result.append({
                "name": repo.name,
                "full_name": repo.full_name,
                "private": repo.private,
                "default_branch": repo.default_branch,
                "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
            })
        
        return {"repos": result, "count": len(result)}
    
    async def get_repo_info(self, owner: str, repo: str) -> dict:
        """Get repository information."""
        client = self._get_client()
        r = client.get_repo(f"{owner}/{repo}")
        
        return {
            "name": r.name,
            "full_name": r.full_name,
            "description": r.description,
            "private": r.private,
            "default_branch": r.default_branch,
            "language": r.language,
            "stars": r.stargazers_count,
            "forks": r.forks_count,
            "open_issues": r.open_issues_count,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            "clone_url": r.clone_url,
        }
    
    async def list_prs(self, owner: str, repo: str, state: str = "open", limit: int = 20) -> dict:
        """List pull requests."""
        client = self._get_client()
        r = client.get_repo(f"{owner}/{repo}")
        prs = r.get_pulls(state=state)
        
        result = []
        for pr in prs[:limit]:
            result.append({
                "number": pr.number,
                "title": pr.title,
                "state": pr.state,
                "user": pr.user.login,
                "created_at": pr.created_at.isoformat() if pr.created_at else None,
                "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
                "head": pr.head.ref,
                "base": pr.base.ref,
                "draft": pr.draft,
                "mergeable": pr.mergeable,
            })
        
        return {"pull_requests": result, "count": len(result)}
    
    async def create_pr(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: str = "",
        draft: bool = False,
    ) -> dict:
        """Create a pull request."""
        client = self._get_client()
        r = client.get_repo(f"{owner}/{repo}")
        
        pr = r.create_pull(title=title, body=body, head=head, base=base, draft=draft)
        
        return {
            "number": pr.number,
            "title": pr.title,
            "url": pr.html_url,
            "status": "created",
        }
    
    async def merge_pr(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        merge_method: str = "squash",
    ) -> dict:
        """Merge a pull request."""
        client = self._get_client()
        r = client.get_repo(f"{owner}/{repo}")
        pr = r.get_pull(pr_number)
        
        result = pr.merge(merge_method=merge_method)
        
        return {
            "merged": result.merged,
            "message": result.message,
            "sha": result.sha,
        }
    
    async def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        labels: Optional[List[str]] = None,
        limit: int = 20,
    ) -> dict:
        """List issues."""
        client = self._get_client()
        r = client.get_repo(f"{owner}/{repo}")
        
        kwargs = {"state": state}
        if labels:
            kwargs["labels"] = labels
        
        issues = r.get_issues(**kwargs)
        
        result = []
        for issue in issues[:limit]:
            # Skip pull requests (they show up as issues)
            if issue.pull_request:
                continue
            result.append({
                "number": issue.number,
                "title": issue.title,
                "state": issue.state,
                "user": issue.user.login,
                "labels": [l.name for l in issue.labels],
                "created_at": issue.created_at.isoformat() if issue.created_at else None,
            })
        
        return {"issues": result, "count": len(result)}
    
    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str = "",
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> dict:
        """Create an issue."""
        client = self._get_client()
        r = client.get_repo(f"{owner}/{repo}")
        
        kwargs = {"title": title, "body": body}
        if labels:
            kwargs["labels"] = labels
        if assignees:
            kwargs["assignees"] = assignees
        
        issue = r.create_issue(**kwargs)
        
        return {
            "number": issue.number,
            "title": issue.title,
            "url": issue.html_url,
            "status": "created",
        }
    
    async def list_workflow_runs(
        self,
        owner: str,
        repo: str,
        workflow: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10,
    ) -> dict:
        """List workflow runs."""
        client = self._get_client()
        r = client.get_repo(f"{owner}/{repo}")
        
        if workflow:
            wf = r.get_workflow(workflow)
            runs = wf.get_runs(status=status) if status else wf.get_runs()
        else:
            runs = r.get_workflow_runs(status=status) if status else r.get_workflow_runs()
        
        result = []
        for run in runs[:limit]:
            result.append({
                "id": run.id,
                "name": run.name,
                "status": run.status,
                "conclusion": run.conclusion,
                "branch": run.head_branch,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "url": run.html_url,
            })
        
        return {"runs": result, "count": len(result)}
    
    async def trigger_workflow(
        self,
        owner: str,
        repo: str,
        workflow: str,
        ref: str = "main",
        inputs: Optional[dict] = None,
    ) -> dict:
        """Trigger a workflow dispatch."""
        client = self._get_client()
        r = client.get_repo(f"{owner}/{repo}")
        wf = r.get_workflow(workflow)
        
        result = wf.create_dispatch(ref=ref, inputs=inputs or {})
        
        return {
            "status": "triggered",
            "workflow": workflow,
            "ref": ref,
        }
    
    async def list_branches(self, owner: str, repo: str) -> dict:
        """List branches."""
        client = self._get_client()
        r = client.get_repo(f"{owner}/{repo}")
        
        result = []
        for branch in r.get_branches():
            result.append({
                "name": branch.name,
                "protected": branch.protected,
                "sha": branch.commit.sha[:7],
            })
        
        return {"branches": result, "count": len(result)}
    
    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str = "main",
    ) -> dict:
        """Get file content."""
        client = self._get_client()
        r = client.get_repo(f"{owner}/{repo}")
        
        content = r.get_contents(path, ref=ref)
        
        return {
            "path": content.path,
            "name": content.name,
            "size": content.size,
            "content": content.decoded_content.decode("utf-8"),
            "sha": content.sha,
        }
