#!/usr/bin/env python3
"""
Linear Webhook Server for NOMARK DevOps

Receives webhooks from Linear when issues change status.
When a NOMARK-tracked issue moves to "In Progress", triggers automation.

Run with: python linear-webhook.py
Listens on port 8765 by default.

Setup:
1. Configure Linear webhook at: https://linear.app/settings/api
2. Point to: https://your-domain/webhook/linear
3. Enable "Issue" events
"""

import os
import json
import asyncio
import logging
import hmac
import hashlib
from pathlib import Path
from aiohttp import web

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
LINEAR_WEBHOOK_SECRET = os.environ.get("LINEAR_WEBHOOK_SECRET", "")
WEBHOOK_PORT = int(os.environ.get("LINEAR_WEBHOOK_PORT", "8765"))
LINEAR_MAPPING_FILE = Path.home() / "config" / "linear-mapping.json"
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")  # For notifications


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify Linear webhook signature."""
    if not LINEAR_WEBHOOK_SECRET:
        logger.warning("LINEAR_WEBHOOK_SECRET not set - skipping verification")
        return True

    expected = hmac.new(
        LINEAR_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)


def load_linear_mapping() -> dict:
    """Load Linear ID mappings."""
    if LINEAR_MAPPING_FILE.exists():
        with open(LINEAR_MAPPING_FILE) as f:
            return json.load(f)
    return {"projects": {}, "prds": {}, "stories": {}}


async def find_nomark_issue(issue_id: str) -> dict:
    """Find NOMARK tracking info for a Linear issue."""
    mapping = load_linear_mapping()

    for prd_id, prd_data in mapping.get("prds", {}).items():
        for story in prd_data.get("stories", []):
            if story.get("linear_id") == issue_id:
                return {
                    "found": True,
                    "prd_id": prd_id,
                    "project_id": prd_data.get("project_id"),
                    "story_index": story.get("story_index"),
                    "story_title": story.get("title"),
                    "identifier": story.get("identifier")
                }

    return {"found": False}


async def download_and_analyze_attachment(url: str, filename: str) -> str:
    """Download a Linear attachment and analyze if it's an image."""
    import httpx

    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    if not ANTHROPIC_API_KEY:
        return f"[Attachment: {filename}]({url})"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            if response.status_code != 200:
                return f"[Attachment: {filename}]({url})"

            file_data = response.content

            # Check if it's an image
            ext = filename.split('.')[-1].lower() if '.' in filename else ''
            if ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                import base64
                base64_image = base64.b64encode(file_data).decode('utf-8')
                media_type = f"image/{ext}" if ext != 'jpg' else "image/jpeg"

                # Analyze with Claude Vision
                vision_response = await client.post(
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
                                    "text": "Describe what you see in this image. If it's a screenshot of a bug or UI issue, explain what the problem appears to be."
                                }
                            ]
                        }]
                    },
                    timeout=60.0
                )

                if vision_response.status_code == 200:
                    result = vision_response.json()
                    analysis = result["content"][0]["text"]
                    return f"**Image Analysis ({filename}):**\n{analysis}"

            return f"[Attachment: {filename}]({url})"

    except Exception as e:
        logger.warning(f"Failed to process attachment {filename}: {e}")
        return f"[Attachment: {filename}]({url})"


async def trigger_nomark_task(trigger_data: dict):
    """Trigger NOMARK task execution."""
    import subprocess

    project_id = trigger_data["project_id"]
    story_title = trigger_data["story_title"]
    prd_id = trigger_data["prd_id"]
    story_index = trigger_data["story_index"]
    identifier = trigger_data["identifier"]
    attachments = trigger_data.get("attachments", [])
    is_followup = trigger_data.get("is_followup", False)

    logger.info(f"Triggering NOMARK: {identifier} - {story_title}")

    # Process attachments if any
    attachment_context = ""
    if attachments:
        logger.info(f"Processing {len(attachments)} attachments...")
        for att in attachments:
            att_url = att.get("url", "")
            att_name = att.get("title", att.get("filename", "attachment"))
            if att_url:
                analysis = await download_and_analyze_attachment(att_url, att_name)
                attachment_context += f"\n\n{analysis}"

    # Combine story title with attachment context
    full_task = story_title
    if attachment_context:
        full_task = f"{story_title}\n\nAttachment Context:{attachment_context}"

    # Post to Linear that we're starting
    try:
        import sys
        sys.path.insert(0, str(Path.home() / "scripts"))

        # Import fresh
        if "linear_integration" in sys.modules:
            del sys.modules["linear_integration"]
        from linear_integration import PRDLinearSync

        sync = PRDLinearSync()

        start_msg = f"🤖 **NOMARK DevOps Starting**\n\n"
        if is_followup:
            start_msg += f"**Follow-up task:** {story_title}\n"
        else:
            start_msg += "Automation triggered from Linear.\n"
        if attachments:
            start_msg += f"\n**Attachments:** {len(attachments)} file(s) included"

        await sync.post_progress(prd_id, story_index, start_msg)
    except Exception as e:
        logger.warning(f"Failed to post Linear comment: {e}")

    # Execute the task - use full_task which includes attachment context
    task_script = Path.home() / "scripts" / "nomark-task.sh"

    try:
        process = await asyncio.create_subprocess_exec(
            str(task_script), project_id, full_task,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()
        stdout_text = stdout.decode() if stdout else ""

        # Extract result file
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

            try:
                sync = PRDLinearSync()
                await sync.post_progress(prd_id, story_index, result_message)

                if pr_url:
                    await sync.update_story_status(prd_id, story_index, "in_review")
            except Exception as e:
                logger.warning(f"Failed to update Linear: {e}")

            logger.info(f"Task completed: {commits} commits, {files_changed} files")

            return {"status": "success", "pr_url": pr_url}

        return {"status": "completed", "message": "Task finished but no result file"}

    except Exception as e:
        logger.exception(f"Task execution failed: {e}")

        # Post failure to Linear
        try:
            sync = PRDLinearSync()
            await sync.post_progress(
                prd_id, story_index,
                f"❌ **Task Failed**\n\n```\n{str(e)}\n```"
            )
        except:
            pass

        return {"status": "error", "error": str(e)}


async def handle_comment_task(issue_id: str, comment_body: str, comment_user: str, attachments: list = None):
    """Handle a comment on a Linear issue as a follow-up task request."""
    # Find NOMARK tracking info for this issue
    nomark_info = await find_nomark_issue(issue_id)

    if not nomark_info.get("found"):
        logger.info(f"Comment on non-NOMARK issue {issue_id}, ignoring")
        return {"status": "ignored", "reason": "Issue not tracked by NOMARK"}

    # Check if comment starts with a trigger word (like @nomark in Slack)
    # Or just treat any comment as a follow-up task
    comment_lower = comment_body.lower().strip()

    # Ignore bot's own comments
    if comment_body.startswith("**🚀") or comment_body.startswith("**📋") or \
       comment_body.startswith("**🔨") or comment_body.startswith("**🧪") or \
       comment_body.startswith("## ✅") or comment_body.startswith("## ❌") or \
       "NOMARK DevOps" in comment_body:
        logger.info("Ignoring bot's own comment")
        return {"status": "ignored", "reason": "Bot comment"}

    # Check for explicit triggers or commands
    is_task_request = False
    task_description = comment_body

    # Explicit triggers
    if comment_lower.startswith("@nomark ") or comment_lower.startswith("/nomark "):
        task_description = comment_body.split(" ", 1)[1] if " " in comment_body else ""
        is_task_request = True
    elif comment_lower.startswith("task:") or comment_lower.startswith("do:"):
        task_description = comment_body.split(":", 1)[1].strip() if ":" in comment_body else ""
        is_task_request = True
    elif comment_lower.startswith("fix ") or comment_lower.startswith("add ") or \
         comment_lower.startswith("update ") or comment_lower.startswith("change ") or \
         comment_lower.startswith("implement ") or comment_lower.startswith("create "):
        # Looks like a task request
        is_task_request = True
    elif attachments:
        # If there are attachments, treat it as a task request (like uploading a screenshot)
        is_task_request = True
        if not task_description.strip():
            task_description = "Fix the issue shown in the attached screenshot"

    if not is_task_request or not task_description.strip():
        logger.info(f"Comment doesn't look like a task request: {comment_body[:50]}...")
        return {"status": "ignored", "reason": "Not a task request"}

    logger.info(f"Comment task request on {nomark_info['identifier']}: {task_description[:50]}...")
    if attachments:
        logger.info(f"  with {len(attachments)} attachment(s)")

    # Trigger the task with the comment as description
    trigger_data = {
        **nomark_info,
        "story_title": task_description,  # Use comment as task description
        "is_followup": True,
        "original_story": nomark_info["story_title"],
        "requested_by": comment_user,
        "attachments": attachments or []
    }

    asyncio.create_task(trigger_nomark_task(trigger_data))

    return {
        "status": "triggered",
        "identifier": nomark_info["identifier"],
        "task": task_description[:100],
        "attachments": len(attachments) if attachments else 0
    }


async def handle_webhook(request: web.Request) -> web.Response:
    """Handle incoming Linear webhook."""
    # Verify signature
    signature = request.headers.get("Linear-Signature", "")
    body = await request.read()

    if not verify_signature(body, signature):
        logger.warning("Invalid webhook signature")
        return web.json_response({"error": "Invalid signature"}, status=401)

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    action = payload.get("action")
    event_type = payload.get("type")
    data = payload.get("data", {})

    logger.info(f"Webhook received: {event_type} - {action}")

    # Handle Comment events (like Slack thread replies)
    if event_type == "Comment" and action == "create":
        issue = data.get("issue", {})
        issue_id = issue.get("id")
        comment_body = data.get("body", "")
        comment_user = data.get("user", {}).get("name", "Unknown")

        # Extract attachments from comment (Linear includes them in the documentContent)
        # Linear attachments can be in data.documentContent or inline in body as markdown links
        attachments = []

        # Check for explicit attachments array
        if "attachments" in data:
            attachments = data["attachments"]

        # Also parse markdown image/file links from body
        # Format: ![alt](url) or [filename](url)
        import re
        link_pattern = r'!?\[([^\]]*)\]\((https?://[^\)]+)\)'
        for match in re.finditer(link_pattern, comment_body):
            title = match.group(1) or "attachment"
            url = match.group(2)
            # Filter for actual file attachments (Linear CDN, etc.)
            if "linear" in url or "uploads" in url or any(ext in url.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip']):
                attachments.append({"title": title, "url": url})

        if issue_id and (comment_body or attachments):
            result = await handle_comment_task(issue_id, comment_body, comment_user, attachments)
            return web.json_response(result)

        return web.json_response({"status": "ignored", "reason": "Missing issue or comment data"})

    # Handle Issue creation (auto-track new issues in NOMARK projects)
    if event_type == "Issue" and action == "create":
        try:
            import sys
            sys.path.insert(0, str(Path.home() / "scripts"))

            if "linear_integration" in sys.modules:
                del sys.modules["linear_integration"]
            from linear_integration import PRDLinearSync

            sync = PRDLinearSync()
            result = await sync.track_new_issue(data)

            if result and result.get("tracked"):
                logger.info(f"Auto-tracked new issue: {result}")
                return web.json_response({
                    "status": "tracked",
                    "type": result.get("type"),
                    "prd_id": result.get("prd_id"),
                    "identifier": result.get("identifier")
                })

        except Exception as e:
            logger.warning(f"Failed to auto-track issue: {e}")

        return web.json_response({"status": "ignored", "reason": "Issue not in tracked project"})

    # Handle Issue updates (status changes)
    if event_type == "Issue" and action == "update":
        # Check if state changed
        updated_from = payload.get("updatedFrom", {})
        if "stateId" not in updated_from:
            return web.json_response({"status": "ignored", "reason": "No state change"})

        # Check if moving to "started" (In Progress)
        state = data.get("state", {})
        if state.get("type") != "started":
            return web.json_response({"status": "ignored", "reason": "Not moving to In Progress"})

        # Find NOMARK tracking info
        issue_id = data.get("id")
        nomark_info = await find_nomark_issue(issue_id)

        if not nomark_info.get("found"):
            return web.json_response({"status": "ignored", "reason": "Issue not tracked by NOMARK"})

        logger.info(f"NOMARK issue detected: {nomark_info['identifier']}")

        # Extract attachments from issue description
        import re
        attachments = []
        description = data.get("description", "") or ""
        link_pattern = r'!?\[([^\]]*)\]\((https?://[^\)]+)\)'
        for match in re.finditer(link_pattern, description):
            title = match.group(1) or "attachment"
            url = match.group(2)
            if "linear" in url or "uploads" in url or any(ext in url.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip']):
                attachments.append({"title": title, "url": url})

        # Also check for attachments array in issue data
        if "attachments" in data:
            attachments.extend(data["attachments"])

        # Add attachments to trigger data
        trigger_data = {**nomark_info, "attachments": attachments}

        # Trigger task execution in background
        asyncio.create_task(trigger_nomark_task(trigger_data))

        return web.json_response({
            "status": "triggered",
            "identifier": nomark_info["identifier"],
            "project": nomark_info["project_id"],
            "story": nomark_info["story_title"],
            "attachments": len(attachments)
        })

    return web.json_response({"status": "ignored", "reason": f"Unhandled event: {event_type}/{action}"})


async def handle_health(request: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.json_response({
        "status": "healthy",
        "service": "linear-webhook",
        "mapping_file": str(LINEAR_MAPPING_FILE),
        "mapping_exists": LINEAR_MAPPING_FILE.exists()
    })


def create_app() -> web.Application:
    """Create the webhook server application."""
    app = web.Application()
    app.router.add_post("/webhook/linear", handle_webhook)
    app.router.add_get("/health", handle_health)
    return app


if __name__ == "__main__":
    logger.info(f"Starting Linear webhook server on port {WEBHOOK_PORT}")
    app = create_app()
    web.run_app(app, port=WEBHOOK_PORT)
