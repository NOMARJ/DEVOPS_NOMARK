---
description: "Create pull request with proper description"
---

# Create Pull Request

Create a well-documented PR.

## Process

### 1. Ensure Ready

- All stories in PRD are `passes: true`
- All verification passes
- Branch is pushed to remote

### 2. Create PR

```sh
gh pr create --title "feat: Feature Title" --body "$(cat <<'EOF'
## Summary

Brief description of what this PR does and why.

## Changes

- Change 1
- Change 2
- Change 3

## User Stories Completed

- [x] US-001: Story title
- [x] US-002: Story title

## Testing

- [x] Typecheck passes
- [x] All tests pass
- [x] Browser verification (for UI changes)

## Screenshots (if UI changes)

[Add screenshots here]

## Notes for Reviewers

Any context reviewers should know.

---

Generated with NOMARK method
EOF
)"
```

### 3. Report

Output the PR URL for the user.

## PR Title Format

```
type: Brief description

Examples:
feat: Add task priority system
fix: Resolve authentication timeout
refactor: Simplify query builder
```

## Before Creating PR

Checklist:
- [ ] All stories complete
- [ ] Verification passes
- [ ] Code simplified
- [ ] progress.txt updated
- [ ] CLAUDE.md updated (if learnings)
