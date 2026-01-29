# FlowMetrics DevOps Workflow

## The Complete Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: PLANNING & PRD DEVELOPMENT (Claude.ai - This Chat)                │
│                                                                             │
│  You + Claude brainstorm, design, and create PRDs                           │
│  → Export PRD to GitHub/local                                               │
│  → Claude.ai has memory of your project context                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 2: INTERACTIVE DEVELOPMENT (Claude Desktop / Windsurf + MCP)         │
│                                                                             │
│  Direct infrastructure access via DevOps MCP                                │
│  → Query databases, manage deployments, trigger workflows                   │
│  → Access your 100+ skills for patterns and guidance                        │
│  → Real-time coding with full context                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 3: AUTONOMOUS EXECUTION (DevOps Agent VM + Ralph)                    │
│                                                                             │
│  Overnight/background development from PRDs                                 │
│  → Triggered via Slack: /dev start feature-x                                │
│  → Ralph reads PRD, implements, creates PR                                  │
│  → Progress updates to Slack                                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 4: REVIEW & ITERATE (Back to Claude.ai or Desktop)                   │
│                                                                             │
│  Review PRs, discuss changes, refine                                        │
│  → Memory persists across sessions                                          │
│  → Context builds over time                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Stage 1: Claude.ai for Planning

### What Happens Here
- High-level architecture discussions
- PRD creation and refinement
- Feature brainstorming
- Technical decision making
- Code review discussions
- Problem solving

### Key Advantages
- **Memory**: Claude remembers your project context across conversations
- **No Setup**: Just chat, no tools to configure
- **Mobile**: Plan on the go from your phone
- **Artifacts**: Create documents, diagrams, code that can be exported
- **Projects**: Organize conversations by feature/epic

### PRD Development Flow

```
1. Start conversation: "Let's design the new client onboarding flow"
2. Discuss requirements, constraints, technical approach
3. Claude creates PRD artifact
4. Export PRD to:
   - GitHub (direct via artifact download)
   - Local project (copy/paste or download)
   - DevOps Agent repo (for autonomous pickup)
```

### PRD Template (Claude.ai creates these)

```markdown
# PRD: [Feature Name]

## Overview
[What and why]

## User Stories
- As a [user], I want [goal] so that [benefit]

## Technical Approach
[Architecture decisions from our discussion]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Tasks
- [ ] Task 1 (estimated: 2h)
- [ ] Task 2 (estimated: 1h)

## Dependencies
- Requires: [other features/services]

## Notes from Discussion
[Key decisions and context from Claude.ai chat]
```

## Connecting the Stages

### Claude.ai → GitHub (Manual Export)

After creating a PRD in Claude.ai:
1. Download the artifact
2. Commit to repo: `prds/feature-name/PRD.md`
3. Or use the MCP from Claude Desktop to push directly

### Claude.ai → DevOps Agent (Automated Pickup)

Option 1: **GitHub Trigger**
```
1. Push PRD to GitHub
2. n8n watches for new PRDs in /prds folder
3. Triggers DevOps Agent automatically
```

Option 2: **Slack Command**
```
1. Finish PRD in Claude.ai
2. In Slack: /dev start feature-name --prd "paste PRD here"
3. n8n receives, creates PRD file, triggers agent
```

Option 3: **Direct Webhook**
```
1. Claude.ai creates PRD
2. You trigger: curl -X POST n8n-webhook/new-prd -d @prd.md
3. Agent picks up and starts
```

## Stage Handoff Patterns

### Pattern 1: Planning Session → Overnight Build

```
MORNING (Claude.ai):
  "Let's design the new reporting dashboard"
  → Discuss requirements
  → Create PRD
  → Export to GitHub

EVENING (Slack):
  /dev start reporting-dashboard

OVERNIGHT (DevOps Agent):
  → Ralph implements from PRD
  → Creates PR
  → Posts to Slack when done

NEXT MORNING (Claude.ai or Desktop):
  → Review PR
  → Discuss refinements
  → Merge or iterate
```

### Pattern 2: Interactive Development with Planning Breaks

```
CLAUDE DESKTOP (coding):
  Working on feature, hit a design question

CLAUDE.AI (planning):
  "I'm building X and need to decide between A and B..."
  → Discuss tradeoffs
  → Make decision
  → Document in PRD

BACK TO DESKTOP (coding):
  Continue with clear direction
```

### Pattern 3: Mobile Planning → Desktop Execution

```
COMMUTE (Claude.ai mobile):
  "Let's sketch out the API for the new integration"
  → High-level design
  → Create PRD artifact

AT DESK (Claude Desktop):
  → Open project
  → PRD synced via GitHub
  → Implement with MCP tools available
```

## Memory Continuity

Claude.ai maintains context about:
- Your FlowMetrics architecture
- Technical decisions made
- Naming conventions
- Past features built
- Your preferences

This means:
- No re-explaining your stack each session
- Consistent architectural recommendations
- Builds on previous discussions
- Understands your codebase patterns

## Integration Points

### 1. PRD Sync

```
Claude.ai PRD → GitHub → DevOps Agent
                      ↘
                        Claude Desktop (MCP reads PRD)
```

### 2. Status Updates

```
DevOps Agent progress → Slack → You review
                              ↘
                                Discuss in Claude.ai
```

### 3. Skill Evolution

```
Claude.ai discussion → New pattern identified
                     ↓
              Add to skills repo
                     ↓
         Available in MCP + Agent
```

## Quick Reference

| Task | Best Tool |
|------|-----------|
| Brainstorm feature | Claude.ai |
| Write PRD | Claude.ai |
| Design architecture | Claude.ai |
| Interactive coding | Claude Desktop + MCP |
| Query production data | Claude Desktop + MCP |
| Overnight implementation | DevOps Agent |
| Code review discussion | Claude.ai |
| Quick fixes | Claude Desktop |
| Mobile planning | Claude.ai app |

## Example Session Flow

```
YOU (Claude.ai): "I need to add multi-currency support to FlowMetrics"

CLAUDE: Let's break this down...
- Database schema changes
- API modifications  
- UI updates
[Discussion continues, PRD takes shape]

CLAUDE: Here's the PRD artifact. Want me to create the migration 
        SQL and API types now?

YOU: Yes, and let's also think about the rollout strategy...

[PRD finalized]

YOU: Great, I'll push this to GitHub and have Ralph work on it tonight.

--- LATER IN SLACK ---

YOU: /dev start multi-currency

AGENT: 🚀 Starting work on multi-currency...
       📋 Found PRD at prds/multi-currency/PRD.md
       🔧 Beginning implementation...

--- NEXT MORNING ---

AGENT: ✅ Completed! PR #142 ready for review
       - Added currency_code to transactions table
       - Updated API endpoints
       - Added currency selector component

YOU (Claude.ai): Let's review the PR together. Here's what Ralph built...

CLAUDE: Looking at the changes... [detailed review]
        I'd suggest we also add exchange rate caching...

[Iterate until perfect]
```

## Setup Checklist

- [ ] Claude.ai project created for FlowMetrics
- [ ] Memory enabled (it learns your context over time)
- [ ] PRD template saved in skills repo
- [ ] GitHub repo structure includes `/prds` folder
- [ ] n8n workflow watches for new PRDs (optional auto-trigger)
- [ ] Slack commands configured
- [ ] DevOps Agent deployed and tested
