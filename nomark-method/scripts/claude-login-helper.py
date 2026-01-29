#!/usr/bin/env python3
"""
Claude Code Login Helper

Captures the OAuth URL from `claude setup-token` and provides it for
remote authentication via Slack.

This script:
1. Runs `claude setup-token` in a pseudo-TTY
2. Captures the OAuth URL
3. Sets up a temporary web server to receive the callback code
4. Completes the authentication

Usage:
  claude-login-helper.py start   - Start login flow, returns OAuth URL
  claude-login-helper.py status  - Check current auth status
  claude-login-helper.py callback <code> - Complete auth with callback code
"""

import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import pty
import select
import time

# State file for tracking login flow
STATE_FILE = Path.home() / "config" / "claude-login-state.json"


def save_state(state: dict):
    """Save login state to file."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def load_state() -> dict:
    """Load login state from file."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def check_auth_status() -> dict:
    """Check Claude Code authentication status."""
    try:
        # Use --print mode to actually test if auth works
        result = subprocess.run(
            ["claude", "--print", "test"],
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout + result.stderr

        if "Invalid API key" in output or "Please run /login" in output or "login" in output.lower():
            return {
                "authenticated": False,
                "message": "Not authenticated",
                "output": output.strip()
            }
        elif result.returncode == 0 and output.strip():
            return {
                "authenticated": True,
                "message": "Authenticated",
                "output": output.strip()[:100]
            }
        else:
            return {
                "authenticated": False,
                "message": "Authentication unclear",
                "output": output.strip()
            }
    except Exception as e:
        return {
            "authenticated": False,
            "message": f"Error checking status: {e}",
            "output": ""
        }


def start_login_flow() -> dict:
    """
    Start the Claude Code login flow and capture the OAuth URL.
    Uses expect for proper TTY handling.

    Returns dict with:
    - success: bool
    - oauth_url: str (if successful)
    - error: str (if failed)
    """
    try:
        # Use expect script for proper TTY handling
        expect_script = Path.home() / "scripts" / "claude-login-expect-start.exp"

        if expect_script.exists():
            # Use expect script
            result = subprocess.run(
                ["timeout", "60", str(expect_script)],
                capture_output=True,
                text=True,
                timeout=65
            )
            output = result.stdout + result.stderr
        else:
            # Fallback to pty method
            return start_login_flow_pty()

        # Parse the output for OAuth URL
        oauth_url = None
        for line in output.split('\n'):
            if line.startswith('OAUTH_URL:'):
                oauth_url = line.replace('OAUTH_URL:', '').strip()
                break
            # Also check for raw URL in output
            if 'https://claude.ai/oauth/authorize' in line:
                match = re.search(r'(https://claude\.ai/oauth/authorize[^\s]+state=[a-zA-Z0-9_-]+)', line)
                if match:
                    oauth_url = match.group(1)
                    break

        # If expect script output didn't have clean URL, parse from raw output
        if not oauth_url and 'claude.ai/oauth' in output:
            # Clean ANSI codes
            clean_output = re.sub(r'\x1b\[[0-9;?]*[a-zA-Z]', '', output)
            clean_output = re.sub(r'\x1b\].*?\x07', '', clean_output)
            clean_output = re.sub(r'\x1b[^\[].?', '', clean_output)
            clean_output = re.sub(r'\x1b', '', clean_output)

            # Reconstruct URL from wrapped lines
            lines = clean_output.split('\n')
            url_parts = []
            url_started = False

            for line in lines:
                line = line.strip()
                if 'https://claude.ai/oauth' in line:
                    match = re.search(r'(https://claude\.ai/oauth[^\s]*)', line)
                    if match:
                        url_parts.append(match.group(1))
                        url_started = True
                elif url_started and line and not line.startswith('Paste') and 'Browser' not in line:
                    if re.match(r'^[a-zA-Z0-9%=&_-]+', line):
                        url_parts.append(line.split()[0] if ' ' in line else line)
                    else:
                        break

            if url_parts:
                oauth_url = ''.join(url_parts)
                # Extract just the valid URL - state param is the last param and ends with alphanumeric chars
                state_match = re.search(r'(https://claude\.ai/oauth/authorize\?[^O]+state=[a-zA-Z0-9_-]+)', oauth_url)
                if state_match:
                    oauth_url = state_match.group(1)
                # Clean any trailing garbage that might have been appended (like OAUTH_URL from expect output)
                oauth_url = re.sub(r'(state=[a-zA-Z0-9_-]+)(?:OAUTH_URL|READY_FOR_CODE|EOF|TIMEOUT).*$', r'\1', oauth_url)
                # Also catch any non-URL characters at the end
                oauth_url = re.sub(r'(state=[a-zA-Z0-9_-]+)[^a-zA-Z0-9_-].*$', r'\1', oauth_url)

        if oauth_url:
            save_state({
                "oauth_url": oauth_url,
                "started_at": datetime.now().isoformat(),
                "status": "pending"
            })

            return {
                "success": True,
                "oauth_url": oauth_url
            }
        else:
            return {
                "success": False,
                "error": "Could not capture OAuth URL",
                "output": output[:500]
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def start_login_flow_pty() -> dict:
    """Fallback pty-based login flow."""
    try:
        master_fd, slave_fd = pty.openpty()
        process = subprocess.Popen(
            ["claude", "setup-token"],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            preexec_fn=os.setsid
        )
        os.close(slave_fd)

        output = ""
        oauth_url = None
        start_time = time.time()
        timeout_secs = 30

        while time.time() - start_time < timeout_secs:
            readable, _, _ = select.select([master_fd], [], [], 0.5)
            if readable:
                try:
                    chunk = os.read(master_fd, 4096).decode('utf-8', errors='replace')
                    output += chunk
                    if "claude.ai/oauth" in output and "state=" in output:
                        clean_output = re.sub(r'\x1b\[[0-9;?]*[a-zA-Z]', '', output)
                        clean_output = re.sub(r'\x1b\].*?\x07', '', clean_output)
                        clean_output = re.sub(r'\x1b[^\[].?', '', clean_output)
                        clean_output = re.sub(r'\x1b', '', clean_output)

                        lines = clean_output.split('\n')
                        url_parts = []
                        url_started = False

                        for line in lines:
                            line = line.strip()
                            if 'https://claude.ai/oauth' in line:
                                match = re.search(r'(https://claude\.ai/oauth[^\s]*)', line)
                                if match:
                                    url_parts.append(match.group(1))
                                    url_started = True
                            elif url_started and line and not line.startswith('Paste') and 'Browser' not in line:
                                if re.match(r'^[a-zA-Z0-9%=&_-]+', line):
                                    url_parts.append(line.split()[0] if ' ' in line else line)
                                else:
                                    break

                        if url_parts:
                            oauth_url = ''.join(url_parts)
                            if 'state=' in oauth_url:
                                state_match = re.search(r'(https://claude\.ai/oauth/authorize\?.*?state=[a-zA-Z0-9_-]+)', oauth_url)
                                if state_match:
                                    oauth_url = state_match.group(1)
                                break
                except OSError:
                    break
            if process.poll() is not None:
                break

        try:
            os.close(master_fd)
        except OSError:
            pass
        try:
            process.terminate()
            process.wait(timeout=5)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass

        if oauth_url:
            save_state({
                "oauth_url": oauth_url,
                "started_at": datetime.now().isoformat(),
                "status": "pending"
            })
            return {"success": True, "oauth_url": oauth_url}
        else:
            return {"success": False, "error": "Could not capture OAuth URL", "output": output[:500]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def complete_login_with_code(code: str) -> dict:
    """
    Complete the login flow by providing the callback code.
    Uses expect for proper TTY handling.
    """
    try:
        # Use expect script for proper TTY handling
        expect_script = Path.home() / "scripts" / "claude-login-callback.exp"

        if expect_script.exists():
            result = subprocess.run(
                ["timeout", "90", str(expect_script), code],
                capture_output=True,
                text=True,
                timeout=95
            )
            output = result.stdout + result.stderr

            success = "SUCCESS" in output or "Signed in" in output or "signed in" in output.lower()
        else:
            # Fallback to pty method
            return complete_login_with_code_pty(code)

        # Update state
        state = load_state()
        state["status"] = "completed" if success else "failed"
        state["completed_at"] = datetime.now().isoformat()
        save_state(state)

        if success:
            return {
                "success": True,
                "message": "Authentication completed successfully"
            }
        else:
            return {
                "success": False,
                "error": "Authentication failed",
                "output": output[-500:]
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def complete_login_with_code_pty(code: str) -> dict:
    """Fallback pty-based callback handling."""
    try:
        master_fd, slave_fd = pty.openpty()
        process = subprocess.Popen(
            ["claude", "setup-token"],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            preexec_fn=os.setsid
        )
        os.close(slave_fd)

        output = ""
        start_time = time.time()
        timeout_secs = 60
        code_sent = False
        success = False

        while time.time() - start_time < timeout_secs:
            readable, _, _ = select.select([master_fd], [], [], 0.5)
            if readable:
                try:
                    chunk = os.read(master_fd, 4096).decode('utf-8', errors='replace')
                    output += chunk
                    if "Paste code here" in output and not code_sent:
                        time.sleep(1)
                        os.write(master_fd, (code + "\n").encode())
                        code_sent = True
                    if code_sent and ("signed in" in output.lower() or "successfully" in output.lower()):
                        success = True
                        break
                    if "error" in output.lower() and code_sent:
                        break
                except OSError:
                    break
            if process.poll() is not None:
                break

        try:
            os.close(master_fd)
        except OSError:
            pass
        try:
            process.terminate()
            process.wait(timeout=5)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass

        state = load_state()
        state["status"] = "completed" if success else "failed"
        state["completed_at"] = datetime.now().isoformat()
        save_state(state)

        if success:
            return {"success": True, "message": "Authentication completed successfully"}
        else:
            return {"success": False, "error": "Authentication failed", "output": output[-500:]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: claude-login-helper.py <start|status|callback> [code]"}))
        return

    command = sys.argv[1]

    if command == "status":
        result = check_auth_status()
        print(json.dumps(result))

    elif command == "start":
        result = start_login_flow()
        print(json.dumps(result))

    elif command == "callback":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Missing callback code"}))
            return
        code = sys.argv[2]
        result = complete_login_with_code(code)
        print(json.dumps(result))

    else:
        print(json.dumps({"error": f"Unknown command: {command}"}))


if __name__ == "__main__":
    main()
