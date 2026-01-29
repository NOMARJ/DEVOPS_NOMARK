# NOMARK Method

**Architecture First. Outcomes Over Hype. Simple Wins.**

A development methodology that combines the best of autonomous AI loops with deliberate planning, optimized for teams that value elegance over complexity.

---

## Philosophy

> "Simple and efficient like Apple is always going to win."

NOMARK is built on three pillars:

1. **Architecture First** - Think before you code. A good plan executed beats perfect code improvised.
2. **Outcomes Over Hype** - Ship what matters. No feature creep, no over-engineering, no cargo cult.
3. **Simple Wins** - The best code is code you don't write. The best abstraction is no abstraction.

---

## The NOMARK Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         NOMARK METHOD                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. THINK        2. PLAN         3. BUILD        4. VERIFY      │
│  ───────────     ──────────      ──────────      ──────────     │
│  First           Architecture    Atomic          Feedback       │
│  Principles      & Stories       Execution       Loops          │
│                                                                  │
│     ↓                ↓               ↓               ↓          │
│  Question         Small,          One task,       Tests,        │
│  everything       verifiable      fresh context   typecheck,    │
│                   stories                         browser       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: THINK (First Principles)

Before touching code, challenge assumptions.

**Use when:**
- Starting a new feature
- "That's how it's always done"
- Existing solution feels wrong
- Need breakthrough, not increment

**Process:**
1. Define the problem (what are we actually solving?)
2. Surface assumptions (what do we take for granted?)
3. Question each one (physics/logic or just convention?)
4. Identify fundamentals (what's truly non-negotiable?)
5. Rebuild from scratch (if we started today...)

**Output:** Clear problem statement with validated constraints.

**Command:** `/think` or `/first-principles`

---

## Phase 2: PLAN (Architecture & Stories)

Design the solution before implementation.

### For Complex Features: Use Plan Mode

1. Enter plan mode (shift+tab twice, or `/plan`)
2. Explore the codebase - understand existing patterns
3. Design the approach - files to modify, patterns to follow
4. Break into atomic stories - each completable in one session
5. Get approval, then execute

### Story Requirements

Each story must be:
- **Atomic** - One focused change, completable in one context window
- **Ordered** - Schema → Backend → Frontend (dependencies first)
- **Verifiable** - Concrete acceptance criteria, not vague

**Right-sized:**
```
✓ Add status column to tasks table
✓ Add filter dropdown to task list
✓ Update server action with validation
```

**Too big (split these):**
```
✗ Build the dashboard
✗ Add authentication
✗ Refactor the API
```

**Rule:** If you can't describe it in 2-3 sentences, it's too big.

### PRD Format

```json
{
  "project": "ProjectName",
  "branchName": "feature/feature-name",
  "description": "What and why",
  "userStories": [
    {
      "id": "US-001",
      "title": "Clear, specific title",
      "description": "As a [user], I want [X] so that [Y]",
      "acceptanceCriteria": [
        "Specific, verifiable criterion",
        "Another criterion",
        "Typecheck passes",
        "Tests pass"
      ],
      "priority": 1,
      "passes": false
    }
  ]
}
```

**Command:** `/plan` or `/prd`

---

## Phase 3: BUILD (Atomic Execution)

Execute one story at a time with fresh context.

### The Build Loop

```
For each story where passes: false:
  1. Read progress.txt (Codebase Patterns section first)
  2. Implement the single story
  3. Run verification (typecheck, lint, test)
  4. If passes:
     - Commit with message: feat: [US-001] - Story Title
     - Update story to passes: true
     - Append learnings to progress.txt
  5. Move to next story
```

### Memory Management

Memory persists across sessions via:
- **Git history** - Commits from previous work
- **progress.txt** - Learnings and context
- **CLAUDE.md** - Mistakes to avoid, patterns to follow
- **prd.json** - What's done, what's remaining

### Pattern Consolidation

When you discover something reusable, add to progress.txt:

```markdown
## Codebase Patterns
- Use `sql<number>` template for aggregations
- Always use `IF NOT EXISTS` for migrations
- Export types from actions.ts for UI components
```

**Command:** `/build` or `/implement`

---

## Phase 4: VERIFY (Feedback Loops)

Verification is non-negotiable. It's the difference between 1x and 3x quality.

### Verification Stack

```
┌─────────────────────────────────────┐
│  Layer 1: Static Analysis           │
│  - Typecheck (npm run typecheck)    │
│  - Lint (npm run lint)              │
├─────────────────────────────────────┤
│  Layer 2: Automated Tests           │
│  - Unit tests                       │
│  - Integration tests                │
├─────────────────────────────────────┤
│  Layer 3: Browser Verification      │
│  - Visual confirmation              │
│  - User flow testing                │
├─────────────────────────────────────┤
│  Layer 4: Simplification            │
│  - Code-simplifier agent            │
│  - Remove accidental complexity     │
└─────────────────────────────────────┘
```

### UI Stories MUST Include

```
"Verify in browser - navigate to page, confirm behavior"
```

### After Each PR

Run code-simplifier to clean up:
- Reduce complexity
- Improve readability
- Remove redundancy
- Keep behavior identical

**Commands:** `/verify`, `/simplify`, `/test-and-fix`

---

## CLAUDE.md: Continuous Learning

Every mistake is a learning opportunity.

```markdown
# CLAUDE.md

## Project Overview
[What this project does]

## Workflow
1. Make changes
2. Run typecheck
3. Run tests
4. Lint before commit

## Code Style
- Prefer `type` over `interface`
- Never use `enum` (use string unions)
- Handle errors explicitly

## DO NOT
- Use `any` without approval
- Skip error handling
- Commit without tests
- Make breaking changes without discussion

## Patterns
[Add as you discover them]
```

**Tag @.claude in PR reviews to add learnings.**

---

## Slash Commands

| Command | Purpose |
|---------|---------|
| `/think` | First principles analysis |
| `/plan` | Enter plan mode, design solution |
| `/prd` | Generate PRD for feature |
| `/build` | Execute next story |
| `/verify` | Run full verification stack |
| `/simplify` | Clean up recent code |
| `/commit` | Stage, commit, push |
| `/pr` | Create pull request |

---

## Agents

| Agent | When to Use |
|-------|-------------|
| `code-architect` | Design reviews, major decisions |
| `code-simplifier` | After implementation, clean up |
| `verify-app` | Before PR, full verification |
| `code-explorer` | Understanding unfamiliar code |

---

## Parallel Execution

For large features, run multiple sessions:

1. **Terminal tabs 1-5** - Local Claude sessions, each on own git checkout
2. **Browser sessions** - Additional capacity via claude.ai
3. **System notifications** - Know when a session needs input

Each session works on different stories. Merge via git.

**Avoid conflicts:** Each session = own checkout (not branches in same repo).

---

## Project Structure

```
project/
├── CLAUDE.md           # Project instructions (mistakes, patterns)
├── prd.json            # Current feature PRD
├── progress.txt        # Learnings from iterations
├── .claude/
│   ├── agents/         # Specialized agents
│   ├── commands/       # Slash commands
│   ├── skills/         # Domain knowledge
│   └── settings.json   # Permissions, hooks
└── docs/
    └── plans/          # First principles analyses
```

---

## Anti-Patterns

### Don't Do This

| Anti-Pattern | Why It Fails |
|--------------|--------------|
| Big stories | Run out of context, produce broken code |
| Skip verification | 1x quality instead of 3x |
| Ignore CLAUDE.md | Repeat same mistakes |
| Over-engineer | More code = more bugs |
| Skip planning | Rework costs 10x more |

### Do This Instead

| Pattern | Why It Works |
|---------|--------------|
| Atomic stories | Complete in one session |
| Verify everything | Catch errors early |
| Update CLAUDE.md | Learn continuously |
| Simple solutions | Less to maintain |
| Plan first | Build right first time |

---

## Getting Started

### 1. Copy NOMARK to Your Project

```bash
cp -r nomark-method/.claude your-project/
cp nomark-method/templates/CLAUDE.md your-project/
```

### 2. Customize CLAUDE.md

Add your project's:
- Tech stack and commands
- Code conventions
- Common mistakes to avoid

### 3. Start With /think

Before building anything new:
```
/think - What problem are we really solving?
```

### 4. Plan Before Build

```
/plan - Design the solution
/prd - Break into atomic stories
```

### 5. Execute With Verification

```
/build - Implement one story
/verify - Confirm it works
/simplify - Clean up
/commit - Ship it
```

---

## Summary

```
NOMARK = Think + Plan + Build + Verify

Think   → First principles, challenge assumptions
Plan    → Architecture, atomic stories
Build   → One task, fresh context, verification
Verify  → Tests, typecheck, browser, simplify

Memory  → CLAUDE.md + progress.txt + git history
Quality → Verification loops = 3x improvement
Speed   → Parallel sessions, slash commands
```

**Simple. Efficient. Wins.**
