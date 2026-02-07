# Slack Bot Interactive Project Selection - Implementation Guide

## Problem Analysis

### Current Issue
Your Slack bot shows `❌ Unknown project: 'inhhale-v2'` because:

1. **No projects.json exists**: The file at `~/config/projects.json` is empty or missing
2. **Project not registered**: "inhhale-v2" hasn't been added to the system
3. **Text parsing is fragile**: Users must type exact project IDs (case-sensitive, no typos allowed)

### Error in Your Screenshot
```
User: @DevOps task inhhale-v2 complete this audit
Bot: ❌ Unknown project: `inhhale-v2`

Available Projects:
• flowmetrics - FlowMetrics (sveltekit-postgres) [P1]
• instaindex - InstaIndex (nextjs-supabase) [P2]
• inhhale-v2 - inhhale-v2 (unknown) [P4]
```

The project IS listed but with the exact ID `inhhale-v2` (with lowercase 'i'). The bot's text parser is case-sensitive.

---

## Solution 1: Register the Project Properly

First, ensure "inhhale-v2" is properly registered in `~/config/projects.json`:

```bash
# Create config directory if it doesn't exist
mkdir -p ~/config

# Create or update projects.json
cat > ~/config/projects.json << 'EOF'
{
  "projects": [
    {
      "id": "flowmetrics",
      "name": "FlowMetrics",
      "repo": "NOMARK/flowmetrics-portal",
      "stack": "sveltekit-postgres",
      "priority": 1,
      "active": true
    },
    {
      "id": "instaindex",
      "name": "InstaIndex",
      "repo": "NOMARK/instaindex",
      "stack": "nextjs-supabase",
      "priority": 2,
      "active": true
    },
    {
      "id": "inhhale-v2",
      "name": "Inhhale iOS App",
      "repo": "NOMARK/inhhale-v2",
      "stack": "swift-ios",
      "description": "Medical breathing therapy iOS app for VCD/ILO patients",
      "priority": 4,
      "active": true
    }
  ],
  "defaults": {
    "model": "claude-opus-4-5-20251101",
    "maxConcurrentTasks": 1,
    "autoShutdown": true
  }
}
EOF
```

**Test command:**
```bash
@DevOps task inhhale-v2 complete the iOS audit
```

---

## Solution 2: Add Interactive Project Selection (RECOMMENDED)

### Implementation Overview

Add Slack Block Kit select menus to eliminate typo issues. Two approaches:

#### Approach A: Inline Select Menu (Quick)
Show a select menu when project is missing/invalid:

```python
# Add this function to slack-bot.py after format_project_list()

def create_project_selector_blocks(command_text: str = "") -> list:
    """Create blocks with a project selector menu."""
    projects = get_active_projects()

    if not projects:
        return [{
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "❌ No active projects configured. Use `@nomark register <github-url>` to add one."
            }
        }]

    # Build options for select menu
    options = []
    for p in projects:
        stack = p.get("stack", "unknown")
        options.append({
            "text": {
                "type": "plain_text",
                "text": f"{p['name']} ({stack})"
            },
            "value": json.dumps({
                "project_id": p["id"],
                "command": command_text
            })
        })

    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "🎯 *Select a project to continue:*"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "static_select",
                    "action_id": "select_project",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Choose a project..."
                    },
                    "options": options
                }
            ]
        }
    ]


# Add action handler for project selection
@app.action("select_project")
async def handle_project_selection(ack, body, action):
    """Handle project selection from dropdown."""
    await ack()

    # Parse the selected value
    value_data = json.loads(action["selected_option"]["value"])
    project_id = value_data["project_id"]
    command = value_data.get("command", "")

    # Get message context
    channel = body["channel"]["id"]
    thread_ts = body["message"]["ts"]

    # Ask for task description if not provided
    if not command:
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"✅ Project `{project_id}` selected.\n\nNow, what would you like me to do? Reply with your task description."
        )
        # Store project context for follow-up
        active_tasks[thread_ts] = {"project": project_id}
        return

    # Execute the task
    await app.client.chat_postMessage(
        channel=channel,
        thread_ts=thread_ts,
        text=f"🚀 Starting task on `{project_id}`..."
    )

    asyncio.create_task(run_task(project_id, command, channel, thread_ts))
```

#### Approach B: Modal Dialog (Better UX)
Show a full modal with project selection and task input:

```python
# Add to slack-bot.py

def create_task_modal(trigger_id: str):
    """Create a modal for task creation with project selection."""
    projects = get_active_projects()

    options = []
    for p in projects:
        stack = p.get("stack", "unknown")
        options.append({
            "text": {
                "type": "plain_text",
                "text": f"{p['name']} ({stack})"
            },
            "value": p["id"]
        })

    modal_view = {
        "type": "modal",
        "callback_id": "task_modal_submit",
        "title": {
            "type": "plain_text",
            "text": "Create Task"
        },
        "submit": {
            "type": "plain_text",
            "text": "Start Task"
        },
        "close": {
            "type": "plain_text",
            "text": "Cancel"
        },
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🎯 *Select a project and describe your task*"
                }
            },
            {
                "type": "input",
                "block_id": "project_block",
                "label": {
                    "type": "plain_text",
                    "text": "Project"
                },
                "element": {
                    "type": "static_select",
                    "action_id": "project_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Choose a project..."
                    },
                    "options": options
                }
            },
            {
                "type": "input",
                "block_id": "task_block",
                "label": {
                    "type": "plain_text",
                    "text": "Task Description"
                },
                "element": {
                    "type": "plain_text_input",
                    "action_id": "task_input",
                    "multiline": True,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "e.g., Add dark mode toggle to settings page"
                    }
                }
            }
        ]
    }

    return modal_view


# Add slash command to trigger modal
@app.command("/nomark-task-new")
async def handle_task_modal_command(ack, body, client):
    """Open task creation modal."""
    await ack()

    try:
        modal = create_task_modal(body["trigger_id"])
        await client.views_open(
            trigger_id=body["trigger_id"],
            view=modal
        )
    except Exception as e:
        logger.error(f"Error opening modal: {e}")
        await client.chat_postEphemeral(
            channel=body["channel_id"],
            user=body["user_id"],
            text=f"❌ Error opening task modal: {e}"
        )


# Handle modal submission
@app.view("task_modal_submit")
async def handle_task_modal_submission(ack, body, view, client):
    """Handle task modal submission."""
    await ack()

    # Extract values
    project_id = view["state"]["values"]["project_block"]["project_select"]["selected_option"]["value"]
    task_description = view["state"]["values"]["task_block"]["task_input"]["value"]

    # Get user and channel info
    user_id = body["user"]["id"]
    # Post to the channel where the command was invoked
    channel_id = body["user"]["id"]  # Send as DM or use a configured channel

    # Send confirmation
    msg = await client.chat_postMessage(
        channel=channel_id,
        text=f"🚀 *Starting task on `{project_id}`*\n\n*Task:* {task_description}"
    )

    thread_ts = msg["ts"]

    # Start the task
    asyncio.create_task(run_task(project_id, task_description, channel_id, thread_ts))
```

#### Approach C: Update Existing Commands
Modify the `task` command handler to show project selector when project is invalid:

```python
# In handle_mention() function, modify the "task" command handler:

if command == "task":
    if len(parts) < 3:
        # Show project selector
        blocks = create_project_selector_blocks(parts[1] if len(parts) > 1 else "")
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text="Please select a project:",
            blocks=blocks
        )
        return

    project = parts[1]
    task = parts[2]

    # Validate project
    projects = get_active_projects()
    project_ids = [p["id"] for p in projects]

    if project not in project_ids:
        # Project invalid - show selector
        blocks = create_project_selector_blocks(task)
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"❌ Unknown project: `{project}`\n\nPlease select a project:",
            blocks=blocks
        )
        return

    # Valid project - continue
    asyncio.create_task(run_task(project, task, channel, thread_ts, attachments=files))
    return
```

---

## Implementation Steps

### Step 1: Update slack-bot.py

Add the functions from **Approach A** and **Approach C** to [slack-bot.py](nomark-method/scripts/slack-bot.py):

1. Add `create_project_selector_blocks()` after line 149
2. Add `@app.action("select_project")` handler after line 1540
3. Update the `task` command handler in `handle_mention()` (around line 2180)

### Step 2: Ensure projects.json exists

```bash
# On your VM/server where the bot runs:
mkdir -p ~/config
# Add your projects as shown in Solution 1
```

### Step 3: Restart the Slack bot

```bash
# Stop the bot
pkill -f slack-bot.py

# Start it again (or use your systemd service)
python3 ~/scripts/slack-bot.py &
```

### Step 4: Test the workflow

```
# In Slack:
@DevOps task complete the iOS audit
# Bot will show project selector since no project specified

# Or:
@DevOps task wrongname complete the audit
# Bot will show project selector since "wrongname" is invalid
```

---

## Recommended Approach

**Use Approach C (Update Existing Commands)** because:

1. ✅ Minimal code changes
2. ✅ Backwards compatible with existing commands
3. ✅ Provides dropdown fallback when project is invalid
4. ✅ Preserves task description in selector context
5. ✅ No new slash commands required

**Bonus: Add Modal for Complex Tasks**
Implement Approach B as `/nomark-task-new` for a richer creation experience.

---

## Testing Checklist

- [ ] Bot recognizes valid project IDs from text commands
- [ ] Bot shows selector dropdown for invalid project names
- [ ] Selector dropdown lists all active projects
- [ ] Selecting a project from dropdown triggers task execution
- [ ] Task description is preserved from original command
- [ ] Follow-up messages work in task threads
- [ ] Project registration adds new projects to selector

---

## Future Enhancements

1. **Autocomplete**: Use Slack's external data source for project autocomplete
2. **Fuzzy Matching**: Suggest closest match when typo detected (e.g., "Did you mean `inhhale-v2`?")
3. **Recent Projects**: Show recently used projects at the top
4. **Project Shortcuts**: Allow users to set default projects with `/nomark set-default flowmetrics`

---

## Additional Files to Create

### 1. Test projects.json
Save this to `~/config/projects.json` on your server:

```json
{
  "projects": [
    {
      "id": "flowmetrics",
      "name": "FlowMetrics",
      "repo": "NOMARK/flowmetrics-portal",
      "stack": "sveltekit-postgres",
      "priority": 1,
      "active": true
    },
    {
      "id": "instaindex",
      "name": "InstaIndex",
      "repo": "NOMARK/instaindex",
      "stack": "nextjs-supabase",
      "priority": 2,
      "active": true
    },
    {
      "id": "inhhale-v2",
      "name": "Inhhale iOS App",
      "repo": "NOMARK/inhhale-v2",
      "stack": "swift-ios",
      "description": "Medical breathing therapy iOS app for VCD/ILO patients",
      "priority": 4,
      "active": true
    }
  ],
  "defaults": {
    "model": "claude-opus-4-5-20251101",
    "maxConcurrentTasks": 1,
    "autoShutdown": true
  }
}
```

### 2. Quick Fix Script
Create this script to quickly fix project names:

```bash
#!/bin/bash
# ~/scripts/fix-project-name.sh

PROJECT_FILE=~/config/projects.json

if [[ ! -f "$PROJECT_FILE" ]]; then
    echo "Error: $PROJECT_FILE not found"
    exit 1
fi

# Show current projects
echo "Current projects:"
jq -r '.projects[] | "\(.id) - \(.name) (\(.stack))"' "$PROJECT_FILE"

echo ""
read -p "Enter project ID to fix (or 'new' to add): " PROJECT_ID

if [[ "$PROJECT_ID" == "new" ]]; then
    read -p "New project ID: " NEW_ID
    read -p "Project name: " NEW_NAME
    read -p "Repo (org/name): " NEW_REPO
    read -p "Stack: " NEW_STACK
    read -p "Priority: " NEW_PRIORITY

    jq --arg id "$NEW_ID" \
       --arg name "$NEW_NAME" \
       --arg repo "$NEW_REPO" \
       --arg stack "$NEW_STACK" \
       --argjson priority "$NEW_PRIORITY" \
       '.projects += [{
           "id": $id,
           "name": $name,
           "repo": $repo,
           "stack": $stack,
           "priority": $priority,
           "active": true
       }]' "$PROJECT_FILE" > "$PROJECT_FILE.tmp"

    mv "$PROJECT_FILE.tmp" "$PROJECT_FILE"
    echo "✅ Added project: $NEW_ID"
else
    # Update existing project
    read -p "New name (leave blank to skip): " NEW_NAME
    read -p "New stack (leave blank to skip): " NEW_STACK

    if [[ -n "$NEW_NAME" ]]; then
        jq --arg id "$PROJECT_ID" --arg name "$NEW_NAME" \
           '(.projects[] | select(.id == $id) | .name) = $name' \
           "$PROJECT_FILE" > "$PROJECT_FILE.tmp"
        mv "$PROJECT_FILE.tmp" "$PROJECT_FILE"
    fi

    if [[ -n "$NEW_STACK" ]]; then
        jq --arg id "$PROJECT_ID" --arg stack "$NEW_STACK" \
           '(.projects[] | select(.id == $id) | .stack) = $stack' \
           "$PROJECT_FILE" > "$PROJECT_FILE.tmp"
        mv "$PROJECT_FILE.tmp" "$PROJECT_FILE"
    fi

    echo "✅ Updated project: $PROJECT_ID"
fi

echo ""
echo "Updated projects:"
jq -r '.projects[] | "\(.id) - \(.name) (\(.stack))"' "$PROJECT_FILE"
```

Make executable:
```bash
chmod +x ~/scripts/fix-project-name.sh
```

---

## Summary

### Immediate Fix (5 minutes)
1. Create `~/config/projects.json` with correct project IDs
2. Ensure "inhhale-v2" is listed with exact lowercase spelling
3. Restart Slack bot

### Long-term Fix (30 minutes)
1. Implement Approach C (project selector on invalid input)
2. Add `create_project_selector_blocks()` function
3. Add `@app.action("select_project")` handler
4. Update `task` command to show selector on error
5. Test and deploy

This eliminates all typo and formatting issues permanently!
