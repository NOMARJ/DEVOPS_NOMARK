# NOMARK DevOps User Guide

A complete guide to using NOMARK DevOps - your autonomous AI development assistant via Slack or Claude.ai.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Concepts](#core-concepts)
3. [Project Registration](#project-registration)
4. [Slack Commands Reference](#slack-commands-reference)
5. [Workflows](#workflows)
6. [Claude.ai Integration](#claudeai-integration)
7. [Claude.ai MCP Connector](#claudeai-mcp-connector)
8. [Live Preview](#live-preview)
9. [File & Image Attachments](#file--image-attachments)
10. [Interactive Buttons](#interactive-buttons)
11. [Best Practices](#best-practices)
12. [Troubleshooting](#troubleshooting)
13. [Linear Integration](#linear-integration)
14. [Claude Code Authentication](#claude-code-authentication)
15. [MCP Servers](#mcp-servers)

---

## Quick Start

### Your First Task

1. Open your Slack workspace
2. Go to the NOMARK DevOps channel
3. Type:
   ```
   @nomark task flowmetrics add a loading spinner to the dashboard
   ```
4. Wait for completion - you'll get a PR link when done

### What Happens Behind the Scenes

```
You send task → Bot acknowledges → Claude Code runs on VM →
Code is written → Tests run → Commits made → PR created →
You get results with PR link
```

---

## Core Concepts

### The NOMARK Method

NOMARK is an autonomous development methodology that combines:

- **Ralph** - PRD-driven autonomous loops
- **Boris Cherny's Workflow** - Claude Code creator's approach

#### The Flow

```
/think → /plan → /build → /verify → /simplify → /commit → /pr
```

| Phase | What Happens |
|-------|--------------|
| `/think` | Analyze the problem, understand constraints |
| `/plan` | Break into atomic user stories |
| `/build` | Implement one story at a time |
| `/verify` | Run tests, typecheck, visual verification |
| `/simplify` | Clean up code, remove unused parts |
| `/commit` | Create descriptive commits |
| `/pr` | Push and create pull request |

### Projects

Projects are codebases registered with NOMARK. Each project has:

- A local clone on the VM (`~/repos/<project-id>`)
- Configuration in `projects.json`
- Optional `.claude/` folder with skills and patterns

View available projects:
```
@nomark projects
```

### Branches

NOMARK creates feature branches automatically:
```
ralph/<task-description-slug>
```

Example: Task "add dark mode toggle" creates branch `ralph/add-dark-mode-toggle`

---

## Project Registration

### Overview

Before NOMARK can work on a project, it needs to be registered. Registration clones the repository to the VM, detects the tech stack, installs dependencies, and sets up the NOMARK method files.

### Registering a New Project

Simply paste a GitHub URL in Slack:

```
@nomark register https://github.com/NOMARJ/inhale-v2
```

Or specify a custom project ID:

```
@nomark register https://github.com/owner/repo-name my-project
```

### What Happens During Registration

```
GitHub URL → Clone repo → Detect stack → Install deps →
Setup NOMARK → Update config → Ready to work!
```

**Step by step:**

1. **Clone Repository**
   - Clones to `~/repos/<project-id>` on the VM
   - Project ID is derived from repo name (lowercase, hyphens)

2. **Detect Tech Stack**
   - Scans `package.json`, `requirements.txt`, `Cargo.toml`, etc.
   - Identifies framework (Next.js, React, Django, Flask, etc.)
   - Detects TypeScript, database tools (Prisma, Supabase)

3. **Install Dependencies**
   - Runs `npm install` for Node.js projects
   - Runs `pip install -r requirements.txt` for Python
   - Appropriate package manager for other stacks

4. **Setup NOMARK Method**
   - Copies `.claude/` folder with skills and patterns
   - Creates `CLAUDE.md` project configuration if missing
   - Sets up progress tracking files

5. **Update Configuration**
   - Adds project to `~/config/projects.json`
   - Sets priority and active status

6. **Confirmation**
   - Returns project details
   - Shows quick-start buttons
   - Ready for tasks immediately

### Supported Tech Stacks

| Stack | Detection |
|-------|-----------|
| **Next.js** | `"next"` in package.json |
| **Vite** | `"vite"` in package.json |
| **React** | `"react"` in package.json |
| **Vue** | `"vue"` in package.json |
| **Node.js** | package.json present |
| **Django** | `manage.py` present |
| **Flask** | `flask` in requirements.txt |
| **FastAPI** | `fastapi` in requirements.txt |
| **Python** | requirements.txt or pyproject.toml |
| **Rust** | Cargo.toml present |
| **Go** | go.mod present |
| **Java** | pom.xml or build.gradle |

TypeScript and database tools (Prisma, Supabase) are also detected and noted.

### GitHub URL Formats

All these formats work:

```
https://github.com/owner/repo
https://github.com/owner/repo.git
git@github.com:owner/repo.git
```

### After Registration

Once registered, you can immediately start working:

```
# List your projects
@nomark projects

# Run a task
@nomark task inhale-v2 add user authentication

# Start a preview
@nomark preview inhale-v2

# View project config
@nomark show inhale-v2 CLAUDE.md
```

### Registration Buttons

After successful registration, you'll see buttons:

| Button | Action |
|--------|--------|
| 📋 View on GitHub | Opens the repository |
| 👁️ Start Preview | Starts dev server with Cloudflare Tunnel |

### Customizing After Registration

**Edit CLAUDE.md** to add project-specific instructions:

```
@nomark show my-project CLAUDE.md
```

Then SSH to the VM to edit:

```bash
nomark-ssh
nano ~/repos/my-project/CLAUDE.md
```

Add:
- Coding conventions
- File structure notes
- Common commands
- Important patterns

### Requirements

For registration to work:

1. **GitHub Access**: The VM must have access to the repository
   - Public repos work automatically
   - Private repos need `GITHUB_TOKEN` configured

2. **GitHub CLI**: `gh` must be authenticated on the VM

3. **Disk Space**: Enough space in `~/repos/` for the clone

### Troubleshooting Registration

**"Failed to clone repository"**
- Check the URL is correct
- Verify the repo exists and is accessible
- For private repos, ensure `GITHUB_TOKEN` is set

**"Project already exists"**
- A project with that ID is already registered
- Use a custom ID: `@nomark register <url> different-id`
- Or remove the existing project first

**Dependencies failed to install**
- Registration continues even if deps fail
- SSH and install manually if needed:
  ```bash
  nomark-ssh
  cd ~/repos/<project>
  npm install
  ```

---

## Slack Commands Reference

### Task Execution

#### `@nomark task <project> <description>`
Run a single development task.

```
@nomark task flowmetrics add priority filter to task list
@nomark task flowmetrics fix the login redirect bug
@nomark task flowmetrics refactor dashboard to use React Query
```

**What it does:**
1. Creates a feature branch
2. Runs Claude Code with NOMARK method
3. Implements the change
4. Runs tests and typecheck
5. Commits and creates PR
6. Returns summary with PR link

#### `@nomark prd <content>`
Execute a full PRD (Product Requirements Document) in Ralph autonomous mode.

```
@nomark prd
## Feature: Dark Mode

### Stories
1. Add theme context provider
2. Create toggle component
3. Apply theme to all components
4. Persist to localStorage
```

**What it does:**
1. Parses your PRD into discrete stories
2. Shows preview with confirmation buttons
3. Creates `prd.json` in project
4. Runs Ralph autonomous loop
5. Implements ALL stories sequentially
6. Commits after each story
7. Creates single PR with all changes

### Project Registration

#### `@nomark register <github-url> [project-id]`
Register a new GitHub repository with NOMARK.

```
@nomark register https://github.com/NOMARJ/inhale-v2
@nomark register https://github.com/owner/repo my-custom-id
```

See [Project Registration](#project-registration) for full details on the registration process, supported stacks, and troubleshooting.

### Status & Monitoring

#### `@nomark status`
Check VM status and recent activity.

```
@nomark status
```

Returns:
- VM running/idle status
- Preview server URL (if running)
- Recent task log entries

#### `@nomark logs [n]`
Show recent log entries (default: 10).

```
@nomark logs        # Last 10 entries
@nomark logs 20     # Last 20 entries
```

#### `@nomark projects`
List all available projects.

```
@nomark projects
```

#### `@nomark threads` / `@nomark active`
List active task threads you can continue.

```
@nomark threads
```

### Preview Server

#### `@nomark preview <project>`
Start a live dev server with public URL via Cloudflare Tunnel.

```
@nomark preview flowmetrics
```

Returns a public URL like `https://random-words.trycloudflare.com` where you can see the running dev server.

#### `@nomark preview stop`
Stop the preview server.

```
@nomark preview stop
```

### File Operations

#### `@nomark show <project> <filepath>`
View contents of a file from a project.

```
@nomark show flowmetrics src/app/page.tsx
@nomark show flowmetrics package.json
@nomark show flowmetrics CLAUDE.md
```

### Control Commands

#### `@nomark stop` / `@nomark cancel`
Stop the currently running task.

```
@nomark stop
```

#### `@nomark done` / `@nomark merge`
Mark a task thread as complete (removes from active threads).

```
@nomark done
```

### Slash Commands

For quick access without @mentioning:

| Command | Description |
|---------|-------------|
| `/nomark-task <project> <desc>` | Quick task execution |
| `/nomark-status` | Quick status check |
| `/nomark-preview <project>` | Quick preview start |

---

## Workflows

### Workflow 1: Single Task

Best for: Bug fixes, small features, quick changes

```
@nomark task flowmetrics fix the date formatting in transaction history
```

Wait for completion, review PR, merge.

### Workflow 2: Follow-up Tasks

Best for: Iterative development, multi-part features

```
# Start initial task
@nomark task flowmetrics add user avatar upload

# After completion, send follow-up in same thread
@nomark add avatar cropping functionality

# Continue iterating
@nomark add avatar preview before save
```

Follow-ups continue on the same branch, building on previous work.

### Workflow 3: PRD Execution (Ralph Mode)

Best for: Larger features, well-defined specs, autonomous execution

1. Design your feature in Claude.ai
2. Create a PRD with clear stories
3. Send to Slack:

```
@nomark prd
## Feature: User Notifications

### Overview
Add real-time notification system for users.

### Stories
1. Create notification data model and API endpoint
2. Add NotificationBell component to header
3. Implement notification dropdown with mark-as-read
4. Add WebSocket connection for real-time updates
5. Create notification preferences in settings

### Constraints
- Use existing WebSocket infrastructure
- Max 50 notifications stored per user
- Support browser notifications if permitted
```

4. Review parsed tasks, click "Execute All Tasks"
5. Claude implements each story, commits after each
6. Review single PR with all changes

### Workflow 4: Design in Claude.ai, Execute in Slack

Best for: Complex features needing design discussion

1. **In Claude.ai:** Have a conversation about architecture, approach, edge cases
2. **Export:** Copy the final PRD/artifact
3. **In Slack:** `@nomark prd <paste content>`
4. **Execute:** Click "Execute All Tasks"
5. **Review:** Check the PR, provide feedback
6. **Iterate:** Send follow-ups in the same thread

### Workflow 5: Bug Fix with Screenshot

Best for: UI bugs, visual issues

1. Take a screenshot of the bug
2. Upload to Slack with description:

```
@nomark task flowmetrics [attach screenshot] fix this button alignment issue
```

Claude analyzes the screenshot and fixes the issue.

### Workflow 6: Onboarding a New Project

Best for: Adding a new repository to NOMARK

**Step 1: Register the project**
```
@nomark register https://github.com/NOMARJ/inhale-v2
```

Wait for confirmation showing project details.

**Step 2: Verify setup**
```
@nomark projects
```

Your new project should appear in the list.

**Step 3: Review the config**
```
@nomark show inhale-v2 CLAUDE.md
```

**Step 4: Start the preview (optional)**
```
@nomark preview inhale-v2
```

**Step 5: Run your first task**
```
@nomark task inhale-v2 add a health check endpoint at /api/health
```

**Step 6: Iterate**
Continue sending tasks in the same thread for follow-ups:
```
@nomark add logging to the health check endpoint
```

### Workflow 7: Multi-Project Development

Best for: Working across multiple repositories

```
# Register all your projects
@nomark register https://github.com/org/frontend
@nomark register https://github.com/org/backend
@nomark register https://github.com/org/shared-lib

# Check available projects
@nomark projects

# Work on frontend
@nomark task frontend add loading spinner to dashboard

# In a new thread, work on backend
@nomark task backend add pagination to /api/users endpoint

# Preview different projects
@nomark preview frontend
# ... later ...
@nomark preview stop
@nomark preview backend
```

Each project maintains its own:
- Feature branches
- Active task threads
- NOMARK configuration

---

## Claude.ai Integration

### The Bridge

NOMARK connects your Claude.ai design sessions to actual code execution:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Claude.ai     │     │     Slack       │     │    VM/Code      │
│                 │     │                 │     │                 │
│  Design PRD     │ ──> │  @nomark prd    │ ──> │  Ralph Loop     │
│  Discuss arch   │     │  Parse & show   │     │  Implement all  │
│  Refine spec    │     │  Execute button │     │  Create PR      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### PRD Format

NOMARK understands various PRD formats. Here are some examples:

#### Simple Format
```
## Feature: <Title>

<Description>

### Tasks
1. Task one
2. Task two
3. Task three
```

#### Detailed Format
```
## Feature: <Title>

### Overview
<Detailed description>

### User Stories
1. As a user, I want to...
2. As an admin, I want to...

### Technical Requirements
- Must use existing auth system
- Should support mobile

### Acceptance Criteria
- [ ] Users can do X
- [ ] System shows Y
```

#### Ralph Format
```
{
  "title": "Feature Name",
  "summary": "One line summary",
  "tasks": [
    {"id": 1, "description": "First task", "priority": "high"},
    {"id": 2, "description": "Second task", "priority": "medium"}
  ],
  "constraints": ["Use TypeScript", "Add tests"]
}
```

### Tips for Good PRDs

1. **Be Specific**: "Add loading spinner to dashboard" not "improve UX"
2. **Order by Dependency**: Put foundational tasks first
3. **Include Constraints**: Tech requirements, patterns to follow
4. **Keep Stories Atomic**: Each should be completable independently

---

## Claude.ai MCP Connector

The DevOps MCP is available as an SSE server that connects directly to Claude.ai, providing an **alternative interface to Slack** with the same capabilities.

### Setup

1. Go to **Claude.ai Settings → Connectors**
2. Click **"Add custom connector"**
3. Enter:
   - **Name:** `DevOps MCP`
   - **Remote MCP server URL:** `https://20-5-185-136.sslip.io/sse`
4. Click **Add**

This is a static URL that uses the Azure VM's public IP with automatic HTTPS.

### Using MCP Tools in Claude.ai

Once connected, you can use all 76 DevOps tools directly in Claude.ai conversations. The tools mirror Slack functionality:

#### Task Execution

**Slack:**
```
@nomark task flowmetrics add dark mode toggle
```

**Claude.ai MCP:**
```
Use the slack_run_task tool:
- project: flowmetrics
- task_description: add dark mode toggle
```

Or simply ask Claude:
> "Run a task on flowmetrics to add a dark mode toggle"

#### PRD Execution

**Slack:**
```
@nomark prd
## Feature: Dark Mode
### Stories
1. Add theme context
2. Create toggle component
```

**Claude.ai MCP:**
```
Use the slack_execute_prd tool:
- project: flowmetrics
- prd_content: <your PRD markdown>
```

Or ask Claude:
> "Execute this PRD on flowmetrics: [paste your PRD]"

#### Linear Integration

**Slack:**
```
@nomark linear issues
@nomark linear create "Bug: Login broken"
```

**Claude.ai MCP:**
```
Use the linear_list_issues tool:
- project_id: <your-project-id>
- state: in_progress

Use the linear_create_issue tool:
- title: Bug: Login broken
- description: <details>
- labels: ["Bug"]
```

Or ask Claude:
> "Show me all in-progress Linear issues"
> "Create a Linear bug for: Login page returns 500 error"

#### GitHub Operations

**Slack:**
```
@nomark show flowmetrics src/app/page.tsx
```

**Claude.ai MCP:**
```
Use the github_get_file_contents tool:
- repo: flowmetrics
- path: src/app/page.tsx
```

Or ask Claude:
> "Show me the contents of src/app/page.tsx in flowmetrics"

#### VM Operations

**Slack:**
```
@nomark status
@nomark preview flowmetrics
```

**Claude.ai MCP:**
```
Use the azure_vm_status tool:
- resource_group: nomark-rg
- vm_name: nomark-devops-vm

Use the slack_start_preview tool:
- project: flowmetrics
```

Or ask Claude:
> "What's the status of the DevOps VM?"
> "Start a preview for flowmetrics"

### Available MCP Tools by Category

| Category | Tools | Description |
|----------|-------|-------------|
| **Slack/Tasks** | `slack_run_task`, `slack_execute_prd`, `slack_start_preview`, `slack_stop_preview` | Task execution, PRD, previews |
| **Linear** | `linear_list_issues`, `linear_create_issue`, `linear_update_issue`, `linear_add_comment`, `linear_search` | Issue management |
| **GitHub** | `github_list_repos`, `github_get_file_contents`, `github_create_pr`, `github_list_prs`, `github_merge_pr` | Repository operations |
| **Azure** | `azure_vm_start`, `azure_vm_stop`, `azure_vm_status`, `azure_vm_run_command` | VM management |
| **Supabase** | `supabase_query`, `supabase_insert`, `supabase_update`, `supabase_list_tables` | Database operations |
| **Vercel** | `vercel_list_deployments`, `vercel_get_deployment`, `vercel_redeploy` | Deployment management |
| **n8n** | `n8n_list_workflows`, `n8n_execute_workflow`, `n8n_activate_workflow` | Workflow automation |
| **Skills** | `skills_list`, `skills_get`, `skills_execute` | NOMARK skills library |

### Command Equivalents

| Slack Command | Claude.ai MCP Equivalent |
|---------------|--------------------------|
| `@nomark task <project> <desc>` | "Run a task on [project] to [desc]" |
| `@nomark prd <content>` | "Execute this PRD on [project]: [content]" |
| `@nomark preview <project>` | "Start a preview for [project]" |
| `@nomark preview stop` | "Stop the preview" |
| `@nomark status` | "What's the VM status?" |
| `@nomark projects` | "List all registered projects" |
| `@nomark show <project> <file>` | "Show me [file] from [project]" |
| `@nomark linear issues` | "Show my Linear issues" |
| `@nomark linear create <title>` | "Create a Linear issue: [title]" |

### Benefits of MCP vs Slack

| Feature | Slack | Claude.ai MCP |
|---------|-------|---------------|
| Conversational UI | Limited | Full natural language |
| Multi-step workflows | Manual | Claude orchestrates |
| Context awareness | Per-message | Full conversation |
| Tool chaining | Manual | Automatic |
| File attachments | Supported | Drag & drop |
| Real-time updates | Thread replies | Streaming |

### Example Workflows

#### Natural Language Task

Instead of remembering exact Slack commands:
```
"I need to add user authentication to the inhale-v2 project.
Start with Supabase auth, add a login page, and create
protected routes. Run this as a PRD."
```

Claude will:
1. Format your request as a proper PRD
2. Execute it on the project using `slack_execute_prd`
3. Report progress as stories complete

#### Cross-Tool Orchestration

```
"Check if there are any bugs in Linear for flowmetrics,
then fix the highest priority one and create a PR"
```

Claude will:
1. Use `linear_search` to find bugs
2. Identify highest priority
3. Use `slack_run_task` to implement the fix
4. Report the PR link

### Sync Between Interfaces

Both Slack and Claude.ai MCP use the same backend:
- Changes made via Claude.ai appear in Slack threads
- Linear issues sync regardless of interface
- Git operations affect the same repositories
- Preview servers are shared

---

## Live Preview

### Starting a Preview

```
@nomark preview flowmetrics
```

This:
1. Starts `npm run dev` (or equivalent) on the VM
2. Creates a Cloudflare Tunnel
3. Returns a public URL

### Viewing Changes

After Claude makes changes:
1. Changes are on the feature branch
2. Preview server shows those changes
3. Refresh the preview URL to see updates

### Workflow with Preview

```
# Start preview
@nomark preview flowmetrics

# Start task
@nomark task flowmetrics add dark mode toggle

# While task runs, preview URL updates automatically
# After completion, verify changes in preview

# Stop preview when done
@nomark preview stop
```

### Preview + PRD

For larger features:
```
# Start preview first
@nomark preview flowmetrics

# Execute PRD
@nomark prd <your PRD>

# Watch changes appear in preview as each story completes
```

---

## File & Image Attachments

### Screenshot Analysis

Upload a screenshot and Claude will analyze it:

```
@nomark [attach screenshot.png]
```

Response includes:
- Description of what's shown
- Identified issues (if any)
- Suggested fixes

### Screenshot + Task

Combine screenshot with task for context:

```
@nomark task flowmetrics [attach bug.png] fix this layout issue
```

Claude sees the screenshot while implementing the fix.

### Code File Attachments

Upload code files for context:

```
@nomark [attach error.log] investigate this error
@nomark task flowmetrics [attach design.json] implement this design spec
```

### Supported File Types

**Images (analyzed with Claude Vision):**
- PNG, JPG, JPEG, GIF, WebP

**Code/Text (content displayed):**
- TXT, LOG, JSON, JS, TS, TSX, PY, MD, YAML, YML, SH, CSS, HTML

---

## Interactive Buttons

### Task Completion Buttons

When a task completes, you get buttons:

| Button | Action |
|--------|--------|
| 👀 View PR | Opens PR in GitHub |
| ✅ Approve PR | Approves the PR via GitHub CLI |
| 🧪 Run Tests | Runs `npm test` and shows results |
| 👁️ Preview | Starts preview server for this project |

### PRD Execution Buttons

After parsing a PRD:

| Button | Action |
|--------|--------|
| ▶️ Execute All Tasks | Run Ralph loop for all stories |
| 📝 Execute First Task Only | Run just the first story |
| ❌ Cancel | Cancel without executing |

### Preview Buttons

When preview is running:

| Button | Action |
|--------|--------|
| Open Preview | Opens preview URL in browser |
| 🛑 Stop Preview | Stops the preview server |

### Project Registration Buttons

After registering a project:

| Button | Action |
|--------|--------|
| 📋 View on GitHub | Opens the repository in GitHub |
| 👁️ Start Preview | Starts dev server for the new project |

---

## Best Practices

### Writing Good Task Descriptions

**Good:**
```
@nomark task flowmetrics add a dropdown filter for task priority with options: all, high, medium, low
```

**Bad:**
```
@nomark task flowmetrics add filter
```

### When to Use What

| Scenario | Use |
|----------|-----|
| New repository | `@nomark register <github-url>` |
| Quick bug fix | `@nomark task` |
| Small feature | `@nomark task` |
| Multi-part feature | `@nomark prd` or follow-up tasks |
| Designed in Claude.ai | `@nomark prd` |
| Need to see changes | `@nomark preview` first |
| Visual bug | Attach screenshot with task |

### Project Registration Tips

1. **Use meaningful project IDs**: If the repo name is generic, specify a custom ID
   ```
   @nomark register https://github.com/org/app my-company-app
   ```

2. **Register private repos**: Ensure `GITHUB_TOKEN` is configured on the VM

3. **Customize CLAUDE.md**: After registration, SSH and edit the project's CLAUDE.md to add:
   - Team conventions
   - Important file locations
   - Testing requirements
   - Deployment notes

4. **Check the stack detection**: Use `@nomark show <project> CLAUDE.md` to verify the detected stack is correct

### Thread Management

- **Same thread** = continue on same branch
- **New thread** = fresh branch
- Use `@nomark done` when finished to clean up
- Use `@nomark threads` to see active work

### Reviewing Changes

1. Check the PR diff on GitHub
2. Use `@nomark preview` to see live
3. Use `@nomark show <project> <file>` to view specific files
4. Send follow-up tasks in thread to iterate

---

## Troubleshooting

### Task Not Starting

**Check:**
```
@nomark status
```

If VM is stopped:
```bash
# From your Mac
nomark-start
```

### Task Stuck

**Stop it:**
```
@nomark stop
```

**Check logs:**
```
@nomark logs 20
```

### No Changes Made

Claude may need more context. Try:
1. More specific task description
2. Attach relevant files
3. Reference specific files: "in src/app/page.tsx"

### PR Not Created

Check if there were commits:
```
@nomark logs
```

If commits exist but no PR, manually:
```bash
# SSH to VM
nomark-ssh
cd ~/repos/flowmetrics
git push -u origin <branch>
gh pr create
```

### Preview Not Working

```
@nomark preview stop
@nomark preview flowmetrics
```

If still broken, SSH and check:
```bash
nomark-ssh
cd ~/repos/flowmetrics
npm run dev  # Test manually
```

### Bot Not Responding

1. Check VM is running: `nomark-status`
2. SSH and check bot: `sudo systemctl status nomark-slack`
3. Restart if needed: `sudo systemctl restart nomark-slack`
4. Check logs: `sudo journalctl -u nomark-slack -f`

### Claude Code Not Authenticated

**Check status:**
```
@nomark claude status
```

**If not authenticated, use OAuth token method (recommended):**

1. On your Mac: `claude setup-token`
2. Complete browser OAuth
3. Copy the `sk-ant-oat01-...` token
4. In Slack: `@nomark claude token <your-token>`

**If interactive login fails:**

The interactive `@nomark claude login` method can be unreliable due to session timing. Always prefer the OAuth token method above.

**If tasks fail with "Invalid API key":**

Your token may have expired. Re-authenticate using the OAuth token method.

### Project Registration Failed

**"Failed to clone repository"**
```bash
# Check the URL is correct
# For private repos, verify GITHUB_TOKEN:
nomark-ssh
echo $GITHUB_TOKEN  # Should show token
gh auth status      # Should show authenticated
```

**"Project already exists"**
```
# Use a different project ID:
@nomark register https://github.com/owner/repo different-name

# Or remove the existing one:
nomark-ssh
rm -rf ~/repos/existing-project
# Then edit ~/config/projects.json to remove the entry
```

**"Dependencies failed to install"**
```bash
# Registration continues even if deps fail
# Install manually:
nomark-ssh
cd ~/repos/<project>
npm install   # or pip install -r requirements.txt
```

**"NOMARK method files not installed"**
```bash
# Copy manually:
nomark-ssh
cp -r ~/flowmetrics-skills/organized/* ~/repos/<project>/.claude/
```

**Stack detected incorrectly**
```bash
# Edit CLAUDE.md to correct:
nomark-ssh
nano ~/repos/<project>/CLAUDE.md
```

---

## Command Quick Reference

### Task Execution

| Command | Description |
|---------|-------------|
| `@nomark task <project> <desc>` | Run a task |
| `@nomark prd <content>` | Execute PRD in Ralph mode |
| `@nomark stop` | Stop running task |
| `@nomark done` | Mark thread complete |
| `@nomark threads` | List active threads |

### Project Management

| Command | Description |
|---------|-------------|
| `@nomark register <github-url>` | Register new project |
| `@nomark projects` | List projects |
| `@nomark show <project> <file>` | View file |
| `@nomark preview <project>` | Start preview |
| `@nomark preview stop` | Stop preview |

### Status & Monitoring

| Command | Description |
|---------|-------------|
| `@nomark status` | Check VM status |
| `@nomark logs [n]` | Show logs |

### Claude Code Authentication

| Command | Description |
|---------|-------------|
| `@nomark claude status` | Check auth status |
| `@nomark claude token <token>` | Set OAuth token *(easiest re-auth)* |
| `@nomark claude login` | Start interactive login |
| `@nomark claude login <api-key>` | Set API key |
| `@nomark claude callback <code>` | Complete interactive login |
| `@nomark claude version` | Show Claude Code version |
| `@nomark claude mcp` | Check MCP server status |

### Slash Commands

| Command | Description |
|---------|-------------|
| `/nomark-task` | Quick task execution |
| `/nomark-status` | Quick status check |
| `/nomark-preview` | Quick preview start |

---

## Examples

### Example 1: Add a Feature
```
@nomark task flowmetrics add a dark mode toggle to the settings page that persists to localStorage
```

### Example 2: Fix a Bug
```
@nomark task flowmetrics fix the date picker not showing selected date on page reload
```

### Example 3: Refactor
```
@nomark task flowmetrics refactor the AdvisorList component to use React Query instead of useEffect
```

### Example 4: PRD Execution
```
@nomark prd
## Feature: Export to CSV

### Overview
Allow users to export their data to CSV format.

### Stories
1. Add ExportButton component with dropdown for format selection
2. Create CSV generation utility function
3. Implement download trigger with proper filename
4. Add loading state during export generation
5. Add success/error toast notifications

### Constraints
- Use existing Button component styling
- Support large datasets (stream if > 1000 rows)
- Include all visible columns in export
```

### Example 5: Screenshot Bug Fix
```
@nomark task flowmetrics [attach screenshot of broken layout] fix the card alignment issue shown in this screenshot
```

### Example 6: Register and Start Working on a New Project

**Step 1: Register**
```
@nomark register https://github.com/NOMARJ/inhale-v2
```

**Response:**
```
✅ Project registered successfully!

Project ID: inhale-v2
Repository: NOMARJ/inhale-v2
Stack: nextjs-typescript-supabase
Files: 247 (12M)
NOMARK: ✅ Method files installed

Get started:
@nomark task inhale-v2 <your task description>
```

**Step 2: Verify**
```
@nomark projects
```

**Step 3: Start preview**
```
@nomark preview inhale-v2
```

**Step 4: First task**
```
@nomark task inhale-v2 add user authentication with Supabase
```

**Step 5: Follow-up in same thread**
```
@nomark add password reset functionality
```

### Example 7: Register with Custom ID
```
@nomark register https://github.com/company/generic-app-repo company-frontend
```

Now use `company-frontend` as the project ID:
```
@nomark task company-frontend add dark mode toggle
```

---

## Linear Integration

NOMARK integrates with Linear for project management. This section explains how Linear concepts map to NOMARK workflows.

### Linear Doesn't Have "Epics"

Linear uses different terminology than Jira. Here's the hierarchy:

| Linear Concept | Jira Equivalent | NOMARK Usage |
|----------------|-----------------|--------------|
| **Initiatives** | Themes/Milestones | Multi-repo coordination (enable in Settings → Projects) |
| **Projects** | Epics | 1:1 with repo registration - each registered repo = 1 Linear Project |
| **Issues + "Feature" label** | Epic | Main feature/deliverable being built |
| **Sub-issues** | Stories/Tasks | Individual work items under a Feature |

### Labels

NOMARK uses these labels to categorize work:

| Label | Color | Purpose |
|-------|-------|---------|
| **Feature** | Purple | Main feature being built (acts like an Epic) |
| **Story** | Blue | Individual user stories/tasks |
| **Bug** | Red | Production bugs (future: Sentry integration) |
| **Test** | Yellow | Test-related work (future: automated testing) |
| **Improvement** | Blue | Enhancements to existing functionality |
| **nomark-devops** | Purple | Marks issues managed by NOMARK automation |

### How It Works

1. **Project Registration** → Creates a Linear Project (1:1 with repo)
2. **PRD Submission** → Creates a Feature-labeled issue with Story sub-issues
3. **Move Story to "In Progress"** → NOMARK starts working automatically
4. **Progress Updates** → Posted as comments on the Linear issue
5. **PR Created** → Story moves to "In Review"

### Workflow: Linear-First Development

You can create issues directly in Linear and NOMARK will pick them up:

1. Create an issue in your Linear Project
2. Add the **Feature** label if it's a main deliverable
3. Add sub-issues for individual stories
4. Move a story to "In Progress" → NOMARK automation triggers

### Workflow: Slack-First Development

Or continue using Slack commands:

```
@nomark task flowmetrics add user authentication
```

This creates the corresponding Linear issues automatically.

### Multi-Repo Coordination with Initiatives

When you have multiple repos that need to work together:

1. Enable Initiatives in Linear (Settings → Projects)
2. Create an Initiative for the larger goal
3. Each repo's Project maps to that Initiative
4. Track cross-repo progress at the Initiative level

---

## Claude Code Authentication

NOMARK uses Claude Code on the VM to execute tasks. Claude Code requires authentication with your Anthropic account (MAX subscription) or API key.

### Checking Auth Status

```
@nomark claude status
```

This shows whether Claude Code is authenticated and ready to run tasks.

### Authentication Methods

There are three ways to authenticate Claude Code:

#### Method 1: OAuth Token (Recommended for Re-auth)

This is the easiest and most reliable method, especially for re-authentication:

1. **On your local Mac**, run:
   ```bash
   claude setup-token
   ```

2. **Complete the browser OAuth** - signs in with your Anthropic account

3. **Copy the OAuth token** that gets generated (starts with `sk-ant-oat01-...`)

4. **In Slack**, paste the token:
   ```
   @nomark claude token sk-ant-oat01-your-token-here
   ```

The bot will save the token to the VM and verify it works.

**Why this method?**
- No interactive terminal needed on VM
- Token is portable - just copy/paste
- Works reliably every time
- Token persists in `~/.bashrc`

#### Method 2: Interactive MAX Login

For initial setup or if you prefer browser-based login:

1. Start the login flow:
   ```
   @nomark claude login
   ```

2. Click the "Sign in with Anthropic" button that appears

3. Complete the OAuth in your browser

4. Copy the callback code you receive

5. Paste the code in Slack:
   ```
   @nomark claude callback <your-code>
   ```

**Note:** This method can be unreliable due to session timing. If it fails, use Method 1 instead.

#### Method 3: API Key

If you have an Anthropic API key (starts with `sk-ant-api`):

```
@nomark claude login sk-ant-api03-your-key-here
```

**Note:** API keys have different rate limits than MAX subscriptions.

### All Claude Commands

| Command | Description |
|---------|-------------|
| `@nomark claude status` | Check authentication status |
| `@nomark claude token <token>` | Set OAuth token (recommended for re-auth) |
| `@nomark claude login` | Start interactive MAX login |
| `@nomark claude login <api-key>` | Authenticate with API key |
| `@nomark claude callback <code>` | Complete interactive login |
| `@nomark claude version` | Show Claude Code version |
| `@nomark claude mcp` | Check MCP server status |

### When to Re-authenticate

You'll need to re-authenticate when:
- OAuth token expires (typically after extended inactivity)
- VM is restarted without persistent environment
- You see "Invalid API key" or "Please run /login" errors in task output

### Troubleshooting Authentication

**"Invalid API key" errors**
```
@nomark claude status
```
If not authenticated, use `@nomark claude token` with a fresh token.

**"Setup-token failed" or "Could not capture OAuth URL"**

Use the OAuth token method instead:
1. Run `claude setup-token` on your local Mac
2. Copy the `sk-ant-oat01-...` token
3. `@nomark claude token <token>`

**Token not persisting after VM restart**

The token is stored in `~/.bashrc`. If the VM was reimaged, you'll need to re-authenticate.

**Verification unclear**

Run a simple test task:
```
@nomark task flowmetrics say hello and confirm auth works
```

---

## MCP Servers

Claude Code on the VM is configured with Model Context Protocol (MCP) servers that extend its capabilities with external integrations.

### Configured MCP Servers

| Server | Purpose |
|--------|---------|
| **linear** | Linear.app integration - manage issues, projects, and workflows |
| **github** | GitHub integration - repos, PRs, issues, actions |
| **devops-mcp** | Custom DevOps tools - Azure, Supabase, Vercel, n8n, Slack |

### Checking MCP Status

```
@nomark claude mcp
```

This shows which MCP servers are configured and their connection status.

### Linear MCP

The Linear MCP server provides tools for:
- Creating and updating issues
- Managing projects and cycles
- Searching issues with filters
- Adding comments and attachments

**Authentication:** Uses your Linear API key stored on the VM.

### GitHub MCP

The GitHub MCP server provides tools for:
- Repository operations (search, clone, list)
- Pull request management
- Issue tracking
- GitHub Actions interaction

**Authentication:** Uses your GitHub Personal Access Token stored on the VM.

### DevOps MCP

The custom DevOps MCP server (`devops-mcp`) provides tools for:

| Category | Tools |
|----------|-------|
| **Azure** | VM management, Container Apps, Key Vault, Storage |
| **Supabase** | Database queries, Auth, Storage buckets |
| **Vercel** | Deployment management, project settings |
| **n8n** | Workflow execution, webhook triggers |
| **Slack** | Send messages, notifications |
| **Skills** | Access NOMARK skills/prompts library |

**Location:** `/home/devops/repos/devops-mcp/` on the VM

### MCP Configuration

MCP servers are configured in `~/.claude.json` on the VM. The configuration includes:

```json
{
  "mcpServers": {
    "linear": {
      "type": "sse",
      "url": "https://mcp.linear.app/sse",
      "headers": {"Authorization": "<LINEAR_API_KEY>"}
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "<GITHUB_TOKEN>"}
    },
    "devops-mcp": {
      "command": "/home/devops/repos/devops-mcp/.venv/bin/python",
      "args": ["-m", "devops_mcp"],
      "env": {"GITHUB_TOKEN": "...", "LINEAR_API_KEY": "..."}
    }
  }
}
```

### Troubleshooting MCP

**MCP server not connecting**

Check the server is configured:
```bash
nomark-ssh
cat ~/.claude.json | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin).get('mcpServers',{}), indent=2))"
```

**DevOps MCP not working**

Verify installation:
```bash
nomark-ssh
cd /home/devops/repos/devops-mcp
source .venv/bin/activate
python -c "import devops_mcp; print('OK')"
```

**Missing API keys**

Check environment file:
```bash
nomark-ssh
cat ~/.env
```

Required keys:
- `LINEAR_API_KEY` - for Linear MCP
- `GITHUB_TOKEN` - for GitHub MCP and DevOps MCP

### Claude.ai MCP Connector

See [Claude.ai MCP Connector](#claudeai-mcp-connector) section for detailed usage instructions.

**Quick Setup:**

In Claude.ai: **Settings → Connectors → Add custom connector**
- **Name:** `DevOps MCP`
- **URL:** `https://20-5-185-136.sslip.io/sse`

This is a **static URL** that doesn't change. It uses Azure's public IP with automatic SSL via Caddy.

**SSE Server Management:**

| Service | Purpose | Port |
|---------|---------|------|
| `devops-mcp` | SSE server | 8080 |
| `caddy` | HTTPS reverse proxy | 443 |

```bash
# Check status
sudo systemctl status devops-mcp caddy

# Restart if needed
sudo systemctl restart devops-mcp caddy

# View logs
sudo journalctl -u devops-mcp -f
```

**Available Endpoints:**

| Endpoint | Purpose |
|----------|---------|
| `/sse` | MCP SSE connection for Claude.ai |
| `/health` | Health check (JSON status) |
| `/tools` | List all 76 available tools |
| `/messages/` | POST endpoint for MCP messages |

---

## Support

- **VM IP:** 20.5.185.136
- **SSH:** `nomark-ssh` (from Mac with env loaded)
- **Logs:** `@nomark logs` or `sudo journalctl -u nomark-slack -f` on VM

---

*NOMARK DevOps - Simple. Efficient. Wins.*
