---
description: "Enter plan mode - explore codebase, design solution before implementing"
---

# Plan Mode

Design the solution before writing code.

## Process

### 1. Understand the Request
- What is the user asking for?
- What problem does this solve?
- What are the constraints?

### 2. Explore the Codebase
Use these tools (NO editing):
- `Read` - Read relevant files
- `Glob` - Find files by pattern
- `Grep` - Search code content
- `Task(Explore)` - Deep exploration

Answer:
- What existing code handles similar functionality?
- What patterns are used in this codebase?
- What are the touch points for this feature?

### 3. Design the Approach

Document:
- **Problem Statement** - What we're solving
- **Proposed Approach** - How we'll solve it
- **Files to Modify** - What changes
- **Files to Create** - What's new
- **Key Decisions** - Tradeoffs made
- **Test Strategy** - How we verify

### 4. Break Into Stories

Each story must be:
- **Atomic** - One focused change
- **Ordered** - Dependencies first (schema → backend → frontend)
- **Verifiable** - Concrete acceptance criteria

### 5. Get Approval

Present the plan, then use `ExitPlanMode` for user approval.

## Plan Template

```markdown
# Implementation Plan: [Feature]

## Problem Statement
[What we're solving and why]

## Research Findings
- Found existing [X] at `path/file.ts:123`
- Pattern used: [describe]

## Proposed Approach
[High-level description]

## Implementation Steps

### Step 1: [Title]
- Modify `file1.ts` to add [X]
- Create `file2.ts` for [Y]

### Step 2: [Title]
...

## Files Affected
- `src/feature/index.ts` - Main implementation
- `tests/feature.test.ts` - Unit tests

## Key Decisions
1. **[What]** - Rationale: [Why]

## Test Strategy
- Unit tests for [X]
- Integration test for [Y]
- Browser verification for [Z]
```

## DO NOT in Plan Mode

- Edit files
- Write files
- Run commands (except read-only)

Plan mode is for thinking, not doing.
