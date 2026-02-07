# Slack Bot Project Selector - Complete Solution

## Executive Summary

Your Slack bot shows `❌ Unknown project: 'inhhale-v2'` because:
- **Root Cause**: Missing or misconfigured `~/config/projects.json` file
- **Impact**: Users cannot execute tasks on the inhhale-v2 project
- **Solution**: Two-part fix (immediate + long-term)

## Solution Overview

### ✅ Immediate Fix (5 minutes)
Create and configure `~/config/projects.json` with correct project definitions.

**Result**: Bot recognizes "inhhale-v2" and all other projects correctly.

### 🚀 Long-term Fix (30 minutes)
Implement interactive project selection dropdown in Slack messages.

**Result**: Users never face typo issues again - just select from dropdown.

---

## Files Created for You

| File | Purpose | Use Case |
|------|---------|----------|
| [QUICK_FIX_GUIDE.md](QUICK_FIX_GUIDE.md) | Fast reference for immediate fix | Quick resolution |
| [SLACK_PROJECT_SELECTOR_IMPLEMENTATION.md](SLACK_PROJECT_SELECTOR_IMPLEMENTATION.md) | Detailed implementation guide | Full understanding |
| [slack-bot-project-selector.py](slack-bot-project-selector.py) | Ready-to-use Python code | Copy-paste implementation |
| [test-project-selector.sh](test-project-selector.sh) | Automated validation script | Verify configuration |
| PROJECT_SELECTOR_SUMMARY.md | This file - executive overview | Quick reference |

---

## Quick Start Guide

### Step 1: Immediate Fix (Do This Now)

**On your server where the Slack bot runs:**

```bash
# 1. Create config directory
mkdir -p ~/config

# 2. Create projects.json
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

# 3. Restart Slack bot
pkill -f slack-bot.py
nohup python3 ~/scripts/slack-bot.py > ~/logs/slack-bot.log 2>&1 &

# 4. Verify configuration
bash ~/DEVOPS_NOMARK/test-project-selector.sh
```

**Test in Slack:**
```
@DevOps task inhhale-v2 complete the iOS audit
```

Should now work! ✅

---

### Step 2: Long-term Fix (Schedule Later)

**Purpose**: Add dropdown menus so users never have to type project names manually.

**Before (current - error-prone):**
```
User types: @DevOps task inhale-v2 do something
Bot:        ❌ Unknown project: `inhale-v2`
            [Lists all projects as text]
User:       Has to retype entire command with correct spelling
```

**After (with dropdown - foolproof):**
```
User types: @DevOps task inhale-v2 do something
Bot:        ❌ Unknown project: `inhale-v2`
            🎯 Select the correct project:
            [Dropdown menu appears with all projects]

User:       [Clicks "Inhhale iOS App (swift-ios) [P4]"]
Bot:        ✅ Project selected: Inhhale iOS App
            🚀 Starting task on `inhhale-v2`...
            [Task starts automatically - no retyping needed!]
```

**Implementation Steps:**

1. **Review the implementation guide**
   ```bash
   cat ~/DEVOPS_NOMARK/SLACK_PROJECT_SELECTOR_IMPLEMENTATION.md
   ```

2. **Edit your Slack bot**
   ```bash
   nano ~/scripts/slack-bot.py
   ```

3. **Copy code from slack-bot-project-selector.py**
   - Add `create_project_selector_blocks()` function (after line 150)
   - Add `@app.action("select_project_for_task")` handler (after line 1540)
   - Update `task` command handler (around line 2180)

4. **Restart and test**
   ```bash
   pkill -f slack-bot.py
   python3 ~/scripts/slack-bot.py &

   # Test with invalid project name in Slack:
   # @DevOps task wrongproject do something
   # Should show dropdown!
   ```

**Detailed instructions**: See [SLACK_PROJECT_SELECTOR_IMPLEMENTATION.md](SLACK_PROJECT_SELECTOR_IMPLEMENTATION.md)

---

## Why This Happened

### The Error Message Breakdown

```
❌ Unknown project: `inhhale-v2`

Available Projects:
• flowmetrics - FlowMetrics (sveltekit-postgres) [P1]
• instaindex - InstaIndex (nextjs-supabase) [P2]
• inhhale-v2 - inhhale-v2 (unknown) [P4]
```

**Confusing, right?** The bot lists "inhhale-v2" as available but still rejects it!

**Why this happens:**

1. **The list is generated differently** than validation
   - List: Shows projects from bot's memory/cache
   - Validation: Reads from `~/config/projects.json`

2. **The file doesn't exist or is misconfigured**
   - Bot can't find the file at runtime
   - File has invalid JSON syntax
   - Project exists but has `"active": false`

3. **Text parsing is fragile**
   - Case-sensitive: `inhhale-v2` ≠ `Inhhale-v2`
   - No fuzzy matching: Typos fail immediately
   - No autocomplete: Users must remember exact IDs

---

## How the Bot Works

### Current Architecture (Text-Based)

```
User Message: "@DevOps task inhhale-v2 complete audit"
      ↓
[1] Parse message: Split by spaces
      ↓
[2] Extract parts: ["task", "inhhale-v2", "complete audit"]
      ↓
[3] Load projects: Read ~/config/projects.json
      ↓
[4] Validate: Check if "inhhale-v2" in project IDs
      ↓
[5] Execute or Error: Start task OR show error message
```

**Problem**: Step 3 fails if `projects.json` is missing/invalid.

### Code Location in slack-bot.py

| Component | File Location | Line # |
|-----------|--------------|--------|
| Load projects.json | `load_projects()` | ~118 |
| Get active projects | `get_active_projects()` | ~126 |
| Format project list | `format_project_list()` | ~137 |
| Validate project | `run_task()` | ~1870-1879 |
| Handle @mentions | `handle_mention()` | ~2067 |
| Task command | Inside `handle_mention()` | ~2180 |

---

## Testing & Validation

### Automated Testing

Run the included test script:

```bash
cd ~/DEVOPS_NOMARK
bash test-project-selector.sh
```

**What it checks:**
- ✓ Config directory exists
- ✓ projects.json exists and has valid JSON
- ✓ Required fields present (id, name, active)
- ✓ No duplicate project IDs
- ✓ inhhale-v2 project exists and is active
- ✓ File permissions are correct
- ✓ Slack bot process is running
- ✓ Lists all active projects

### Manual Testing Checklist

**Test 1: Valid project**
```
Slack: @DevOps task inhhale-v2 complete the iOS audit
Expected: ✅ Task starts
```

**Test 2: Invalid project (before dropdown implementation)**
```
Slack: @DevOps task wrongproject do something
Expected: ❌ Error message with project list
```

**Test 3: Invalid project (after dropdown implementation)**
```
Slack: @DevOps task wrongproject do something
Expected: ❌ Error message with dropdown selector
         [User clicks correct project from dropdown]
         ✅ Task starts automatically
```

**Test 4: List projects**
```
Slack: @DevOps projects
Expected: Shows all active projects
```

**Test 5: Register new project**
```
Slack: @DevOps register https://github.com/NOMARK/new-project
Expected: Clones repo, detects stack, adds to projects.json
```

---

## Troubleshooting Guide

### Issue: "Unknown project" persists after fix

**Diagnosis steps:**

```bash
# 1. Verify file exists
ls -la ~/config/projects.json

# 2. Check JSON is valid
cat ~/config/projects.json | jq .

# 3. Verify project exists
cat ~/config/projects.json | jq '.projects[] | select(.id == "inhhale-v2")'

# 4. Check if active
cat ~/config/projects.json | jq '.projects[] | select(.id == "inhhale-v2") | .active'

# 5. Verify bot is running
ps aux | grep slack-bot.py

# 6. Check bot logs
tail -50 ~/logs/slack-bot.log

# 7. Restart bot
pkill -f slack-bot.py
python3 ~/scripts/slack-bot.py &
```

### Issue: Dropdown doesn't appear

**Cause**: Code changes not implemented yet.

**Solution**:
1. The immediate fix (projects.json) makes projects work with text commands
2. The dropdown requires code changes to slack-bot.py
3. Follow Step 2 (Long-term Fix) to implement dropdown

### Issue: Bot shows project in list but still rejects it

**Cause**: Project has `"active": false` or bot hasn't restarted.

**Solution**:
```bash
# Set project to active
jq '(.projects[] | select(.id == "inhhale-v2") | .active) = true' \
   ~/config/projects.json > ~/config/projects.json.tmp
mv ~/config/projects.json.tmp ~/config/projects.json

# Restart bot
pkill -f slack-bot.py
python3 ~/scripts/slack-bot.py &
```

---

## Project Management Tips

### Adding a New Project

**Method 1: Via Slack (Automatic)**
```
@DevOps register https://github.com/org/repo
```
Bot automatically:
- Clones the repo
- Detects tech stack
- Generates project ID
- Adds to projects.json

**Method 2: Manual JSON Edit**
```bash
nano ~/config/projects.json
```

Add to `projects` array:
```json
{
  "id": "my-project",
  "name": "My Project Name",
  "repo": "org/repo-name",
  "stack": "nextjs-supabase",
  "priority": 5,
  "active": true
}
```

**Method 3: Using jq command**
```bash
jq '.projects += [{
  "id": "my-project",
  "name": "My Project",
  "repo": "org/repo",
  "stack": "nextjs",
  "priority": 5,
  "active": true
}]' ~/config/projects.json > ~/config/projects.json.tmp

mv ~/config/projects.json.tmp ~/config/projects.json
```

### Deactivating a Project

```bash
# Deactivate (hides from bot, keeps in config)
jq '(.projects[] | select(.id == "old-project") | .active) = false' \
   ~/config/projects.json > ~/config/projects.json.tmp
mv ~/config/projects.json.tmp ~/config/projects.json
```

### Removing a Project

```bash
# Completely remove from config
jq '.projects = [.projects[] | select(.id != "old-project")]' \
   ~/config/projects.json > ~/config/projects.json.tmp
mv ~/config/projects.json.tmp ~/config/projects.json
```

---

## Implementation Approaches Comparison

| Approach | Pros | Cons | Effort | Recommended |
|----------|------|------|--------|-------------|
| **A: Inline Dropdown** | Simple, minimal code | Only shows on error | Low | ✅ Yes |
| **B: Modal Dialog** | Rich UX, validation | More code, new command | Medium | Later |
| **C: Autocomplete** | Best UX | Requires external API | High | Future |

**Recommendation**: Start with Approach A (inline dropdown on error), add B later if needed.

---

## Next Steps

### Immediate (Today)

1. ✅ **Fix projects.json** - 5 minutes
   ```bash
   # Run commands from "Step 1: Immediate Fix" above
   ```

2. ✅ **Test basic functionality** - 2 minutes
   ```
   # In Slack: @DevOps task inhhale-v2 complete audit
   ```

3. ✅ **Run validation script** - 1 minute
   ```bash
   bash ~/DEVOPS_NOMARK/test-project-selector.sh
   ```

### This Week

4. 📋 **Review implementation guide** - 10 minutes
   - Read [SLACK_PROJECT_SELECTOR_IMPLEMENTATION.md](SLACK_PROJECT_SELECTOR_IMPLEMENTATION.md)
   - Understand the dropdown approach

5. 🔧 **Implement dropdown selector** - 30 minutes
   - Follow code in [slack-bot-project-selector.py](slack-bot-project-selector.py)
   - Test with team

6. 📚 **Document for team** - 5 minutes
   - Share QUICK_FIX_GUIDE.md with team
   - Show dropdown feature

### Future Enhancements

- 🎯 Add fuzzy matching ("did you mean...")
- 🔍 Implement autocomplete for project names
- 📊 Track most-used projects
- ⚡ Add keyboard shortcuts
- 🎨 Customize project icons/colors

---

## Support & Resources

### Documentation

- **Quick Reference**: [QUICK_FIX_GUIDE.md](QUICK_FIX_GUIDE.md)
- **Full Guide**: [SLACK_PROJECT_SELECTOR_IMPLEMENTATION.md](SLACK_PROJECT_SELECTOR_IMPLEMENTATION.md)
- **Code**: [slack-bot-project-selector.py](slack-bot-project-selector.py)
- **Testing**: [test-project-selector.sh](test-project-selector.sh)

### Useful Commands

```bash
# View all projects
cat ~/config/projects.json | jq '.projects[] | "\(.id) - \(.name)"'

# View only active projects
cat ~/config/projects.json | jq '.projects[] | select(.active == true) | .id'

# Count projects
cat ~/config/projects.json | jq '.projects | length'

# Find project by ID
cat ~/config/projects.json | jq '.projects[] | select(.id == "inhhale-v2")'

# Validate JSON
cat ~/config/projects.json | jq empty && echo "Valid JSON" || echo "Invalid JSON"

# Check bot status
ps aux | grep slack-bot.py

# View bot logs
tail -f ~/logs/slack-bot.log

# Restart bot
pkill -f slack-bot.py && python3 ~/scripts/slack-bot.py &
```

---

## Summary

✅ **Problem Identified**: Missing/misconfigured projects.json
✅ **Immediate Fix**: Create projects.json with correct configuration
✅ **Long-term Fix**: Add interactive dropdown selector
✅ **Files Provided**: Complete implementation code and guides
✅ **Testing**: Automated validation script included

**You're all set!** Start with the immediate fix, then implement the dropdown when you have time.

Questions? Check the detailed guides or test script output for specific issues.
