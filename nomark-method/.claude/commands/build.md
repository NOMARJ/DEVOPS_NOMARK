---
description: "Execute next story from PRD with verification"
---

# Build Mode

Execute one story at a time with full verification.

## Process

### 1. Load Context

```
1. Read prd.json
2. Read progress.txt (Codebase Patterns section FIRST)
3. Check correct branch (from PRD branchName)
```

### 2. Pick Next Story

Select highest priority story where `passes: false`

### 3. Implement

- Focus on THIS story only
- Follow existing codebase patterns
- Keep changes minimal and focused

### 4. Verify

Run verification stack in order:

```sh
npm run typecheck    # Types must pass
npm run lint         # Lint must pass
npm test            # Tests must pass
```

For UI stories: Verify in browser

### 5. If Verification Passes

```
1. Commit: git commit -m "feat: [US-XXX] - Story Title"
2. Update prd.json: set passes: true
3. Append to progress.txt
```

### 6. Progress Report

Append to progress.txt:

```markdown
## [Date] - US-XXX

- What was implemented
- Files changed
- **Learnings:**
  - Patterns discovered
  - Gotchas encountered
  - Useful context

---
```

### 7. Pattern Consolidation

If you discovered a REUSABLE pattern, add to top of progress.txt:

```markdown
## Codebase Patterns
- [New pattern here]
```

### 8. Update CLAUDE.md

If you found something future iterations should know:
- Patterns specific to this module
- Gotchas or non-obvious requirements
- Dependencies between files

## Stop Conditions

**All stories complete:**
```
All stories have passes: true
→ Output: "COMPLETE - All stories implemented"
```

**Story incomplete:**
```
Verification fails or task too big
→ Output: "BLOCKED - [reason]"
→ Do NOT mark as passes: true
```

## Rules

- ONE story per build session
- ALWAYS run verification
- NEVER commit failing code
- ALWAYS update progress.txt
