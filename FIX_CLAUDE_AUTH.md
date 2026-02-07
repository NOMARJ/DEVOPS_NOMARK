# Fix Claude CLI Authentication for Claude Max

## Problem

Your Slack bot is failing with "Credit balance is too low" because the Claude CLI on the Azure VM is using API credits instead of your Claude Max subscription.

**Error:**
```
Credit balance is too low
```

**Root Cause:**
The `claude` CLI on the VM (version 2.1.19) needs to be authenticated with your Claude.ai account that has the Claude Max subscription.

---

## Solution: Authenticate Claude CLI on VM

### Option 1: Interactive Authentication (Recommended)

1. **SSH to the VM:**
   ```bash
   ssh devops@20.5.185.136
   ```

2. **Start Claude authentication:**
   ```bash
   claude auth login
   ```

3. **Follow the prompts:**
   - The CLI will show you a URL and code
   - Open the URL in your browser
   - Log in with your Claude.ai account (the one with Claude Max)
   - Enter the code shown by the CLI
   - Confirm the authentication

4. **Verify authentication:**
   ```bash
   claude auth status
   ```

   Should show:
   ```
   ✓ Authenticated as: your-email@domain.com
   ✓ Subscription: Claude Max
   ```

5. **Test it:**
   ```bash
   claude "say hello"
   ```

6. **Exit SSH:**
   ```bash
   exit
   ```

7. **Test from Slack:**
   ```
   @DevOps task inhhale-v2 complete the iOS audit
   ```

---

### Option 2: Use Session Token from Your Machine

If you're already authenticated on your local machine:

1. **On your local machine, get your session token:**
   ```bash
   cat ~/.claude/config.json | jq -r '.sessionKey'
   ```

2. **Copy the token, then SSH to VM:**
   ```bash
   ssh devops@20.5.185.136
   ```

3. **Create Claude config directory:**
   ```bash
   mkdir -p ~/.claude
   ```

4. **Set the session token:**
   ```bash
   cat > ~/.claude/config.json << 'EOF'
   {
     "sessionKey": "YOUR_SESSION_TOKEN_HERE"
   }
   EOF
   # Replace YOUR_SESSION_TOKEN_HERE with the actual token
   ```

5. **Verify:**
   ```bash
   claude auth status
   ```

6. **Exit and test from Slack**

---

### Option 3: Use Environment Variable (Temporary)

For a quick test:

```bash
ssh devops@20.5.185.136

# Set session key as environment variable
export CLAUDE_SESSION_KEY="your-session-token"

# Test
claude "say hello"

# Make it permanent by adding to ~/.bashrc
echo 'export CLAUDE_SESSION_KEY="your-session-token"' >> ~/.bashrc
```

---

## Verification Steps

After authentication, verify everything works:

1. **Check auth status:**
   ```bash
   ssh devops@20.5.185.136 "claude auth status"
   ```

   Expected output:
   ```
   ✓ Authenticated
   ✓ Using Claude Max subscription
   ```

2. **Test simple command:**
   ```bash
   ssh devops@20.5.185.136 "claude 'count to 3'"
   ```

   Should return:
   ```
   1, 2, 3
   ```

3. **Check Slack bot can use it:**
   ```
   @DevOps task inhhale-v2 list all Swift files
   ```

   Should work without credit errors ✅

---

## Update Bot to Use Authenticated Claude

The bot is already configured correctly! The `nomark-task.sh` script uses:

```bash
claude --dangerously-skip-permissions --print "..."
```

This will automatically use your authenticated session once you complete the steps above.

---

## Understanding the Architecture

### How It Currently Works:

```
Slack Message
    ↓
Slack Bot (slack-bot.py)
    ↓
Task Script (nomark-task.sh)
    ↓
Claude CLI (claude command)
    ↓
??? Uses API key (WRONG - no credits)
    ✗ "Credit balance is too low"
```

### How It Should Work:

```
Slack Message
    ↓
Slack Bot (slack-bot.py)
    ↓
Task Script (nomark-task.sh)
    ↓
Claude CLI (claude command)
    ↓
✓ Uses authenticated session (Claude Max)
    ✓ Unlimited usage with Claude Max subscription
```

---

## What About the ANTHROPIC_API_KEY?

**Q: Do I still need the ANTHROPIC_API_KEY in the environment?**

**A:** It depends:

- **For Claude CLI tasks** (most tasks): No, use authenticated session
- **For image analysis in Slack** (optional feature): Yes, keep it for now

The Slack bot uses the API key only for analyzing images attached to messages. The main task execution uses the `claude` CLI, which should use your authenticated session.

---

## Long-term Solution: Remove API Dependency

To fully remove the API key dependency, you can:

1. **Remove image analysis feature** (if not needed):
   ```python
   # In slack-bot.py, comment out the image analysis code
   ```

2. **Or use Claude CLI for image analysis too**:
   - Update the image analysis to call `claude` with the image
   - This will use your Max subscription

For now, just authenticate the Claude CLI and you'll be good to go!

---

## Quick Fix Script

I've created a helper script for you:

```bash
#!/bin/bash
# fix-claude-auth.sh

echo "Fixing Claude CLI authentication on Azure VM..."

# SSH and authenticate
ssh devops@20.5.185.136 << 'ENDSSH'
echo "Starting Claude authentication..."
claude auth login

echo ""
echo "Verifying authentication..."
claude auth status

echo ""
echo "Testing Claude CLI..."
claude "respond with: Authentication successful!"

echo ""
echo "Done! Exit this SSH session and test from Slack."
ENDSSH

echo ""
echo "Now test from Slack:"
echo "  @DevOps task inhhale-v2 complete the iOS audit"
```

---

## Summary

**Problem:** Claude CLI not authenticated → uses API credits → fails

**Solution:** Run `claude auth login` on the VM → uses Claude Max → unlimited

**Steps:**
1. SSH to VM: `ssh devops@20.5.185.136`
2. Login: `claude auth login`
3. Follow browser prompts
4. Verify: `claude auth status`
5. Test from Slack: `@DevOps task inhhale-v2 <task>`

**Time:** 2 minutes ⏱️

---

## Need Help?

If `claude auth login` doesn't work:

1. Check Claude Code version:
   ```bash
   claude --version
   ```
   Should be 2.x.x or higher

2. Update if needed:
   ```bash
   npm install -g @anthropic-ai/claude-code@latest
   ```

3. Try authentication again

---

**Ready to fix it now?**

```bash
ssh devops@20.5.185.136
claude auth login
```

Then test: `@DevOps task inhhale-v2 complete the iOS audit` ✅
