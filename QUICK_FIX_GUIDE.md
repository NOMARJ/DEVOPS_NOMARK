# Quick Fix Guide: "Unknown project: inhhale-v2"

## The Problem

Your Slack bot shows this error:
```
❌ Unknown project: `inhhale-v2`

Available Projects:
• flowmetrics - FlowMetrics (sveltekit-postgres) [P1]
• instaindex - InstaIndex (nextjs-supabase) [P2]
• inhhale-v2 - inhhale-v2 (unknown) [P4]
```

**Root Cause:** The bot lists "inhhale-v2" as available but still rejects it. This happens when:
1. The `~/config/projects.json` file is missing or misconfigured
2. The project exists in the list but `active: false` is set
3. There's a mismatch in project ID casing or spelling

---

## Immediate Fix (2 minutes)

### Step 1: Create/Fix projects.json

```bash
# SSH into your server where the Slack bot runs
ssh your-server

# Create config directory
mkdir -p ~/config

# Create projects.json with all your projects
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

### Step 2: Restart the Slack Bot

```bash
# Stop the bot
pkill -f slack-bot.py

# Start it again (adjust path if needed)
nohup python3 ~/scripts/slack-bot.py > ~/logs/slack-bot.log 2>&1 &

# Or if using systemd:
sudo systemctl restart slack-bot
```

### Step 3: Test

In Slack, try:
```
@DevOps task inhhale-v2 complete the iOS audit
```

Should now work! ✅

---

## Permanent Fix: Add Project Selection Dropdown (30 minutes)

To prevent typo issues permanently, implement the interactive project selector.

### What You Get

**Before (current):**
```
User: @DevOps task inhale-v2 do something
Bot:  ❌ Unknown project: `inhale-v2`
      [User has to retype everything]
```

**After (with selector):**
```
User: @DevOps task inhale-v2 do something
Bot:  ❌ Unknown project: `inhale-v2`
      🎯 Select the correct project:
      [Dropdown showing: flowmetrics, instaindex, inhhale-v2]
      💡 Tip: Available project IDs: flowmetrics, instaindex, inhhale-v2

User: [Clicks "Inhhale iOS App (swift-ios) [P4]" from dropdown]
Bot:  ✅ Project selected: Inhhale iOS App (swift-ios) [P4]
      🚀 Starting task on `inhhale-v2`...
      Task: do something
```

### Implementation Files

I've created two files for you:

1. **[SLACK_PROJECT_SELECTOR_IMPLEMENTATION.md](SLACK_PROJECT_SELECTOR_IMPLEMENTATION.md)**
   - Detailed explanation of the problem
   - Multiple implementation approaches
   - Step-by-step guide
   - Testing checklist

2. **[slack-bot-project-selector.py](slack-bot-project-selector.py)**
   - Ready-to-use Python code
   - Copy-paste functions into your slack-bot.py
   - Detailed inline comments
   - Installation checklist at the bottom

### Quick Installation

```bash
# 1. Edit your slack-bot.py
nano ~/scripts/slack-bot.py

# 2. Copy these sections from slack-bot-project-selector.py:
#    - create_project_selector_blocks() → Add after line 150
#    - @app.action("select_project_for_task") → Add after line 1540
#    - Update "task" command handler → Replace around line 2180

# 3. Restart bot
pkill -f slack-bot.py
python3 ~/scripts/slack-bot.py &

# 4. Test
# In Slack: @DevOps task wrongname do something
# Should show dropdown!
```

---

## Verification Checklist

After implementing the fix, verify:

- [ ] `~/config/projects.json` exists and is readable
- [ ] All projects have `"active": true`
- [ ] Project IDs match exactly (case-sensitive)
- [ ] Bot is restarted and running
- [ ] Test command works: `@DevOps task inhhale-v2 complete audit`
- [ ] Invalid project shows dropdown: `@DevOps task wrongname test`
- [ ] `@DevOps projects` shows all projects

---

## Troubleshooting

### Issue: Bot still says "Unknown project"

**Check 1: File exists?**
```bash
cat ~/config/projects.json | jq .
```

**Check 2: Bot can read it?**
```bash
ls -la ~/config/projects.json
# Should be readable by the user running the bot
```

**Check 3: Project is active?**
```bash
cat ~/config/projects.json | jq '.projects[] | select(.id == "inhhale-v2")'
# Should show: "active": true
```

**Check 4: Bot is actually restarted?**
```bash
ps aux | grep slack-bot.py
# Should show a running process
```

### Issue: Projects list shows but bot still rejects

This means the bot hasn't reloaded `projects.json`. Solutions:

```bash
# Option 1: Restart bot
pkill -f slack-bot.py
python3 ~/scripts/slack-bot.py &

# Option 2: If using systemd
sudo systemctl restart slack-bot

# Option 3: Check bot is reading the right file
# Add this debug line in slack-bot.py get_active_projects():
# print(f"DEBUG: Loading from {PROJECTS_FILE}")
```

### Issue: Dropdown doesn't appear

The dropdown feature requires code changes to `slack-bot.py`. If you only fixed `projects.json`:
- ✅ Bot will recognize correct project names
- ❌ Dropdown won't appear for invalid names (still shows text list)

To get the dropdown, follow the "Permanent Fix" section above.

---

## Project Management Scripts

### Quick Add Project

```bash
# Add this function to your ~/.bashrc or ~/.zshrc
nomark-add-project() {
    local id="$1"
    local name="$2"
    local repo="$3"
    local stack="${4:-unknown}"
    local priority="${5:-99}"

    if [[ -z "$id" || -z "$name" || -z "$repo" ]]; then
        echo "Usage: nomark-add-project <id> <name> <repo> [stack] [priority]"
        echo "Example: nomark-add-project myapp 'My App' 'org/myapp' 'nextjs' 5"
        return 1
    fi

    jq --arg id "$id" \
       --arg name "$name" \
       --arg repo "$repo" \
       --arg stack "$stack" \
       --argjson priority "$priority" \
       '.projects += [{
           "id": $id,
           "name": $name,
           "repo": $repo,
           "stack": $stack,
           "priority": $priority,
           "active": true
       }]' ~/config/projects.json > ~/config/projects.json.tmp

    mv ~/config/projects.json.tmp ~/config/projects.json
    echo "✅ Added project: $id"
    cat ~/config/projects.json | jq '.projects[] | "\(.id) - \(.name)"'
}
```

Usage:
```bash
nomark-add-project inhhale-v2 "Inhhale iOS App" "NOMARK/inhhale-v2" "swift-ios" 4
```

### List Projects

```bash
alias nomark-projects="cat ~/config/projects.json | jq -r '.projects[] | \"\(.id) - \(.name) (\(.stack)) [P\(.priority)] active=\(.active)\"'"
```

Usage:
```bash
$ nomark-projects
flowmetrics - FlowMetrics (sveltekit-postgres) [P1] active=true
instaindex - InstaIndex (nextjs-supabase) [P2] active=true
inhhale-v2 - Inhhale iOS App (swift-ios) [P4] active=true
```

### Toggle Project Active Status

```bash
nomark-toggle-project() {
    local id="$1"
    if [[ -z "$id" ]]; then
        echo "Usage: nomark-toggle-project <project-id>"
        return 1
    fi

    local current=$(jq -r ".projects[] | select(.id == \"$id\") | .active" ~/config/projects.json)

    if [[ "$current" == "true" ]]; then
        jq "(.projects[] | select(.id == \"$id\") | .active) = false" ~/config/projects.json > ~/config/projects.json.tmp
        echo "✅ Deactivated: $id"
    else
        jq "(.projects[] | select(.id == \"$id\") | .active) = true" ~/config/projects.json > ~/config/projects.json.tmp
        echo "✅ Activated: $id"
    fi

    mv ~/config/projects.json.tmp ~/config/projects.json
}
```

---

## Summary

### What Causes the Error?

1. Missing or empty `~/config/projects.json`
2. Project not listed in the JSON file
3. Project has `"active": false`
4. Project ID typo (case-sensitive)
5. Bot not restarted after config changes

### How to Fix?

**Immediate (2 min):**
1. Create `~/config/projects.json` with your projects
2. Ensure `"active": true` for each project
3. Restart the Slack bot
4. Test: `@DevOps task inhhale-v2 <task>`

**Long-term (30 min):**
1. Implement the project selector dropdown
2. Copy code from `slack-bot-project-selector.py`
3. Update command handlers in `slack-bot.py`
4. Restart bot and test

### Files Created for You

- `SLACK_PROJECT_SELECTOR_IMPLEMENTATION.md` - Full guide
- `slack-bot-project-selector.py` - Ready-to-use code
- `QUICK_FIX_GUIDE.md` - This file

### Next Steps

1. ✅ Fix `~/config/projects.json` (immediate fix)
2. ✅ Restart bot and verify it works
3. 📋 Schedule time to implement dropdown selector
4. 🚀 Test dropdown with team
5. 📝 Document for team: "Use dropdown when project name rejected"

Done! Your "inhhale-v2" project should now be recognized. 🎉
