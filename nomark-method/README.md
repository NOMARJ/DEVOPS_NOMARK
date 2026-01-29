# NOMARK Method

> Architecture First. Outcomes Over Hype. Simple Wins.

A development methodology combining the best of autonomous AI loops (Ralph) with deliberate planning (Boris Cherny's workflow), optimized for teams that value elegance over complexity.

## Quick Start

### 1. Copy to Your Project

```bash
cp -r nomark-method/.claude your-project/
cp nomark-method/templates/CLAUDE.md your-project/
```

### 2. Customize CLAUDE.md

Add your project's tech stack, conventions, and common mistakes.

### 3. Use the Flow

```
/think    → Question assumptions, find fundamentals
/plan     → Design solution, break into stories
/build    → Execute one story with verification
/verify   → Run full verification stack
/simplify → Clean up code
/commit   → Ship it
/pr       → Create pull request
```

## The NOMARK Flow

```
THINK → PLAN → BUILD → VERIFY
  ↓       ↓       ↓       ↓
Question  Atomic  One    Tests,
assump-   stories task,  type-
tions     in     fresh   check,
          order   ctx    browser
```

## Key Principles

### From Ralph
- **Atomic stories** - Small enough to complete in one session
- **Fresh context** - Each task starts clean
- **Memory persistence** - Git + progress.txt + CLAUDE.md
- **Pattern consolidation** - Learn from each iteration

### From Boris Cherny
- **Plan first** - Iterate on plan, then auto-accept
- **Verification loops** - 2-3x quality improvement
- **CLAUDE.md** - Continuous learning from mistakes
- **Simplify after** - Clean up with code-simplifier

### NOMARK Philosophy
- **Architecture first** - Think before code
- **Outcomes over hype** - Ship what matters
- **Simple wins** - Best code is code you don't write

## What's Included

### Slash Commands
| Command | Purpose |
|---------|---------|
| `/think` | First principles analysis |
| `/plan` | Enter plan mode |
| `/build` | Execute next story |
| `/verify` | Full verification |
| `/simplify` | Clean up code |
| `/commit` | Stage and commit |
| `/pr` | Create pull request |

### Agents
| Agent | Purpose |
|-------|---------|
| `code-architect` | Design reviews |
| `code-simplifier` | Post-implementation cleanup |
| `verify-app` | Full verification |
| `code-explorer` | Codebase understanding |

### Templates
- `CLAUDE.md` - Project instructions
- `prd.json` - PRD format
- `progress.txt` - Learning persistence

## Documentation

- [NOMARK.md](./NOMARK.md) - Full methodology documentation
- [templates/](./templates/) - Template files

### DevOps Setup (Azure)

For running NOMARK as an autonomous DevOps system:

- [NOMARK_DEVOPS_ARCHITECTURE.md](./docs/NOMARK_DEVOPS_ARCHITECTURE.md) - System architecture
- [NOMARK_DEVOPS_SETUP.md](./docs/NOMARK_DEVOPS_SETUP.md) - Setup guide
- [SLACK_SETUP.md](./docs/SLACK_SETUP.md) - Slack integration

### Scripts

| Script | Purpose |
|--------|---------|
| `scripts/azure-deploy.sh` | Deploy Azure resources (VM, PostgreSQL, Key Vault) |
| `scripts/setup-vm.sh` | Configure VM with required packages |
| `scripts/init-knowledge-base.sh` | Initialize PostgreSQL schema |
| `scripts/slack-bot.py` | Slack bot for task dispatch |

## Sources

Based on:
- [Ralph](https://github.com/snarktank/ralph) - Autonomous PRD-driven loops
- [Boris Cherny's Workflow](https://venturebeat.com/technology/the-creator-of-claude-code-just-revealed-his-workflow-and-developers-are) - Claude Code creator's setup

---

**Simple. Efficient. Wins.**
