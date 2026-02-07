"""
Slack Bot Project Selector - Code to Add to slack-bot.py

This file contains the functions and handlers to add interactive project selection
to your Slack bot, eliminating typo and formatting issues.

Installation:
1. Copy these functions into your slack-bot.py file
2. Update the command handlers as indicated
3. Restart your Slack bot

Author: DevOps Assistant
Date: 2026-01-31
"""

import json
from typing import Optional, List, Dict, Any


# =============================================================================
# Project Selector Functions (Add after format_project_list() around line 150)
# =============================================================================

def create_project_selector_blocks(command_text: str = "", original_project: str = "") -> list:
    """
    Create Slack Block Kit blocks with a project selector menu.

    Args:
        command_text: The task description to preserve
        original_project: The invalid project name that was attempted

    Returns:
        List of Slack Block Kit blocks
    """
    projects = get_active_projects()

    if not projects:
        return [{
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "❌ No active projects configured.\n\nUse `@nomark register <github-url>` to add a project."
            }
        }]

    # Build options for select menu
    options = []
    for p in projects:
        stack = p.get("stack", "unknown")
        priority = p.get("priority", "-")

        # Create a descriptive label
        label = f"{p['name']} ({stack}) [P{priority}]"
        if len(label) > 75:  # Slack limit
            label = f"{p['name']} ({stack})"[:75]

        options.append({
            "text": {
                "type": "plain_text",
                "text": label
            },
            "value": json.dumps({
                "project_id": p["id"],
                "command": command_text
            })
        })

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"❌ Unknown project: `{original_project}`\n\n🎯 *Select the correct project:*"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "static_select",
                    "action_id": "select_project_for_task",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Choose a project..."
                    },
                    "options": options
                }
            ]
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"💡 *Tip:* Available project IDs: {', '.join([f'`{p[\"id\"]}`' for p in projects])}"
                }
            ]
        }
    ]

    return blocks


def create_project_list_with_selector(channel: str, thread_ts: str = None) -> Dict[str, Any]:
    """
    Create a message with both project list and selector dropdown.

    Args:
        channel: Slack channel ID
        thread_ts: Thread timestamp (optional)

    Returns:
        Dict with message parameters for chat_postMessage
    """
    projects = get_active_projects()

    if not projects:
        return {
            "channel": channel,
            "thread_ts": thread_ts,
            "text": "❌ No active projects configured.\n\nUse `@nomark register <github-url>` to add a project."
        }

    # Build options
    options = []
    for p in projects:
        stack = p.get("stack", "unknown")
        priority = p.get("priority", "-")
        label = f"{p['name']} ({stack}) [P{priority}]"[:75]

        options.append({
            "text": {"type": "plain_text", "text": label},
            "value": p["id"]
        })

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Available Projects:*\n\n" + "\n".join([
                    f"• `{p['id']}` - {p['name']} ({p.get('stack', 'unknown')}) [P{p.get('priority', '-')}]"
                    for p in projects
                ])
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "🎯 *Quick Select:*"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "static_select",
                    "action_id": "quick_select_project",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select a project..."
                    },
                    "options": options
                }
            ]
        }
    ]

    return {
        "channel": channel,
        "thread_ts": thread_ts,
        "text": format_project_list(),
        "blocks": blocks
    }


# =============================================================================
# Action Handlers (Add after existing @app.action handlers around line 1540)
# =============================================================================

@app.action("select_project_for_task")
async def handle_project_selection_for_task(ack, body, action):
    """
    Handle project selection from the dropdown when fixing an invalid project.
    This is triggered when a user selects a project from the error message dropdown.
    """
    await ack()

    try:
        # Parse the selected value
        value_data = json.loads(action["selected_option"]["value"])
        project_id = value_data["project_id"]
        command = value_data.get("command", "")

        # Get message context
        channel = body["channel"]["id"]
        message_ts = body["message"]["ts"]
        thread_ts = body["message"].get("thread_ts", message_ts)
        user_id = body["user"]["id"]

        # Update the original message to show selection was made
        selected_project_name = action["selected_option"]["text"]["text"]
        await app.client.chat_update(
            channel=channel,
            ts=message_ts,
            text=f"✅ Project selected: `{project_id}`",
            blocks=[{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"✅ *Project selected:* {selected_project_name}"
                }
            }]
        )

        # Check if we have a task description
        if not command:
            await app.client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=f"✅ Project `{project_id}` selected.\n\nNow, what would you like me to do?\n\nReply with: `@nomark task {project_id} <your task description>`"
            )
            return

        # Execute the task
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"🚀 Starting task on `{project_id}`...\n\n*Task:* {command}"
        )

        # Get any attachments from the original message
        files = body.get("message", {}).get("files", [])

        # Start the task
        asyncio.create_task(run_task(project_id, command, channel, thread_ts, attachments=files))

    except Exception as e:
        logger.error(f"Error handling project selection: {e}")
        await app.client.chat_postMessage(
            channel=body["channel"]["id"],
            thread_ts=body["message"].get("thread_ts", body["message"]["ts"]),
            text=f"❌ Error processing selection: {e}"
        )


@app.action("quick_select_project")
async def handle_quick_project_selection(ack, body, action):
    """
    Handle quick project selection from the projects list.
    This is triggered when viewing the project list and selecting a project.
    """
    await ack()

    try:
        project_id = action["selected_option"]["value"]
        selected_project_name = action["selected_option"]["text"]["text"]

        channel = body["channel"]["id"]
        message_ts = body["message"]["ts"]
        thread_ts = body["message"].get("thread_ts", message_ts)

        # Update message to confirm selection
        await app.client.chat_update(
            channel=channel,
            ts=message_ts,
            text=f"✅ Project selected: `{project_id}`",
            blocks=[{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"✅ *Project selected:* {selected_project_name}"
                }
            }]
        )

        # Prompt for task
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"Great! Now tell me what to do on `{project_id}`.\n\n*Example:*\n`@nomark task {project_id} add dark mode toggle to settings`"
        )

    except Exception as e:
        logger.error(f"Error handling quick project selection: {e}")


# =============================================================================
# Updated Command Handlers
# =============================================================================

"""
REPLACE the existing "task" command handler in handle_mention() (around line 2180)
with this updated version that includes project selector fallback:
"""

# In the handle_mention() function, replace the "task" section with:

if command == "task":
    # Usage: @nomark task <project> <task_description>
    if len(parts) < 2:
        await say(
            text="*Usage:* `@nomark task <project> <task_description>`\n\n*Example:* `@nomark task flowmetrics add dark mode toggle`",
            thread_ts=thread_ts
        )
        return

    # Check if we have both project and task
    if len(parts) < 3:
        # Only project provided, no task - show selector
        blocks = create_project_selector_blocks(
            command_text="",
            original_project=parts[1] if len(parts) > 1 else ""
        )
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"Please provide a task description for `{parts[1]}`:",
            blocks=blocks if parts[1] else None
        )
        return

    project = parts[1]
    task = parts[2]

    # Validate project
    projects = get_active_projects()
    project_ids = [p["id"] for p in projects]

    if project not in project_ids:
        # Project invalid - show selector with task preserved
        blocks = create_project_selector_blocks(
            command_text=task,
            original_project=project
        )
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"❌ Unknown project: `{project}`",
            blocks=blocks
        )
        return

    # Valid project - continue with task
    asyncio.create_task(run_task(project, task, channel, thread_ts, attachments=files))
    return


"""
REPLACE the existing "projects" command handler in handle_mention() (around line 2240)
with this enhanced version:
"""

if command == "projects":
    # Show project list with interactive selector
    message_params = create_project_list_with_selector(channel, thread_ts)
    await app.client.chat_postMessage(**message_params)
    return


# =============================================================================
# Alternative: Modal-based Task Creation (OPTIONAL)
# =============================================================================

"""
Add this as a new slash command for a richer task creation experience.
Register this slash command in your Slack app settings:
  Command: /nomark-new-task
  Request URL: Your bot's URL + /slack/events
  Short Description: Create a new task with project selection
"""

def create_task_creation_modal() -> dict:
    """Create a modal for task creation with project selection."""
    projects = get_active_projects()

    if not projects:
        # Return a simple modal with error
        return {
            "type": "modal",
            "callback_id": "task_modal_no_projects",
            "title": {"type": "plain_text", "text": "Create Task"},
            "close": {"type": "plain_text", "text": "Close"},
            "blocks": [{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "❌ No active projects configured.\n\nUse `@nomark register <github-url>` to add a project."
                }
            }]
        }

    options = []
    for p in projects:
        stack = p.get("stack", "unknown")
        priority = p.get("priority", "-")
        label = f"{p['name']} ({stack}) [P{priority}]"[:75]

        options.append({
            "text": {"type": "plain_text", "text": label},
            "value": p["id"]
        })

    return {
        "type": "modal",
        "callback_id": "task_creation_modal_submit",
        "title": {"type": "plain_text", "text": "Create Task"},
        "submit": {"type": "plain_text", "text": "Start Task"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🚀 Create a New Task"}
            },
            {
                "type": "input",
                "block_id": "project_block",
                "label": {"type": "plain_text", "text": "Project"},
                "element": {
                    "type": "static_select",
                    "action_id": "project_select",
                    "placeholder": {"type": "plain_text", "text": "Choose a project..."},
                    "options": options
                }
            },
            {
                "type": "input",
                "block_id": "task_block",
                "label": {"type": "plain_text", "text": "Task Description"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "task_input",
                    "multiline": True,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "e.g., Add dark mode toggle to the settings page"
                    }
                },
                "hint": {
                    "type": "plain_text",
                    "text": "Describe what you want Claude to do in detail"
                }
            },
            {
                "type": "context",
                "elements": [{
                    "type": "mrkdwn",
                    "text": "💡 Be specific about requirements, files to modify, and expected behavior"
                }]
            }
        ]
    }


@app.command("/nomark-new-task")
async def handle_new_task_modal(ack, body, client):
    """Open the task creation modal."""
    await ack()

    try:
        modal = create_task_creation_modal()
        await client.views_open(
            trigger_id=body["trigger_id"],
            view=modal
        )
    except Exception as e:
        logger.error(f"Error opening task modal: {e}")
        await client.chat_postEphemeral(
            channel=body["channel_id"],
            user=body["user_id"],
            text=f"❌ Error opening task creation modal: {e}"
        )


@app.view("task_creation_modal_submit")
async def handle_task_modal_submission(ack, body, view, client):
    """Handle task creation modal submission."""
    await ack()

    try:
        # Extract values from modal
        project_id = view["state"]["values"]["project_block"]["project_select"]["selected_option"]["value"]
        task_description = view["state"]["values"]["task_block"]["task_input"]["value"]

        # Get user info
        user_id = body["user"]["id"]

        # Post to user's DM or a configured channel
        # For DM, use user_id as channel
        channel_id = user_id

        # Send task start message
        msg = await client.chat_postMessage(
            channel=channel_id,
            text=f"🚀 *Starting task on `{project_id}`*\n\n*Task:* {task_description}\n\n`[○○○○○○]` Initializing..."
        )

        thread_ts = msg["ts"]

        # Start the task
        asyncio.create_task(run_task(project_id, task_description, channel_id, thread_ts))

    except Exception as e:
        logger.error(f"Error handling task modal submission: {e}")
        # Send error message to user
        await client.chat_postEphemeral(
            channel=body["user"]["id"],
            user=body["user"]["id"],
            text=f"❌ Error starting task: {e}"
        )


# =============================================================================
# Installation Checklist
# =============================================================================

"""
To install this project selector functionality:

1. Copy the following functions into slack-bot.py:
   - create_project_selector_blocks() → After format_project_list() (line ~150)
   - create_project_list_with_selector() → After create_project_selector_blocks()

2. Copy the action handlers:
   - @app.action("select_project_for_task") → After existing action handlers (line ~1540)
   - @app.action("quick_select_project") → After select_project_for_task handler

3. Update command handlers in handle_mention():
   - Replace the "task" command section (line ~2180)
   - Replace the "projects" command section (line ~2240)

4. OPTIONAL: Add modal-based task creation:
   - Copy create_task_creation_modal() function
   - Copy @app.command("/nomark-new-task") handler
   - Copy @app.view("task_creation_modal_submit") handler
   - Register /nomark-new-task as a slash command in Slack app settings

5. Ensure ~/config/projects.json exists with valid projects:
   mkdir -p ~/config
   # Add your projects to ~/config/projects.json

6. Restart the Slack bot:
   pkill -f slack-bot.py
   python3 ~/scripts/slack-bot.py &

7. Test the changes:
   @DevOps task wrongproject do something
   # Should show project selector dropdown

   @DevOps projects
   # Should show list with quick selector

   /nomark-new-task
   # Should open modal (if implemented)

Done! Your bot now has interactive project selection.
"""
