#!/usr/bin/env python3
"""
NOMARK DevOps Slack Bot

Listens for task commands in Slack and dispatches them to the task runner.
Provides Claude Code-style rich summaries with PR links and next actions.

Features:
  - Task execution with rich formatting
  - File/image attachments with Claude Vision analysis
  - Live preview via Cloudflare Tunnel
  - Interactive buttons (Approve PR, Run Tests, Cancel)
  - Show file command
  - Live progress updates

Commands:
  @nomark task <project> <description>  - Run a task on a project
  @nomark status                        - Check VM and task status
  @nomark projects                      - List available projects
  @nomark logs [n]                      - Show last n log entries
  @nomark preview [project]             - Start dev server with public URL
  @nomark preview stop                  - Stop dev server
  @nomark show <project> <filepath>     - View a file from the project
  @nomark stop                          - Stop running task

Slash Commands:
  /nomark-task <project> <description>  - Quick task execution
  /nomark-status                        - Quick status check
"""

import os
import re
import json
import subprocess
import asyncio
import logging
import tempfile
import base64
import httpx
from datetime import datetime
from pathlib import Path
from typing import Optional

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
PROJECTS_FILE = Path.home() / "config" / "projects.json"
LOGS_FILE = Path.home() / "logs" / "tasks.log"
TASK_SCRIPT = Path.home() / "scripts" / "nomark-task.sh"
PRD_SCRIPT = Path.home() / "scripts" / "nomark-prd.sh"
PREVIEW_SCRIPT = Path.home() / "scripts" / "preview-server.sh"
REGISTER_SCRIPT = Path.home() / "scripts" / "register-project.sh"
LINEAR_API_KEY = os.environ.get("LINEAR_API_KEY")
LINEAR_MAPPING_FILE = Path.home() / "config" / "linear-mapping.json"

logger.info(f"Bot token present: {bool(SLACK_BOT_TOKEN)}")
logger.info(f"Linear API key present: {bool(LINEAR_API_KEY)}")
logger.info(f"App token present: {bool(SLACK_APP_TOKEN)}")

# Initialize Slack app
app = AsyncApp(token=SLACK_BOT_TOKEN)

# Track active tasks per thread for follow-ups (persisted to file)
ACTIVE_TASKS_FILE = Path.home() / "config" / "active_tasks.json"

# Track running processes per thread (in-memory, not persisted)
running_processes = {}

# Track preview server state
preview_state = {
    "running": False,
    "project": None,
    "url": None,
    "process": None
}

# Track progress message IDs for live updates
progress_messages = {}


def load_active_tasks():
    """Load active tasks from persistent storage."""
    if ACTIVE_TASKS_FILE.exists():
        try:
            with open(ACTIVE_TASKS_FILE) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load active tasks: {e}")
    return {}


def save_active_tasks(tasks):
    """Save active tasks to persistent storage."""
    try:
        ACTIVE_TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ACTIVE_TASKS_FILE, 'w') as f:
            json.dump(tasks, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save active tasks: {e}")


# Load on startup
active_tasks = load_active_tasks()
logger.info(f"Loaded {len(active_tasks)} active task threads")


def load_projects():
    """Load projects configuration."""
    if PROJECTS_FILE.exists():
        with open(PROJECTS_FILE) as f:
            return json.load(f)
    return {"projects": []}


def get_active_projects():
    """Get list of active projects."""
    config = load_projects()
    return [p for p in config.get("projects", []) if p.get("active", True)]


def get_project_path(project_id: str) -> Optional[Path]:
    """Get the path to a project."""
    return Path.home() / "repos" / project_id


def format_project_list():
    """Format projects as a Slack message."""
    projects = get_active_projects()
    if not projects:
        return "No active projects configured."

    lines = ["*Available Projects:*\n"]
    for p in projects:
        stack = p.get("stack", "unknown")
        priority = p.get("priority", "-")
        lines.append(f"• `{p['id']}` - {p['name']} ({stack}) [P{priority}]")

    return "\n".join(lines)


def get_recent_logs(n=10):
    """Get recent log entries."""
    if not LOGS_FILE.exists():
        return "No logs found."

    try:
        result = subprocess.run(
            ["tail", f"-{n}", str(LOGS_FILE)],
            capture_output=True,
            text=True
        )
        if result.stdout:
            return f"```\n{result.stdout}\n```"
        return "No recent log entries."
    except Exception as e:
        return f"Error reading logs: {e}"


# =============================================================================
# FEATURE 1: File/Image Attachment Support with Claude Vision
# =============================================================================

async def download_slack_file(url: str) -> bytes:
    """Download a file from Slack."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
        )
        return response.content


async def analyze_image_with_claude(image_data: bytes, prompt: str, media_type: str = "image/png") -> str:
    """Analyze an image using Claude Vision API."""
    if not ANTHROPIC_API_KEY:
        return "Error: ANTHROPIC_API_KEY not configured for image analysis."

    base64_image = base64.b64encode(image_data).decode('utf-8')

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            },
            timeout=60.0
        )

        if response.status_code == 200:
            result = response.json()
            return result["content"][0]["text"]
        else:
            return f"Error analyzing image: {response.status_code}"


async def process_file_attachment(file_info: dict, context: str = "") -> str:
    """Process a file attachment and return analysis or content."""
    file_type = file_info.get("filetype", "")
    file_name = file_info.get("name", "unknown")
    file_url = file_info.get("url_private", "")

    if not file_url:
        return f"Could not access file: {file_name}"

    try:
        file_data = await download_slack_file(file_url)

        # Image files - analyze with Claude Vision
        if file_type in ["png", "jpg", "jpeg", "gif", "webp"]:
            media_type = f"image/{file_type}" if file_type != "jpg" else "image/jpeg"
            prompt = context if context else "Describe what you see in this image. If it's a screenshot of a bug or error, explain what the issue appears to be and suggest how to fix it."
            analysis = await analyze_image_with_claude(file_data, prompt, media_type)
            return f"*Image Analysis for `{file_name}`:*\n\n{analysis}"

        # Text/code files - return content
        elif file_type in ["txt", "log", "json", "js", "ts", "tsx", "py", "md", "yaml", "yml", "sh", "css", "html"]:
            content = file_data.decode('utf-8', errors='replace')
            # Truncate if too long
            if len(content) > 2000:
                content = content[:2000] + "\n... (truncated)"
            return f"*Content of `{file_name}`:*\n```{file_type}\n{content}\n```"

        else:
            return f"Received file `{file_name}` ({file_type}). File type not supported for inline analysis."

    except Exception as e:
        logger.exception(f"Error processing file: {e}")
        return f"Error processing file `{file_name}`: {str(e)}"


# =============================================================================
# FEATURE 7: PRD/Claude.ai Integration
# =============================================================================

async def parse_prd_with_claude(content: str) -> dict:
    """Use Claude to parse PRD content and extract actionable tasks."""
    if not ANTHROPIC_API_KEY:
        return {"error": "ANTHROPIC_API_KEY not configured"}

    prompt = """Analyze this PRD/specification and extract:
1. The project it's for (or suggest one if not specified)
2. A list of discrete, implementable tasks in order of dependency
3. Any technical requirements or constraints

Return as JSON:
{
  "project": "project-name or null",
  "title": "Feature title",
  "summary": "One sentence summary",
  "tasks": [
    {"id": 1, "description": "Task description", "type": "feature|bugfix|refactor", "priority": "high|medium|low"},
    ...
  ],
  "constraints": ["constraint 1", ...],
  "estimated_complexity": "small|medium|large"
}

PRD Content:
"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 2048,
                "messages": [{
                    "role": "user",
                    "content": prompt + content
                }]
            },
            timeout=60.0
        )

        if response.status_code == 200:
            result = response.json()
            text = result["content"][0]["text"]
            # Extract JSON from response
            try:
                # Find JSON in response
                json_match = re.search(r'\{[\s\S]*\}', text)
                if json_match:
                    return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
            return {"error": "Could not parse PRD", "raw": text}
        else:
            return {"error": f"API error: {response.status_code}"}


async def execute_prd(prd_data: dict, project: str, channel: str, thread_ts: str):
    """Execute PRD using Ralph autonomous mode - creates prd.json and runs autonomous loop."""
    tasks = prd_data.get("tasks", [])
    title = prd_data.get("title", "PRD Execution")

    if not tasks:
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text="❌ No tasks found in PRD."
        )
        return

    # Convert tasks to Ralph story format with status tracking
    stories = []
    for t in tasks:
        stories.append({
            "id": t.get("id", len(stories) + 1),
            "description": t["description"],
            "type": t.get("type", "feature"),
            "priority": t.get("priority", "medium"),
            "status": "pending",
            "acceptance_criteria": t.get("acceptance_criteria", [])
        })

    # Create Ralph-compatible prd.json
    ralph_prd = {
        "title": title,
        "summary": prd_data.get("summary", ""),
        "project": project,
        "complexity": prd_data.get("estimated_complexity", "medium"),
        "constraints": prd_data.get("constraints", []),
        "tasks": stories,
        "created_at": datetime.now().isoformat(),
        "mode": "ralph_autonomous"
    }

    # Post PRD summary
    summary_lines = [
        f"🤖 *RALPH MODE: {title}*",
        "",
        f"*Summary:* {prd_data.get('summary', 'N/A')}",
        f"*Complexity:* {prd_data.get('estimated_complexity', 'unknown')}",
        f"*Stories:* {len(stories)}",
        "",
        "*Story Queue:*"
    ]
    for s in stories:
        summary_lines.append(f"  {s['id']}. {s['description']} [{s.get('priority', 'medium')}]")

    if prd_data.get("constraints"):
        summary_lines.append("")
        summary_lines.append("*Constraints:*")
        for c in prd_data["constraints"]:
            summary_lines.append(f"  • {c}")

    summary_lines.extend([
        "",
        "_Creating prd.json and starting Ralph autonomous loop..._",
        "_Claude will implement ALL stories sequentially, committing after each._"
    ])

    await app.client.chat_postMessage(
        channel=channel,
        thread_ts=thread_ts,
        text="\n".join(summary_lines)
    )

    # Save prd.json to temp file
    prd_file = Path(tempfile.gettempdir()) / f"prd-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    with open(prd_file, 'w') as f:
        json.dump(ralph_prd, f, indent=2)

    try:
        # Run the Ralph PRD script
        process = await asyncio.create_subprocess_exec(
            str(PRD_SCRIPT), project, str(prd_file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        running_processes[thread_ts] = process

        stdout, stderr = await process.communicate()

        if thread_ts in running_processes:
            del running_processes[thread_ts]

        stdout_text = stdout.decode() if stdout else ""
        stderr_text = stderr.decode() if stderr else ""

        if process.returncode == 0:
            # Parse result file
            result_file = None
            for line in stdout_text.split('\n'):
                if line.startswith('RESULT_FILE:'):
                    result_file = line.split(':', 1)[1].strip()
                    break

            result = {}
            if result_file:
                result_path = Path(result_file)
                if result_path.exists():
                    try:
                        result = json.loads(result_path.read_text())
                    except Exception as e:
                        logger.error(f"Failed to read PRD result file: {e}")

            # Format completion message
            stories_done = result.get("stories_done", 0)
            stories_total = result.get("stories_total", len(stories))
            pr_url = result.get("pr_url", "")
            commits = result.get("commits", 0)
            completion = result.get("completion_status", "unknown")

            if completion == "complete":
                emoji = "✅"
                status_text = "All stories complete!"
            elif completion == "partial":
                emoji = "⚠️"
                status_text = f"{stories_done}/{stories_total} stories complete"
            else:
                emoji = "❌"
                status_text = "No stories completed"

            message_lines = [
                f"{emoji} *PRD Execution: {title}*",
                "",
                f"*Status:* {status_text}",
                f"*Commits:* {commits}",
            ]

            if pr_url:
                message_lines.append(f"*PR:* <{pr_url}|View on GitHub>")

            message_lines.extend([
                "",
                f"*Next:* {result.get('next_actions', 'Review the changes')}"
            ])

            await app.client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text="\n".join(message_lines)
            )

            # Track for follow-ups
            if result.get("branch"):
                active_tasks[thread_ts] = {
                    "project": project,
                    "branch": result.get("branch", ""),
                    "last_task_id": result.get("task_id", ""),
                    "pr_url": pr_url,
                    "channel": channel,
                    "prd_title": title,
                    "mode": "ralph",
                    "created_at": datetime.now().isoformat()
                }
                save_active_tasks(active_tasks)

        else:
            error_msg = stderr_text[:500] if stderr_text else stdout_text[:500] or "Unknown error"
            await app.client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=f"❌ *PRD Execution Failed*\n\n```\n{error_msg}\n```"
            )

    except Exception as e:
        logger.exception(f"PRD execution error: {e}")
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"❌ *PRD execution failed unexpectedly*\n\n```\n{str(e)}\n```"
        )
    finally:
        # Clean up temp file
        if prd_file.exists():
            prd_file.unlink()


def format_prd_preview(prd_data: dict) -> tuple:
    """Format PRD data for preview with confirmation buttons."""
    title = prd_data.get("title", "Untitled PRD")
    summary = prd_data.get("summary", "No summary")
    tasks = prd_data.get("tasks", [])
    complexity = prd_data.get("estimated_complexity", "unknown")

    text = f"""📋 *PRD Parsed: {title}*

*Summary:* {summary}
*Complexity:* {complexity}
*Tasks:* {len(tasks)}

*Task Breakdown:*"""

    for t in tasks[:5]:  # Show first 5
        text += f"\n  {t['id']}. {t['description']}"
    if len(tasks) > 5:
        text += f"\n  _...and {len(tasks) - 5} more tasks_"

    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": text}
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "▶️ Execute All Tasks"},
                    "style": "primary",
                    "action_id": "execute_prd",
                    "value": json.dumps(prd_data)
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📝 Execute First Task Only"},
                    "action_id": "execute_prd_first",
                    "value": json.dumps(prd_data)
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "❌ Cancel"},
                    "style": "danger",
                    "action_id": "cancel_prd"
                }
            ]
        }
    ]

    return text, blocks


# PRD button handlers
@app.action("execute_prd")
async def handle_execute_prd(ack, body, say):
    """Execute all tasks from PRD."""
    await ack()

    prd_data = json.loads(body["actions"][0]["value"])
    channel = body["channel"]["id"]
    thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]

    # Get project from PRD or use default
    project = prd_data.get("project") or "flowmetrics"

    await say(
        text=f"🚀 Starting PRD execution on `{project}`...",
        thread_ts=thread_ts
    )

    # Sync to Linear if configured
    if LINEAR_API_KEY:
        await say(
            text="📊 *Syncing to Linear...*",
            thread_ts=thread_ts
        )
        linear_result = await sync_prd_to_linear(project, prd_data, channel, thread_ts)
        if linear_result:
            prd_data["linear_prd_id"] = linear_result.get("prd_id")

    asyncio.create_task(execute_prd(prd_data, project, channel, thread_ts))


@app.action("execute_prd_first")
async def handle_execute_prd_first(ack, body, say):
    """Execute only the first task from PRD."""
    await ack()

    prd_data = json.loads(body["actions"][0]["value"])
    channel = body["channel"]["id"]
    thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]

    tasks = prd_data.get("tasks", [])
    if not tasks:
        await say(text="No tasks in PRD.", thread_ts=thread_ts)
        return

    project = prd_data.get("project") or "flowmetrics"
    first_task = tasks[0]["description"]

    await say(
        text=f"▶️ Executing first task: {first_task}",
        thread_ts=thread_ts
    )

    asyncio.create_task(run_task(project, first_task, channel, thread_ts))


@app.action("cancel_prd")
async def handle_cancel_prd(ack, body, say):
    """Cancel PRD execution."""
    await ack()

    thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]
    await say(text="PRD execution cancelled.", thread_ts=thread_ts)


# =============================================================================
# FEATURE 8: Project Registration
# =============================================================================

async def register_project(github_url: str, project_id: str, channel: str, thread_ts: str):
    """Register a new GitHub project with NOMARK."""

    # Validate GitHub URL
    if not github_url or "github.com" not in github_url:
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text="❌ Invalid GitHub URL. Please provide a valid GitHub repository URL.\n\n*Example:* `https://github.com/owner/repo`"
        )
        return

    await app.client.chat_postMessage(
        channel=channel,
        thread_ts=thread_ts,
        text=f"📦 *Registering project...*\n\n*URL:* `{github_url}`\n\nCloning repository and setting up NOMARK method. This may take a moment..."
    )

    try:
        # Build command
        args = [str(REGISTER_SCRIPT), github_url]
        if project_id:
            args.append(project_id)

        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()
        stdout_text = stdout.decode() if stdout else ""
        stderr_text = stderr.decode() if stderr else ""

        if process.returncode == 0:
            # Parse result JSON - try to extract JSON from output
            result = None
            try:
                result = json.loads(stdout_text.strip())
            except json.JSONDecodeError:
                # Try to find JSON in the output (may have extra text before it)
                import re
                json_match = re.search(r'\{[^{}]*"status"[^{}]*\}', stdout_text, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        pass

                if result is None:
                    # Last resort: try to find any JSON object
                    for line in stdout_text.strip().split('\n'):
                        line = line.strip()
                        if line.startswith('{') and line.endswith('}'):
                            try:
                                result = json.loads(line)
                                break
                            except json.JSONDecodeError:
                                continue

                if result is None:
                    result = {"status": "unknown", "error": f"Could not parse result. Output: {stdout_text[:200]}"}

            if result.get("status") == "success":
                proj_id = result.get("project_id", "unknown")
                repo = result.get("repo", "unknown")
                stack = result.get("stack", "unknown")
                description = result.get("description", "")
                file_count = result.get("file_count", 0)
                total_size = result.get("total_size", "unknown")
                nomark_setup = result.get("nomark_setup", False)

                message_lines = [
                    f"✅ *Project registered successfully!*",
                    "",
                    f"*Project ID:* `{proj_id}`",
                    f"*Repository:* <https://github.com/{repo}|{repo}>",
                    f"*Stack:* {stack}",
                    f"*Files:* {file_count} ({total_size})",
                ]

                if description:
                    message_lines.insert(2, f"*Description:* {description}")

                if nomark_setup:
                    message_lines.append("*NOMARK:* ✅ Method files installed")
                else:
                    message_lines.append("*NOMARK:* ⚠️ Method files not installed (copy manually)")

                message_lines.extend([
                    "",
                    "*Get started:*",
                    f"```@nomark task {proj_id} <your task description>```",
                    "",
                    f"_Use `@nomark show {proj_id} CLAUDE.md` to view project config._"
                ])

                # Auto-create Linear project if Linear is configured
                linear_project_url = None
                if LINEAR_API_KEY:
                    try:
                        import sys
                        sys.path.insert(0, str(Path.home() / "scripts"))
                        from importlib import import_module

                        if "linear_integration" in sys.modules:
                            del sys.modules["linear_integration"]
                        linear_module = import_module("linear_integration")

                        sync = linear_module.PRDLinearSync()
                        linear_result = await sync.sync_project(proj_id, {
                            "id": proj_id,
                            "name": result.get("repo", "").split("/")[-1] or proj_id,
                            "description": description,
                            "repo": repo
                        })
                        linear_project_url = f"https://linear.app/nomark/project/{linear_result.get('linear_id', '')}"
                        message_lines.append(f"*Linear:* ✅ Project created")
                        logger.info(f"Created Linear project for {proj_id}")
                    except Exception as e:
                        logger.warning(f"Failed to create Linear project: {e}")

                # Build action buttons
                action_buttons = [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📋 View on GitHub"},
                        "url": f"https://github.com/{repo}",
                        "action_id": "view_repo"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "👁️ Start Preview"},
                        "action_id": "start_preview",
                        "value": json.dumps({"project": proj_id, "branch": "main"})
                    }
                ]

                # Add Linear button if project was created
                if linear_project_url:
                    action_buttons.append({
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📊 Open in Linear"},
                        "url": linear_project_url,
                        "action_id": "view_linear_project"
                    })

                await app.client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text="\n".join(message_lines),
                    blocks=[
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": "\n".join(message_lines[:12])}
                        },
                        {
                            "type": "actions",
                            "elements": action_buttons
                        },
                        {
                            "type": "context",
                            "elements": [
                                {"type": "mrkdwn", "text": f"_Ready to work! Try `@nomark task {proj_id} <description>`_"}
                            ]
                        }
                    ]
                )
            else:
                error = result.get("error", "Unknown error")
                await app.client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text=f"❌ *Registration failed:* {error}"
                )
        else:
            error_msg = stderr_text[:500] if stderr_text else stdout_text[:500] or "Unknown error"
            await app.client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=f"❌ *Registration failed*\n\n```\n{error_msg}\n```"
            )

    except Exception as e:
        logger.exception(f"Project registration error: {e}")
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"❌ *Registration failed unexpectedly*\n\n```\n{str(e)}\n```"
        )


@app.action("view_repo")
async def handle_view_repo(ack):
    """Handle view repo button click - just acknowledge, URL opens in browser."""
    await ack()


# =============================================================================
# FEATURE 9: Linear Integration
# =============================================================================

def load_linear_mapping() -> dict:
    """Load Linear ID mappings."""
    if LINEAR_MAPPING_FILE.exists():
        with open(LINEAR_MAPPING_FILE) as f:
            return json.load(f)
    return {"projects": {}, "prds": {}, "stories": {}}


def save_linear_mapping(mapping: dict):
    """Save Linear ID mappings."""
    LINEAR_MAPPING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LINEAR_MAPPING_FILE, "w") as f:
        json.dump(mapping, f, indent=2)


async def sync_prd_to_linear(project_id: str, prd_data: dict, channel: str, thread_ts: str) -> dict:
    """Sync a PRD to Linear, creating Epic and Issues."""
    if not LINEAR_API_KEY:
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text="⚠️ *Linear not configured.* Set `LINEAR_API_KEY` to enable Linear sync."
        )
        return None

    try:
        # Import the Linear integration module
        import sys
        sys.path.insert(0, str(Path.home() / "scripts"))
        from importlib import import_module

        # Re-import to get fresh module
        if "linear_integration" in sys.modules:
            del sys.modules["linear_integration"]
        linear_module = import_module("linear_integration")

        sync = linear_module.PRDLinearSync()
        result = await sync.sync_prd(project_id, prd_data)

        # Format success message
        epic = result["epic"]
        stories = result["stories"]

        story_list = "\n".join([
            f"  • <{s['url']}|{s['identifier']}> {s['title']}"
            for s in stories
        ])

        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"""📊 *Synced to Linear*

*Epic:* <{epic['url']}|{epic['identifier']}> {epic['title']}

*Stories:*
{story_list}

_Move stories to "In Progress" in Linear to trigger NOMARK automation._""",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"📊 *Synced to Linear*\n\n*Epic:* <{epic['url']}|{epic['identifier']}>"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Stories ({len(stories)}):*\n{story_list}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "📋 Open in Linear"},
                            "url": epic['url'],
                            "action_id": "open_linear_epic"
                        }
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": "_Move stories to 'In Progress' in Linear to trigger NOMARK._"}
                    ]
                }
            ]
        )

        return result

    except Exception as e:
        logger.exception(f"Linear sync error: {e}")
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"❌ *Linear sync failed:* {str(e)}"
        )
        return None


async def post_linear_comment(prd_id: str, story_index: int, message: str):
    """Post a progress comment to a Linear issue."""
    if not LINEAR_API_KEY:
        return

    try:
        import sys
        sys.path.insert(0, str(Path.home() / "scripts"))
        from importlib import import_module

        if "linear_integration" in sys.modules:
            del sys.modules["linear_integration"]
        linear_module = import_module("linear_integration")

        sync = linear_module.PRDLinearSync()
        await sync.post_progress(prd_id, story_index, message)
    except Exception as e:
        logger.warning(f"Failed to post Linear comment: {e}")


async def update_linear_story_status(prd_id: str, story_index: int, status: str):
    """Update a story's status in Linear."""
    if not LINEAR_API_KEY:
        return

    try:
        import sys
        sys.path.insert(0, str(Path.home() / "scripts"))
        from importlib import import_module

        if "linear_integration" in sys.modules:
            del sys.modules["linear_integration"]
        linear_module = import_module("linear_integration")

        sync = linear_module.PRDLinearSync()
        await sync.update_story_status(prd_id, story_index, status)
    except Exception as e:
        logger.warning(f"Failed to update Linear status: {e}")


async def handle_linear_webhook_trigger(trigger_data: dict, channel: str = None):
    """
    Handle a Linear webhook trigger to start NOMARK automation.

    Called when a story is moved to "In Progress" in Linear.
    """
    project_id = trigger_data["project_id"]
    prd_id = trigger_data["prd_id"]
    story_index = trigger_data["story_index"]
    story_title = trigger_data["story_title"]
    identifier = trigger_data["identifier"]

    logger.info(f"Linear trigger: {identifier} - {story_title}")

    # Post to Linear that we're starting
    await post_linear_comment(
        prd_id, story_index,
        f"🤖 **NOMARK DevOps Starting**\n\nAutomation triggered for this story."
    )

    # Load PRD data to get full story info
    mapping = load_linear_mapping()
    prd_data = mapping.get("prds", {}).get(prd_id)

    if not prd_data:
        logger.error(f"PRD {prd_id} not found in mapping")
        return

    # Find the story in the original PRD
    # We need to load the prd.json from the project
    project_path = Path.home() / "repos" / project_id
    prd_file = project_path / "prd.json"

    if prd_file.exists():
        with open(prd_file) as f:
            full_prd = json.load(f)
        tasks = full_prd.get("tasks", [])
        if story_index < len(tasks):
            task = tasks[story_index]
            task_description = task.get("title", story_title)
        else:
            task_description = story_title
    else:
        task_description = story_title

    # Execute the task using nomark-task.sh
    logger.info(f"Executing task: {task_description} on {project_id}")

    try:
        process = await asyncio.create_subprocess_exec(
            str(TASK_SCRIPT), project_id, task_description,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()
        stdout_text = stdout.decode() if stdout else ""

        # Extract result file path
        result_file = None
        for line in stdout_text.split('\n'):
            if line.startswith("RESULT_FILE:"):
                result_file = line.split(":", 1)[1].strip()
                break

        if result_file and Path(result_file).exists():
            with open(result_file) as f:
                result = json.load(f)

            pr_url = result.get("pr_url", "")
            commits = result.get("commits", 0)
            files_changed = result.get("files_changed", 0)

            # Post result to Linear
            result_message = f"""## Task Complete

**Commits:** {commits}
**Files Changed:** {files_changed}
"""
            if pr_url:
                result_message += f"\n**Pull Request:** [{pr_url}]({pr_url})"

            await post_linear_comment(prd_id, story_index, result_message)

            # Update status to in_review if PR created
            if pr_url:
                await update_linear_story_status(prd_id, story_index, "in_review")

    except Exception as e:
        logger.exception(f"Task execution failed: {e}")
        await post_linear_comment(
            prd_id, story_index,
            f"❌ **Task Failed**\n\n```\n{str(e)}\n```"
        )


@app.action("open_linear_epic")
async def handle_open_linear_epic(ack):
    """Handle open Linear epic button - just acknowledge."""
    await ack()


@app.action("view_linear_project")
async def handle_view_linear_project(ack):
    """Handle view Linear project button - just acknowledge, URL opens in browser."""
    await ack()


# =============================================================================
# FEATURE 2: Cloudflare Tunnel Preview Server
# =============================================================================

async def start_preview_server(project: str, channel: str, thread_ts: str):
    """Start a dev server with Cloudflare Tunnel for live preview."""
    global preview_state

    project_path = get_project_path(project)
    if not project_path or not project_path.exists():
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"❌ Project `{project}` not found."
        )
        return

    # Stop existing preview if running
    if preview_state["running"]:
        await stop_preview_server()

    await app.client.chat_postMessage(
        channel=channel,
        thread_ts=thread_ts,
        text=f"🚀 *Starting preview server for `{project}`...*\n\nThis may take a moment to initialize."
    )

    try:
        # Start the preview script
        process = await asyncio.create_subprocess_exec(
            str(PREVIEW_SCRIPT), project,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        preview_state["process"] = process
        preview_state["project"] = project
        preview_state["running"] = True

        # Read output to get the tunnel URL
        url = None
        try:
            # Wait for URL with timeout
            for _ in range(30):  # 30 second timeout
                if process.stdout:
                    line = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=2.0
                    )
                    line_text = line.decode().strip()
                    logger.info(f"Preview output: {line_text}")

                    # Look for tunnel URL
                    if "https://" in line_text and "trycloudflare.com" in line_text:
                        url = re.search(r'https://[^\s]+trycloudflare\.com[^\s]*', line_text)
                        if url:
                            url = url.group(0)
                            break
                await asyncio.sleep(1)
        except asyncio.TimeoutError:
            pass

        if url:
            preview_state["url"] = url
            await app.client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=f"""✅ *Preview server running!*

*Project:* `{project}`
*Preview URL:* <{url}|{url}>

The dev server is now accessible. Changes you push to the branch will be reflected after a page refresh.

_Use `@nomark preview stop` to shut down the preview server._""",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"✅ *Preview server running!*\n\n*Project:* `{project}`"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Preview URL:* <{url}|Open Preview>"
                        },
                        "accessory": {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Open Preview"},
                            "url": url,
                            "action_id": "open_preview"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "🛑 Stop Preview"},
                                "style": "danger",
                                "action_id": "stop_preview"
                            }
                        ]
                    }
                ]
            )
        else:
            await app.client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text="⚠️ Preview server started but couldn't get tunnel URL. Check `@nomark logs` for details."
            )

    except Exception as e:
        logger.exception(f"Error starting preview: {e}")
        preview_state["running"] = False
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"❌ Failed to start preview server: {str(e)}"
        )


async def stop_preview_server():
    """Stop the preview server."""
    global preview_state

    if preview_state["process"]:
        try:
            preview_state["process"].terminate()
            await asyncio.sleep(1)
            if preview_state["process"].returncode is None:
                preview_state["process"].kill()
        except Exception as e:
            logger.error(f"Error stopping preview: {e}")

    # Also kill any lingering processes
    subprocess.run(["pkill", "-f", "preview-server.sh"], capture_output=True)
    subprocess.run(["pkill", "-f", "cloudflared"], capture_output=True)
    subprocess.run(["pkill", "-f", "npm run dev"], capture_output=True)

    preview_state = {
        "running": False,
        "project": None,
        "url": None,
        "process": None
    }


# =============================================================================
# FEATURE 3: Show File Command
# =============================================================================

async def show_file(project: str, filepath: str, channel: str, thread_ts: str):
    """Show contents of a file from a project."""
    project_path = get_project_path(project)
    if not project_path or not project_path.exists():
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"❌ Project `{project}` not found."
        )
        return

    full_path = project_path / filepath
    if not full_path.exists():
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"❌ File not found: `{filepath}`"
        )
        return

    if not full_path.is_file():
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"❌ `{filepath}` is not a file."
        )
        return

    try:
        content = full_path.read_text()

        # Determine file type for syntax highlighting
        ext = full_path.suffix.lstrip('.')
        lang_map = {
            'ts': 'typescript', 'tsx': 'typescript',
            'js': 'javascript', 'jsx': 'javascript',
            'py': 'python', 'rb': 'ruby',
            'sh': 'bash', 'bash': 'bash',
            'json': 'json', 'yaml': 'yaml', 'yml': 'yaml',
            'md': 'markdown', 'css': 'css', 'html': 'html'
        }
        lang = lang_map.get(ext, ext)

        # Truncate if too long (Slack has message limits)
        if len(content) > 3000:
            content = content[:3000] + "\n\n... (truncated, file too large)"

        # Get line count
        line_count = content.count('\n') + 1

        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"*`{filepath}`* ({line_count} lines)\n```{lang}\n{content}\n```"
        )

    except Exception as e:
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"❌ Error reading file: {str(e)}"
        )


# =============================================================================
# FEATURE 4: Live Progress Updates (edit message with phases)
# =============================================================================

async def update_progress(channel: str, thread_ts: str, message_ts: str, phase: str, detail: str = "", linear_context: dict = None):
    """Update an existing message with new progress. Also posts to Linear if context provided."""
    phase_info = {
        "starting": ("🚀", "Starting", "Initializing task..."),
        "thinking": ("🧠", "Analyzing", "Understanding the codebase and requirements..."),
        "planning": ("📋", "Planning", "Designing implementation approach..."),
        "building": ("🔨", "Building", "Implementing changes..."),
        "testing": ("🧪", "Testing", "Running tests and verification..."),
        "verifying": ("✅", "Verifying", "Final checks and validation..."),
        "committing": ("💾", "Committing", "Creating commits..."),
        "creating_pr": ("🔗", "Creating PR", "Pushing and creating pull request..."),
        "complete": ("✅", "Complete", "Task finished!")
    }

    emoji, title, default_detail = phase_info.get(phase, ("⚙️", phase.title(), ""))
    detail_text = detail if detail else default_detail

    # Build progress bar
    phases = ["thinking", "planning", "building", "testing", "committing", "creating_pr"]
    try:
        current_idx = phases.index(phase)
        progress = "".join(["●" if i <= current_idx else "○" for i in range(len(phases))])
    except ValueError:
        progress = "○○○○○○"

    message = f"{emoji} *{title}*\n{detail_text}\n\n`[{progress}]`"

    try:
        await app.client.chat_update(
            channel=channel,
            ts=message_ts,
            text=message
        )
    except Exception as e:
        logger.error(f"Failed to update progress message: {e}")

    # Post progress to Linear if context provided (only for significant phases)
    if linear_context and phase in ["planning", "building", "testing", "creating_pr"]:
        try:
            linear_message = f"**{emoji} {title}**\n\n{detail_text}"
            await post_linear_comment(
                linear_context.get("prd_id"),
                linear_context.get("story_index", 0),
                linear_message
            )
        except Exception as e:
            logger.warning(f"Failed to post progress to Linear: {e}")


# =============================================================================
# FEATURE 5: Interactive Buttons
# =============================================================================

def create_task_complete_blocks(result: dict) -> list:
    """Create Block Kit blocks for task completion with interactive buttons."""
    task_id = result.get("task_id", "unknown")
    pr_url = result.get("pr_url", "")
    branch = result.get("branch", "")
    project = result.get("project", "")
    commits = result.get("commits", 0)
    files_changed = result.get("files_changed", 0)

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"✅ Task {task_id} Complete"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Commits:* {commits}"},
                {"type": "mrkdwn", "text": f"*Files Changed:* {files_changed}"},
                {"type": "mrkdwn", "text": f"*Branch:* `{branch}`"},
                {"type": "mrkdwn", "text": f"*Project:* `{project}`"}
            ]
        }
    ]

    # Add PR section if available
    if pr_url:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Pull Request:* <{pr_url}|View on GitHub>"}
        })

    # Add action buttons
    action_elements = []

    if pr_url:
        action_elements.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "👀 View PR"},
            "url": pr_url,
            "action_id": "view_pr"
        })
        action_elements.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "✅ Approve PR"},
            "style": "primary",
            "action_id": "approve_pr",
            "value": json.dumps({"pr_url": pr_url, "project": project, "branch": branch})
        })

    action_elements.append({
        "type": "button",
        "text": {"type": "plain_text", "text": "🧪 Run Tests"},
        "action_id": "run_tests",
        "value": json.dumps({"project": project, "branch": branch})
    })

    action_elements.append({
        "type": "button",
        "text": {"type": "plain_text", "text": "👁️ Preview"},
        "action_id": "start_preview",
        "value": json.dumps({"project": project, "branch": branch})
    })

    if action_elements:
        blocks.append({
            "type": "actions",
            "elements": action_elements[:4]  # Slack limits to 5 elements
        })

    # Add follow-up prompt
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": "_Reply in this thread for follow-up tasks, or use the buttons above._"}
        ]
    })

    return blocks


# Button action handlers
@app.action("approve_pr")
async def handle_approve_pr(ack, body, say):
    """Handle PR approval button click."""
    await ack()

    value = json.loads(body["actions"][0]["value"])
    pr_url = value.get("pr_url", "")
    project = value.get("project", "")

    # Extract PR number from URL
    pr_match = re.search(r'/pull/(\d+)', pr_url)
    if pr_match:
        pr_number = pr_match.group(1)
        project_path = get_project_path(project)

        if project_path:
            result = subprocess.run(
                ["gh", "pr", "review", pr_number, "--approve", "-b", "Approved via NOMARK DevOps"],
                cwd=str(project_path),
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                await say(
                    text=f"✅ PR #{pr_number} approved!",
                    thread_ts=body["message"]["thread_ts"] or body["message"]["ts"]
                )
            else:
                await say(
                    text=f"❌ Failed to approve PR: {result.stderr}",
                    thread_ts=body["message"]["thread_ts"] or body["message"]["ts"]
                )


@app.action("run_tests")
async def handle_run_tests(ack, body, say):
    """Handle run tests button click."""
    await ack()

    value = json.loads(body["actions"][0]["value"])
    project = value.get("project", "")
    branch = value.get("branch", "")

    thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]

    await say(
        text=f"🧪 *Running tests for `{project}`...*",
        thread_ts=thread_ts
    )

    project_path = get_project_path(project)
    if project_path:
        # Run tests
        result = subprocess.run(
            ["npm", "test"],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        output = result.stdout[-1500:] if len(result.stdout) > 1500 else result.stdout

        if result.returncode == 0:
            await say(
                text=f"✅ *Tests passed!*\n```\n{output}\n```",
                thread_ts=thread_ts
            )
        else:
            await say(
                text=f"❌ *Tests failed*\n```\n{output}\n{result.stderr[-500:]}\n```",
                thread_ts=thread_ts
            )


@app.action("start_preview")
async def handle_start_preview(ack, body, say):
    """Handle start preview button click."""
    await ack()

    value = json.loads(body["actions"][0]["value"])
    project = value.get("project", "")
    channel = body["channel"]["id"]
    thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]

    await start_preview_server(project, channel, thread_ts)


@app.action("stop_preview")
async def handle_stop_preview(ack, body, say):
    """Handle stop preview button click."""
    await ack()

    await stop_preview_server()

    thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]
    await say(
        text="🛑 Preview server stopped.",
        thread_ts=thread_ts
    )


@app.action("view_pr")
async def handle_view_pr(ack):
    """Handle view PR button click - just acknowledge, URL opens in browser."""
    await ack()


@app.action("open_preview")
async def handle_open_preview(ack):
    """Handle open preview button click - just acknowledge, URL opens in browser."""
    await ack()


@app.action("claude_login_max")
async def handle_claude_login_max(ack, body, say):
    """Handle Claude MAX login button click - start the login flow."""
    await ack()

    channel = body["channel"]["id"]
    thread_ts = body["message"].get("thread_ts") or body["message"]["ts"]

    await say(
        text="🔐 *Starting MAX account login...*\n\nGenerating OAuth login link...",
        thread_ts=thread_ts
    )

    try:
        result = subprocess.run(
            ["ssh", "devops@20.5.185.136", "python3 ~/scripts/claude-login-helper.py start"],
            capture_output=True,
            text=True,
            timeout=60
        )

        try:
            login_result = json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            login_result = {"success": False, "error": result.stdout[:500] or result.stderr[:500]}

        if login_result.get("success"):
            oauth_url = login_result.get("oauth_url", "")

            blocks = [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "🔐 *Claude MAX Login*\n\nClick the button below to sign in with your Anthropic account:"}
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "🔑 Sign in with Anthropic"},
                            "style": "primary",
                            "url": oauth_url,
                            "action_id": "claude_oauth_link"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*After signing in:*\n1. You'll see a code on the callback page\n2. Copy the code\n3. Paste it here: `@nomark claude callback <code>`"}
                }
            ]

            await app.client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text="Click to sign in with your Anthropic MAX account",
                blocks=blocks
            )
        else:
            error = login_result.get("error", "Unknown error")
            await say(
                text=f"❌ *Failed to start login flow:* {error}",
                thread_ts=thread_ts
            )

    except Exception as e:
        await say(
            text=f"❌ *Failed to start login:* {str(e)}",
            thread_ts=thread_ts
        )


@app.action("claude_oauth_link")
async def handle_claude_oauth_link(ack):
    """Handle Claude OAuth link button click - just acknowledge, URL opens in browser."""
    await ack()


# =============================================================================
# FEATURE 6: Slash Commands
# =============================================================================

@app.command("/nomark-task")
async def handle_slash_task(ack, command, say):
    """Handle /nomark-task slash command."""
    await ack()

    text = command.get("text", "").strip()
    channel = command.get("channel_id")
    user = command.get("user_id")

    if not text:
        await say(
            text="*Usage:* `/nomark-task <project> <task description>`\n\n*Example:* `/nomark-task flowmetrics add dark mode toggle`"
        )
        return

    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await say(
            text="Please provide both a project and task description.\n*Example:* `/nomark-task flowmetrics add dark mode toggle`"
        )
        return

    project = parts[0]
    task = parts[1]

    # Post initial message and get thread_ts
    result = await app.client.chat_postMessage(
        channel=channel,
        text=f"🚀 *Task from <@{user}>:* {task}"
    )
    thread_ts = result["ts"]

    # Run the task
    asyncio.create_task(run_task(project, task, channel, thread_ts))


@app.command("/nomark-status")
async def handle_slash_status(ack, command, say):
    """Handle /nomark-status slash command."""
    await ack()

    # Check if any tasks are running
    try:
        result = subprocess.run(
            ["pgrep", "-f", "nomark-task.sh"],
            capture_output=True
        )
        running = result.returncode == 0

        logs = get_recent_logs(3)

        status_emoji = "🟢" if running else "⚪"
        status_text = "Processing a task" if running else "Idle - ready for tasks"

        preview_info = ""
        if preview_state["running"]:
            preview_info = f"\n*Preview:* <{preview_state['url']}|{preview_state['project']}>"

        await say(
            text=f"""*NOMARK DevOps Status*

*VM:* {status_emoji} {status_text}{preview_info}

*Recent Activity:*
{logs}"""
        )
    except Exception as e:
        await say(text=f"Error checking status: {e}")


@app.command("/nomark-preview")
async def handle_slash_preview(ack, command, say):
    """Handle /nomark-preview slash command."""
    await ack()

    text = command.get("text", "").strip()
    channel = command.get("channel_id")

    if text.lower() == "stop":
        await stop_preview_server()
        await say(text="🛑 Preview server stopped.")
        return

    if not text:
        if preview_state["running"]:
            await say(
                text=f"*Preview running:* <{preview_state['url']}|{preview_state['project']}>\n\nUse `/nomark-preview stop` to stop."
            )
        else:
            await say(text="No preview running. Use `/nomark-preview <project>` to start one.")
        return

    # Post message and start preview
    result = await app.client.chat_postMessage(
        channel=channel,
        text=f"🚀 Starting preview for `{text}`..."
    )

    await start_preview_server(text, channel, result["ts"])


# =============================================================================
# Core Task Execution
# =============================================================================

def format_success_message(result: dict) -> str:
    """Format a rich success message like Claude Code."""
    task_id = result.get("task_id", "unknown")
    task = result.get("task", "")
    branch = result.get("branch", "")
    pr_url = result.get("pr_url", "")
    commits = result.get("commits", 0)
    files_changed = result.get("files_changed", 0)
    insertions = result.get("insertions", 0)
    deletions = result.get("deletions", 0)
    files = result.get("files", [])
    commit_messages = result.get("commit_messages", [])
    next_actions = result.get("next_actions", "")

    lines = [
        f"*Task `{task_id}` completed*",
        "",
        f"*{task}*",
        "",
    ]

    # Summary section
    lines.append("*Summary*")
    if commits > 0:
        lines.append(f"Made {commits} commit{'s' if commits != 1 else ''} with {files_changed} file{'s' if files_changed != 1 else ''} changed")
        if insertions or deletions:
            lines.append(f"`+{insertions}` / `-{deletions}` lines")
    else:
        lines.append("No changes were made to the codebase.")
    lines.append("")

    # Commits section
    if commit_messages:
        lines.append("*Commits*")
        for msg in commit_messages[:5]:
            lines.append(f"• {msg}")
        lines.append("")

    # Files changed section
    if files:
        lines.append("*Files Changed*")
        display_files = files[:8]
        for f in display_files:
            lines.append(f"• `{f}`")
        if len(files) > 8:
            lines.append(f"_...and {len(files) - 8} more files_")
        lines.append("")

    # PR link section
    if pr_url:
        lines.append("*Pull Request*")
        lines.append(f"<{pr_url}|View PR on GitHub>")
        lines.append("")

    # Preview section
    if preview_state["running"] and preview_state["url"]:
        lines.append("*Live Preview*")
        lines.append(f"<{preview_state['url']}|Open Preview>")
        lines.append("")

    # Next actions section
    if next_actions:
        lines.append("*Next Steps*")
        lines.append(f"→ {next_actions}")
        if pr_url:
            lines.append("→ Review the changes and merge when ready")
            lines.append("→ Or reply here with follow-up tasks")
        lines.append("")

    lines.append(f"_Branch: `{branch}`_")

    return "\n".join(lines)


def format_error_message(task_id: str, project: str, task: str, error: str) -> str:
    """Format an error message with helpful context."""
    return "\n".join([
        f"*Task `{task_id}` failed*",
        "",
        f"*Task:* {task}",
        f"*Project:* {project}",
        "",
        "*Error*",
        f"```\n{error[:800]}\n```",
        "",
        "*Troubleshooting*",
        "• Check if the project exists and is accessible",
        "• Verify the task description is clear",
        "• Try `@nomark logs` to see detailed logs",
        "",
        "_Reply with a clarified task or try a different approach._"
    ])


async def stop_running_task(thread_ts: str) -> bool:
    """Stop any running task in a thread. Returns True if a task was stopped."""
    if thread_ts in running_processes:
        process = running_processes[thread_ts]
        if process.returncode is None:
            logger.info(f"Stopping running task in thread {thread_ts}")
            try:
                process.terminate()
                await asyncio.sleep(0.5)
                if process.returncode is None:
                    process.kill()
                subprocess.run(["pkill", "-f", "claude"], capture_output=True)
                return True
            except Exception as e:
                logger.error(f"Error stopping task: {e}")
        del running_processes[thread_ts]
    return False


async def run_task(project: str, task: str, channel: str, thread_ts: str, continue_branch: str = None, attachments: list = None, linear_context: dict = None):
    """Run a task and report progress to Slack with rich formatting.

    Args:
        linear_context: Optional dict with {"prd_id": str, "story_index": int} to post progress to Linear
    """
    projects = get_active_projects()
    project_ids = [p["id"] for p in projects]

    if project not in project_ids:
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"❌ Unknown project: `{project}`\n\n{format_project_list()}"
        )
        return

    task_id = datetime.now().strftime("%Y%m%d-%H%M%S")

    # Create initial progress message
    if continue_branch:
        start_message = f"🔄 *Continuing task `{task_id}`*\n\n*Project:* {project}\n*Branch:* `{continue_branch}`"
    else:
        start_message = f"🚀 *Starting task `{task_id}`*\n\n*Project:* {project}\n*Task:* {task}\n\n`[○○○○○○]` Initializing..."

    # Post progress message and save its ts for updates
    progress_msg = await app.client.chat_postMessage(
        channel=channel,
        thread_ts=thread_ts,
        text=start_message
    )
    progress_ts = progress_msg["ts"]
    progress_messages[thread_ts] = progress_ts

    # Post start to Linear if context provided
    if linear_context:
        await post_linear_comment(
            linear_context.get("prd_id"),
            linear_context.get("story_index", 0),
            f"**🚀 Task Started**\n\n**Task:** {task}\n**Project:** {project}"
        )

    # Process any attachments
    attachment_context = ""
    if attachments:
        for attachment in attachments:
            analysis = await process_file_attachment(attachment, f"This file is context for the task: {task}")
            attachment_context += f"\n\n{analysis}"

    try:
        # Update progress: thinking
        await update_progress(channel, thread_ts, progress_ts, "thinking", linear_context=linear_context)

        args = [str(TASK_SCRIPT), project, task]
        if continue_branch:
            args.append(continue_branch)

        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        running_processes[thread_ts] = process

        # Monitor for phase changes (simplified - just periodic updates)
        phases = ["planning", "building", "testing", "committing", "creating_pr"]
        phase_idx = 0

        while process.returncode is None:
            await asyncio.sleep(10)  # Check every 10 seconds
            if phase_idx < len(phases) and process.returncode is None:
                await update_progress(channel, thread_ts, progress_ts, phases[phase_idx], linear_context=linear_context)
                phase_idx += 1

        stdout, stderr = await process.communicate()

        if thread_ts in running_processes:
            del running_processes[thread_ts]

        stdout_text = stdout.decode() if stdout else ""
        stderr_text = stderr.decode() if stderr else ""

        if process.returncode == 0:
            result_file = None
            for line in stdout_text.split('\n'):
                if line.startswith('RESULT_FILE:'):
                    result_file = line.split(':', 1)[1].strip()
                    break

            result = {}
            if result_file:
                result_path = Path(result_file)
                if result_path.exists():
                    try:
                        result = json.loads(result_path.read_text())
                    except Exception as e:
                        logger.error(f"Failed to read result file: {e}")

            if result.get("status") == "success":
                # Update progress to complete
                await update_progress(channel, thread_ts, progress_ts, "complete", "Task finished successfully!", linear_context=linear_context)

                # Send completion message with interactive buttons
                blocks = create_task_complete_blocks(result)
                message = format_success_message(result)

                await app.client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text=message,
                    blocks=blocks
                )

                # Track for follow-ups
                active_tasks[thread_ts] = {
                    "project": project,
                    "branch": result.get("branch", ""),
                    "last_task_id": result.get("task_id", task_id),
                    "pr_url": result.get("pr_url", ""),
                    "channel": channel,
                    "created_at": datetime.now().isoformat()
                }
                save_active_tasks(active_tasks)

                # Post completion to Linear with PR link
                if linear_context:
                    pr_url = result.get("pr_url", "")
                    commits = result.get("commits", 0)
                    files_changed = result.get("files_changed", 0)

                    linear_result = f"""## ✅ Task Complete

**Commits:** {commits}
**Files Changed:** {files_changed}
"""
                    if pr_url:
                        linear_result += f"\n**Pull Request:** [{pr_url}]({pr_url})"

                    # Add preview URL if running
                    if preview_state.get("running") and preview_state.get("url"):
                        linear_result += f"\n\n**Live Preview:** [{preview_state['url']}]({preview_state['url']})"

                    await post_linear_comment(
                        linear_context.get("prd_id"),
                        linear_context.get("story_index", 0),
                        linear_result
                    )

                    # Update Linear status to in_review if PR created
                    if pr_url:
                        await update_linear_story_status(
                            linear_context.get("prd_id"),
                            linear_context.get("story_index", 0),
                            "in_review"
                        )
            else:
                message = f"✅ *Task `{task_id}` completed*\n\n*Project:* {project}\n*Task:* {task}\n\nCheck the branch for changes."
                await app.client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text=message
                )

        else:
            error_msg = stderr_text[:500] if stderr_text else stdout_text[:500] or "Unknown error"
            message = format_error_message(task_id, project, task, error_msg)
            await app.client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=message
            )

            # Post failure to Linear
            if linear_context:
                await post_linear_comment(
                    linear_context.get("prd_id"),
                    linear_context.get("story_index", 0),
                    f"## ❌ Task Failed\n\n```\n{error_msg}\n```"
                )

    except Exception as e:
        logger.exception(f"Task execution error: {e}")
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"❌ *Task failed unexpectedly*\n\n```\n{str(e)}\n```"
        )

        # Post failure to Linear
        if linear_context:
            await post_linear_comment(
                linear_context.get("prd_id"),
                linear_context.get("story_index", 0),
                f"## ❌ Task Failed Unexpectedly\n\n```\n{str(e)}\n```"
            )


# =============================================================================
# Main Event Handler
# =============================================================================

@app.event("app_mention")
async def handle_mention(event, say):
    """Handle @nomark mentions."""
    text = event.get("text", "")
    channel = event.get("channel")
    thread_ts = event.get("thread_ts") or event.get("ts")
    files = event.get("files", [])

    # Remove the mention
    text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

    # Parse command
    parts = text.split(maxsplit=2)
    command = parts[0].lower() if parts else "help"

    # Handle file attachments
    if files and not text:
        # Just an attachment with no text - analyze it
        for file_info in files:
            analysis = await process_file_attachment(file_info)
            await say(text=analysis, thread_ts=thread_ts)
        return

    # Check for follow-up commands in existing thread
    if thread_ts in active_tasks and command not in ["task", "status", "projects", "logs", "help", "done", "merge", "preview", "show", "stop", "cancel", "prd", "register", "linear"]:
        task_context = active_tasks[thread_ts]
        project = task_context["project"]
        task = text

        await say(
            text=f"📎 *Follow-up task on `{project}`*\n\nContinuing on branch `{task_context.get('branch', 'unknown')}`...",
            thread_ts=thread_ts
        )

        asyncio.create_task(run_task(project, task, channel, thread_ts, continue_branch=task_context.get("branch"), attachments=files))
        return

    # Command handlers
    if command == "stop" or command == "cancel":
        try:
            result = subprocess.run(["pkill", "-f", "nomark-task.sh"], capture_output=True)
            subprocess.run(["pkill", "-f", "claude"], capture_output=True)

            if result.returncode == 0:
                await say(
                    text="🛑 *Task stopped*\n\nThe running task has been cancelled.",
                    thread_ts=thread_ts
                )
            else:
                await say(text="No task is currently running.", thread_ts=thread_ts)
        except Exception as e:
            await say(text=f"Error stopping task: {e}", thread_ts=thread_ts)
        return

    if command == "preview":
        if len(parts) > 1 and parts[1].lower() == "stop":
            await stop_preview_server()
            await say(text="🛑 Preview server stopped.", thread_ts=thread_ts)
        elif len(parts) > 1:
            await start_preview_server(parts[1], channel, thread_ts)
        elif preview_state["running"]:
            await say(
                text=f"*Preview running:* <{preview_state['url']}|{preview_state['project']}>\n\nUse `@nomark preview stop` to stop.",
                thread_ts=thread_ts
            )
        else:
            await say(text="No preview running. Use `@nomark preview <project>` to start one.", thread_ts=thread_ts)
        return

    if command == "show":
        if len(parts) < 3:
            await say(
                text="*Usage:* `@nomark show <project> <filepath>`\n\n*Example:* `@nomark show flowmetrics src/app/page.tsx`",
                thread_ts=thread_ts
            )
        else:
            project = parts[1]
            filepath = parts[2]
            await show_file(project, filepath, channel, thread_ts)
        return

    if command == "prd":
        # Parse PRD content - can be pasted directly or in a file attachment
        prd_content = ""

        # Check for file attachments first
        if files:
            for file_info in files:
                if file_info.get("filetype") in ["txt", "md", "json"]:
                    file_data = await download_slack_file(file_info.get("url_private", ""))
                    prd_content = file_data.decode('utf-8', errors='replace')
                    break

        # Otherwise use the text after "prd"
        if not prd_content and len(parts) > 1:
            prd_content = " ".join(parts[1:])

        if not prd_content:
            await say(
                text="""*Usage:* `@nomark prd <paste PRD content or attach file>`

*Examples:*
```
@nomark prd
## Feature: Dark Mode
Add a dark mode toggle to the settings page...
```

Or attach a .txt/.md file with your PRD from Claude.ai.

*Workflow:*
1. Design your feature in Claude.ai
2. Copy the PRD/artifact or download as file
3. Paste here or attach the file
4. Bot parses and executes tasks sequentially""",
                thread_ts=thread_ts
            )
            return

        await say(
            text="📋 *Parsing PRD...*\n\nAnalyzing your specification to extract actionable tasks.",
            thread_ts=thread_ts
        )

        # Parse the PRD
        prd_data = await parse_prd_with_claude(prd_content)

        if "error" in prd_data:
            await say(
                text=f"❌ *Failed to parse PRD:* {prd_data['error']}\n\n_Try reformatting or adding more detail._",
                thread_ts=thread_ts
            )
            return

        # Show preview with confirmation buttons
        text, blocks = format_prd_preview(prd_data)
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=text,
            blocks=blocks
        )
        return

    if command == "threads" or command == "active":
        if not active_tasks:
            await say(text="No active task threads.", thread_ts=thread_ts)
        else:
            lines = ["*Active Task Threads:*\n"]
            for ts, ctx in active_tasks.items():
                branch = ctx.get('branch', 'unknown')
                project = ctx.get('project', 'unknown')
                created = ctx.get('created_at', 'unknown')[:10]
                lines.append(f"• `{project}` - `{branch}` (started {created})")
            await say(text="\n".join(lines), thread_ts=thread_ts)
        return

    if command == "done" or command == "merge":
        if thread_ts in active_tasks:
            task_context = active_tasks[thread_ts]
            del active_tasks[thread_ts]
            save_active_tasks(active_tasks)
            await say(
                text=f"✅ *Task thread closed*\n\nBranch `{task_context.get('branch', 'unknown')}` marked as complete.",
                thread_ts=thread_ts
            )
        else:
            await say(text="No active task in this thread.", thread_ts=thread_ts)
        return

    if command == "register":
        # Register a new project from GitHub URL
        if len(parts) < 2:
            await say(
                text="""*Usage:* `@nomark register <github-url> [project-id]`

*Examples:*
```
@nomark register https://github.com/NOMARJ/inhale-v2
@nomark register https://github.com/owner/repo my-custom-id
```

The bot will:
1. Clone the repository
2. Detect the project stack
3. Install dependencies
4. Set up NOMARK method files
5. Add to projects list

_After registration, use `@nomark task <project-id> <description>` to run tasks._""",
                thread_ts=thread_ts
            )
            return

        github_url = parts[1]

        # Clean Slack URL formatting: <url> or <url|label> -> url
        if github_url.startswith('<') and '>' in github_url:
            github_url = github_url.strip('<>').split('|')[0]

        project_id = parts[2] if len(parts) > 2 else None

        asyncio.create_task(register_project(github_url, project_id, channel, thread_ts))
        return

    if command == "linear":
        # Linear integration commands
        if len(parts) < 2:
            await say(
                text="""*Usage:* `@nomark linear <subcommand>`

*Subcommands:*
• `@nomark linear sync <project>` - Sync project to Linear
• `@nomark linear import [project]` - Import existing Linear epics/issues
• `@nomark linear prds` - List PRDs synced to Linear
• `@nomark linear status` - Show Linear connection status

*Workflows:*

*1. Slack-first (PRD → Linear):*
Submit a PRD → Auto-creates Epic + Issues in Linear
Move issue to "In Progress" → NOMARK starts working

*2. Linear-first (Epic → NOMARK):*
Create Epic + Issues in Linear → `@nomark linear import`
Move issue to "In Progress" → NOMARK starts working

_Requires `LINEAR_API_KEY` to be configured._""",
                thread_ts=thread_ts
            )
            return

        subcommand = parts[1].lower()

        if subcommand == "status":
            if not LINEAR_API_KEY:
                await say(
                    text="❌ *Linear not configured*\n\nSet `LINEAR_API_KEY` environment variable on the VM.",
                    thread_ts=thread_ts
                )
            else:
                mapping = load_linear_mapping()
                projects_count = len(mapping.get("projects", {}))
                prds_count = len(mapping.get("prds", {}))
                await say(
                    text=f"""✅ *Linear Connected*

*Projects synced:* {projects_count}
*PRDs synced:* {prds_count}

_Use `@nomark linear prds` to see details._""",
                    thread_ts=thread_ts
                )
            return

        if subcommand == "prds":
            mapping = load_linear_mapping()
            prds = mapping.get("prds", {})

            if not prds:
                await say(
                    text="No PRDs synced to Linear yet.\n\n_Submit a PRD with `@nomark prd` - it will automatically sync._",
                    thread_ts=thread_ts
                )
                return

            lines = ["*PRDs synced to Linear:*\n"]
            for prd_id, prd_data in prds.items():
                epic_url = prd_data.get("epic_url", "")
                title = prd_data.get("title", "Untitled")
                stories = len(prd_data.get("stories", []))
                project = prd_data.get("project_id", "unknown")
                lines.append(f"• <{epic_url}|{title}> ({stories} stories) - `{project}`")

            await say(text="\n".join(lines), thread_ts=thread_ts)
            return

        if subcommand == "sync":
            if len(parts) < 3:
                await say(
                    text="*Usage:* `@nomark linear sync <project-id>`",
                    thread_ts=thread_ts
                )
                return

            project_id = parts[2]
            project_path = Path.home() / "repos" / project_id

            if not project_path.exists():
                await say(
                    text=f"❌ Project `{project_id}` not found.",
                    thread_ts=thread_ts
                )
                return

            # Load project info
            with open(PROJECTS_FILE) as f:
                projects = json.load(f)
            project_info = next(
                (p for p in projects.get("projects", []) if p["id"] == project_id),
                {"id": project_id, "name": project_id}
            )

            await say(
                text=f"📊 *Syncing project `{project_id}` to Linear...*",
                thread_ts=thread_ts
            )

            try:
                import sys
                sys.path.insert(0, str(Path.home() / "scripts"))
                from importlib import import_module

                if "linear_integration" in sys.modules:
                    del sys.modules["linear_integration"]
                linear_module = import_module("linear_integration")

                sync = linear_module.PRDLinearSync()
                result = await sync.sync_project(project_id, project_info)

                await say(
                    text=f"✅ *Project synced to Linear*\n\nProject: `{result['name']}`",
                    thread_ts=thread_ts
                )
            except Exception as e:
                await say(
                    text=f"❌ *Sync failed:* {str(e)}",
                    thread_ts=thread_ts
                )
            return

        if subcommand == "import":
            # Import existing Linear epics/issues into NOMARK
            project_id = parts[2] if len(parts) > 2 else None

            if project_id:
                # Import specific project
                await say(
                    text=f"📥 *Importing from Linear for `{project_id}`...*",
                    thread_ts=thread_ts
                )

                try:
                    import sys
                    sys.path.insert(0, str(Path.home() / "scripts"))
                    from importlib import import_module

                    if "linear_integration" in sys.modules:
                        del sys.modules["linear_integration"]
                    linear_module = import_module("linear_integration")

                    sync = linear_module.PRDLinearSync()
                    result = await sync.sync_from_linear(project_id)

                    await say(
                        text=f"""✅ *Linear Import Complete*

*Project:* `{result['project']}` → {result['linear_project']}
*Epics imported:* {result['total_epics']}
*Stories imported:* {result['total_stories']}

*Epics:* {', '.join(result['epics_imported']) or 'None'}

_Move any issue to "In Progress" in Linear to trigger NOMARK automation._""",
                        thread_ts=thread_ts
                    )
                except Exception as e:
                    await say(
                        text=f"❌ *Import failed:* {str(e)}",
                        thread_ts=thread_ts
                    )
            else:
                # Import all registered projects
                await say(
                    text="📥 *Importing from Linear for all registered projects...*",
                    thread_ts=thread_ts
                )

                try:
                    import sys
                    sys.path.insert(0, str(Path.home() / "scripts"))
                    from importlib import import_module

                    if "linear_integration" in sys.modules:
                        del sys.modules["linear_integration"]
                    linear_module = import_module("linear_integration")

                    with open(PROJECTS_FILE) as f:
                        projects_config = json.load(f)

                    sync = linear_module.PRDLinearSync()
                    results = []
                    total_epics = 0
                    total_stories = 0

                    for project in projects_config.get("projects", []):
                        proj_id = project["id"]
                        try:
                            result = await sync.sync_from_linear(proj_id)
                            results.append(f"✓ `{proj_id}`: {result['total_epics']} epics, {result['total_stories']} stories")
                            total_epics += result['total_epics']
                            total_stories += result['total_stories']
                        except Exception as e:
                            results.append(f"✗ `{proj_id}`: {str(e)}")

                    await say(
                        text=f"""✅ *Linear Import Complete*

*Total:* {total_epics} epics, {total_stories} stories

*Results:*
{chr(10).join(results)}

_Move any issue to "In Progress" in Linear to trigger NOMARK automation._""",
                        thread_ts=thread_ts
                    )
                except Exception as e:
                    await say(
                        text=f"❌ *Import failed:* {str(e)}",
                        thread_ts=thread_ts
                    )
            return

        await say(
            text=f"Unknown Linear subcommand: `{subcommand}`\n\nUse `@nomark linear` to see available commands.",
            thread_ts=thread_ts
        )
        return

    if command == "claude":
        # Claude Code management commands
        if len(parts) < 2:
            await say(
                text="""*Usage:* `@nomark claude <subcommand>`

*Subcommands:*
• `@nomark claude status` - Check Claude Code auth status
• `@nomark claude token <token>` - Set OAuth token *(Recommended for re-auth)*
• `@nomark claude login` - Start MAX account login (interactive)
• `@nomark claude login <api-key>` - Set up with API key
• `@nomark claude callback <code>` - Complete login with auth code
• `@nomark claude version` - Show Claude Code version
• `@nomark claude mcp` - Check MCP server status

*Easiest Re-authentication (Recommended):*
1. On your Mac: `claude setup-token`
2. Complete browser OAuth
3. Copy the `sk-ant-oat01-...` token
4. Paste here: `@nomark claude token <token>`

_Claude Code needs authentication to run tasks._""",
                thread_ts=thread_ts
            )
            return

        subcommand = parts[1].lower()

        if subcommand == "status":
            try:
                # Check auth status
                result = subprocess.run(
                    ["ssh", "devops@20.5.185.136", "python3 ~/scripts/claude-login-helper.py status 2>/dev/null || claude auth status 2>&1"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                output = result.stdout.strip() or result.stderr.strip()

                # Try to parse JSON result
                try:
                    status_data = json.loads(output)
                    is_authenticated = status_data.get("authenticated", False)
                except json.JSONDecodeError:
                    is_authenticated = "Invalid API key" not in output and "Please run /login" not in output

                if is_authenticated:
                    status_emoji = "✅"
                    status_text = "Authenticated"
                    blocks = [
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": f"*Claude Code Status*\n\n*Auth:* {status_emoji} {status_text}\n\n_Ready to run tasks!_"}
                        }
                    ]
                else:
                    status_emoji = "❌"
                    status_text = "Not authenticated"
                    blocks = [
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": f"*Claude Code Status*\n\n*Auth:* {status_emoji} {status_text}"}
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "🔐 Login with MAX Account"},
                                    "style": "primary",
                                    "action_id": "claude_login_max"
                                }
                            ]
                        },
                        {
                            "type": "context",
                            "elements": [
                                {"type": "mrkdwn", "text": "_Or use `@nomark claude login <api-key>` for API key auth_"}
                            ]
                        }
                    ]

                await app.client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text=f"*Claude Code Status:* {status_emoji} {status_text}",
                    blocks=blocks
                )
            except Exception as e:
                await say(
                    text=f"❌ *Failed to check Claude status:* {str(e)}",
                    thread_ts=thread_ts
                )
            return

        if subcommand == "version":
            try:
                result = subprocess.run(
                    ["ssh", "devops@20.5.185.136", "claude --version 2>&1"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                version = result.stdout.strip() or "Unknown"

                await say(
                    text=f"*Claude Code Version:* `{version}`",
                    thread_ts=thread_ts
                )
            except Exception as e:
                await say(
                    text=f"❌ *Failed to get version:* {str(e)}",
                    thread_ts=thread_ts
                )
            return

        if subcommand == "login":
            # Check if API key provided
            if len(parts) >= 3:
                api_key = parts[2]

                # Validate key format
                if not api_key.startswith("sk-ant-"):
                    await say(
                        text="⚠️ That doesn't look like a valid Anthropic API key (should start with `sk-ant-`).\n\nFor MAX subscription, use `@nomark claude login` without a key.",
                        thread_ts=thread_ts
                    )
                    return

                await say(
                    text="🔐 *Setting up Claude Code with API key...*",
                    thread_ts=thread_ts
                )

                try:
                    # Set the API key directly in settings
                    result = subprocess.run(
                        ["ssh", "devops@20.5.185.136", f"mkdir -p ~/.claude && cat > ~/.claude/settings.json << 'EOF'\n{{\"apiKey\": \"{api_key}\"}}\nEOF"],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )

                    # Verify it worked
                    verify_result = subprocess.run(
                        ["ssh", "devops@20.5.185.136", "claude auth status 2>&1"],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )

                    if "Invalid API key" not in verify_result.stdout and "Please run /login" not in verify_result.stdout:
                        await say(
                            text="✅ *Claude Code authenticated with API key!*\n\nYou can now run tasks with `@nomark task <project> <description>`",
                            thread_ts=thread_ts
                        )
                    else:
                        await say(
                            text="⚠️ *API key set but verification unclear*\n\nTry running a task to test: `@nomark task flowmetrics check auth`",
                            thread_ts=thread_ts
                        )
                except Exception as e:
                    await say(
                        text=f"❌ *Failed to set up API key:* {str(e)}",
                        thread_ts=thread_ts
                    )
                return

            # No API key - start interactive MAX login
            await say(
                text="🔐 *Starting MAX account login...*\n\nGenerating OAuth login link...",
                thread_ts=thread_ts
            )

            try:
                result = subprocess.run(
                    ["ssh", "devops@20.5.185.136", "python3 ~/scripts/claude-login-helper.py start"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                try:
                    login_result = json.loads(result.stdout.strip())
                except json.JSONDecodeError:
                    login_result = {"success": False, "error": result.stdout[:500] or result.stderr[:500]}

                if login_result.get("success"):
                    oauth_url = login_result.get("oauth_url", "")

                    blocks = [
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": "🔐 *Claude MAX Login*\n\nClick the button below to sign in with your Anthropic account:"}
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "🔑 Sign in with Anthropic"},
                                    "style": "primary",
                                    "url": oauth_url,
                                    "action_id": "claude_oauth_link"
                                }
                            ]
                        },
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": "*After signing in:*\n1. You'll see a code on the callback page\n2. Copy the code\n3. Paste it here: `@nomark claude callback <code>`"}
                        },
                        {
                            "type": "context",
                            "elements": [
                                {"type": "mrkdwn", "text": f"_Link expires in 10 minutes. If you can't click the button, copy this URL:_\n`{oauth_url[:100]}...`"}
                            ]
                        }
                    ]

                    await app.client.chat_postMessage(
                        channel=channel,
                        thread_ts=thread_ts,
                        text="Click to sign in with your Anthropic MAX account",
                        blocks=blocks
                    )
                else:
                    error = login_result.get("error", "Unknown error")
                    await say(
                        text=f"❌ *Failed to start login flow:* {error}\n\n*Alternative:* SSH to VM and run:\n```\nssh devops@20.5.185.136\nclaude\n/login\n```",
                        thread_ts=thread_ts
                    )

            except Exception as e:
                await say(
                    text=f"❌ *Failed to start login:* {str(e)}",
                    thread_ts=thread_ts
                )
            return

        if subcommand == "callback":
            # Complete login with OAuth callback code
            if len(parts) < 3:
                await say(
                    text="*Usage:* `@nomark claude callback <code>`\n\nPaste the code you received after signing in.",
                    thread_ts=thread_ts
                )
                return

            code = parts[2]

            await say(
                text="🔐 *Completing authentication...*",
                thread_ts=thread_ts
            )

            try:
                result = subprocess.run(
                    ["ssh", "devops@20.5.185.136", f"python3 ~/scripts/claude-login-helper.py callback '{code}'"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                try:
                    callback_result = json.loads(result.stdout.strip())
                except json.JSONDecodeError:
                    callback_result = {"success": False, "error": result.stdout[:500] or result.stderr[:500]}

                if callback_result.get("success"):
                    await say(
                        text="✅ *Claude Code authenticated successfully with MAX account!*\n\nYou can now run tasks with `@nomark task <project> <description>`",
                        thread_ts=thread_ts
                    )
                else:
                    error = callback_result.get("error", "Unknown error")
                    await say(
                        text=f"❌ *Authentication failed:* {error}\n\nTry `@nomark claude login` to start over.",
                        thread_ts=thread_ts
                    )

            except Exception as e:
                await say(
                    text=f"❌ *Failed to complete authentication:* {str(e)}",
                    thread_ts=thread_ts
                )
            return

        if subcommand == "token":
            # Set OAuth token directly (easiest re-auth method)
            if len(parts) < 3:
                await say(
                    text="""*OAuth Token Authentication (Recommended for Re-auth)*

This is the easiest way to authenticate Claude Code on the VM.

*Steps:*
1. On your local Mac, run: `claude setup-token`
2. Complete the browser OAuth flow
3. Copy the token that starts with `sk-ant-oat01-...`
4. Paste it here: `@nomark claude token <your-token>`

*Example:*
```
@nomark claude token sk-ant-oat01-ABC123...
```

_The token will be securely stored on the VM._""",
                    thread_ts=thread_ts
                )
                return

            oauth_token = parts[2]

            # Validate token format
            if not oauth_token.startswith("sk-ant-oat01-"):
                await say(
                    text="⚠️ That doesn't look like an OAuth token (should start with `sk-ant-oat01-`).\n\n• For OAuth token: Run `claude setup-token` locally, then use `@nomark claude token <token>`\n• For API key: Use `@nomark claude login <api-key>` (starts with `sk-ant-api`)",
                    thread_ts=thread_ts
                )
                return

            await say(
                text="🔐 *Setting OAuth token on VM...*",
                thread_ts=thread_ts
            )

            try:
                # Set the OAuth token in ~/.bashrc for persistence
                # First remove any existing CLAUDE_CODE_OAUTH_TOKEN line, then add new one
                result = subprocess.run(
                    ["ssh", "devops@20.5.185.136", f"""
sed -i '/^export CLAUDE_CODE_OAUTH_TOKEN=/d' ~/.bashrc 2>/dev/null || true
echo 'export CLAUDE_CODE_OAUTH_TOKEN="{oauth_token}"' >> ~/.bashrc
export CLAUDE_CODE_OAUTH_TOKEN="{oauth_token}"
claude --print 'Say OK if you can hear me' 2>&1
"""],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                output = result.stdout.strip()

                # Check if Claude responded
                if "OK" in output or "ok" in output.lower() or result.returncode == 0:
                    await say(
                        text="✅ *Claude Code authenticated with OAuth token!*\n\n• Token saved to VM's `~/.bashrc` for persistence\n• Ready to run tasks: `@nomark task <project> <description>`",
                        thread_ts=thread_ts
                    )
                else:
                    # Token set but verification unclear
                    await say(
                        text=f"⚠️ *Token set but verification unclear*\n\nResponse: `{output[:200]}`\n\nTry running a task to test: `@nomark task flowmetrics say hello`",
                        thread_ts=thread_ts
                    )

            except Exception as e:
                await say(
                    text=f"❌ *Failed to set OAuth token:* {str(e)}",
                    thread_ts=thread_ts
                )
            return

        if subcommand == "mcp":
            # Check MCP server status
            try:
                result = subprocess.run(
                    ["ssh", "devops@20.5.185.136", "cat ~/.claude.json 2>/dev/null | python3 -c \"import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('mcpServers',{}), indent=2))\" 2>/dev/null || echo '{}'"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                output = result.stdout.strip()

                if output == "{}" or not output:
                    mcp_text = "No MCP servers configured"
                else:
                    mcp_text = f"```\n{output}\n```"

                await say(
                    text=f"""*Claude Code MCP Servers*

{mcp_text}

*To add Linear MCP:*
```
ssh devops@20.5.185.136
claude mcp add --transport sse linear-server https://mcp.linear.app/sse
```
Then run `/mcp` in Claude to complete OAuth.""",
                    thread_ts=thread_ts
                )
            except Exception as e:
                await say(
                    text=f"❌ *Failed to check MCP status:* {str(e)}",
                    thread_ts=thread_ts
                )
            return

        await say(
            text=f"Unknown claude subcommand: `{subcommand}`\n\nUse `@nomark claude` to see available commands.",
            thread_ts=thread_ts
        )
        return

    if command == "task":
        if len(parts) < 3:
            await say(
                text="""*Usage:* `@nomark task <project> <task description>`

*Examples:*
```
@nomark task flowmetrics add dark mode toggle
@nomark task flowmetrics fix login redirect bug
```

Use `@nomark projects` to see available projects.""",
                thread_ts=thread_ts
            )
            return

        project = parts[1]
        task = parts[2]

        if await stop_running_task(thread_ts):
            await say(
                text="🔄 *Stopping previous task...*\nStarting your corrected task instead.",
                thread_ts=thread_ts
            )
            await asyncio.sleep(1)

        asyncio.create_task(run_task(project, task, channel, thread_ts, attachments=files))

    elif command == "status":
        try:
            result = subprocess.run(["pgrep", "-f", "nomark-task.sh"], capture_output=True)
            running = result.returncode == 0
            logs = get_recent_logs(3)

            status_emoji = "🟢" if running else "⚪"
            status_text = "Processing a task" if running else "Idle - ready for tasks"

            preview_info = ""
            if preview_state["running"]:
                preview_info = f"\n*Preview:* <{preview_state['url']}|{preview_state['project']}>"

            await say(
                text=f"*NOMARK DevOps Status*\n\n*VM:* {status_emoji} {status_text}{preview_info}\n\n*Recent Activity:*\n{logs}",
                thread_ts=thread_ts
            )
        except Exception as e:
            await say(text=f"Error checking status: {e}", thread_ts=thread_ts)

    elif command == "projects":
        await say(text=format_project_list(), thread_ts=thread_ts)

    elif command == "logs":
        n = 10
        if len(parts) > 1:
            try:
                n = int(parts[1])
                n = min(max(n, 1), 50)
            except ValueError:
                pass
        await say(text=get_recent_logs(n), thread_ts=thread_ts)

    else:
        help_text = """*NOMARK DevOps Bot*

I help automate development tasks using Claude Code and the NOMARK method.

*Commands:*
• `@nomark task <project> <description>` - Run a development task
• `@nomark prd <content>` - Execute a PRD from Claude.ai
• `@nomark register <github-url>` - Register a new project
• `@nomark linear <subcommand>` - Linear integration
• `@nomark claude <subcommand>` - Claude Code auth management
• `@nomark status` - Check VM and task status
• `@nomark projects` - List available projects
• `@nomark logs [n]` - Show recent log entries
• `@nomark preview <project>` - Start live preview server
• `@nomark preview stop` - Stop preview server
• `@nomark show <project> <filepath>` - View a file
• `@nomark stop` - Stop running task

*Claude Code Auth:*
`@nomark claude status` - Check auth status
`@nomark claude token <token>` - Set OAuth token *(easiest re-auth)*
`@nomark claude login <api-key>` - Set API key
`@nomark claude mcp` - Check MCP servers

*Linear Integration:*
Two workflows supported:
1. PRD → Linear: Submit PRD → Auto-creates Epic + Issues
2. Linear → NOMARK: Create in Linear → `@nomark linear import`
Move issues to "In Progress" → NOMARK starts working

*Claude.ai Integration:*
Design in Claude.ai → Copy PRD → Paste with `@nomark prd`
The bot parses your spec and executes tasks sequentially!

*Project Registration:*
Register any GitHub repo: `@nomark register https://github.com/owner/repo`
The bot clones, detects stack, and sets up NOMARK method!

*Attachments:*
Upload screenshots or files with your message for context!

*Examples:*
```
@nomark task flowmetrics add priority filter to task list
@nomark register https://github.com/NOMARJ/inhale-v2
@nomark claude status
```"""
        await say(text=help_text, thread_ts=thread_ts)


@app.event("message")
async def handle_message(event, logger):
    """Handle direct messages and file shares."""
    if event.get("channel_type") == "im":
        logger.info(f"DM received: {event.get('text', '')[:50]}")


async def main():
    """Start the Slack bot."""
    logger.info("Starting NOMARK DevOps Slack bot...")

    if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
        logger.error("Error: SLACK_BOT_TOKEN and SLACK_APP_TOKEN required")
        return

    logger.info("Tokens validated, connecting to Slack...")
    handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN)
    logger.info("🤖 NOMARK DevOps Slack bot starting...")
    logger.info("   Features: Tasks, Attachments, Preview, Buttons, Slash Commands")
    await handler.start_async()


if __name__ == "__main__":
    logger.info("Bot script starting...")
    asyncio.run(main())
