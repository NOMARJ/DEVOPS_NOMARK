# PRD Development Skill

> Creating well-structured Product Requirement Documents through conversation

## Overview

This skill guides PRD creation during planning conversations in Claude.ai. PRDs created here feed into the DevOps Agent for autonomous implementation.

## When to Use

- Starting a new feature
- Planning a refactor
- Designing an integration
- Documenting technical decisions

## PRD Structure

### Standard PRD Template

```markdown
# PRD: [Feature Name]

**Status**: Draft | Ready | In Progress | Complete
**Author**: [Your name]
**Created**: [Date]
**Target**: [Sprint/Release]

## 1. Overview

### Problem Statement
[What problem are we solving?]

### Proposed Solution
[High-level approach]

### Success Metrics
- [Metric 1]
- [Metric 2]

## 2. User Stories

### Primary User Flow
As a [user type], I want [action] so that [benefit].

### Additional Stories
- As a [user], I want...
- As an [admin], I want...

## 3. Technical Design

### Architecture
[Describe the technical approach]

### Database Changes
```sql
-- New tables or modifications
```

### API Changes
```typescript
// New or modified endpoints
```

### UI Components
- [ ] Component 1
- [ ] Component 2

## 4. Acceptance Criteria

### Must Have
- [ ] Criterion 1
- [ ] Criterion 2

### Should Have
- [ ] Criterion 3

### Nice to Have
- [ ] Criterion 4

## 5. Implementation Tasks

### Phase 1: Foundation
- [ ] Task 1 (~2h)
- [ ] Task 2 (~1h)

### Phase 2: Core Features
- [ ] Task 3 (~4h)

### Phase 3: Polish
- [ ] Task 4 (~1h)

## 6. Dependencies

### Requires
- [Other feature/service]

### Blocks
- [What this unblocks]

## 7. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Risk 1 | High | Mitigation approach |

## 8. Discussion Notes

### Key Decisions
- Decision 1: [Context and rationale]
- Decision 2: [Context and rationale]

### Open Questions
- [ ] Question 1
- [ ] Question 2

### References
- [Link to related discussion]
- [Link to design doc]
```

## PRD Conversation Flow

### Phase 1: Problem Definition
```
Questions to explore:
- What problem are we solving?
- Who experiences this problem?
- How do they currently work around it?
- What's the impact of not solving it?
```

### Phase 2: Solution Design
```
Questions to explore:
- What are the possible approaches?
- What are the tradeoffs?
- What's the simplest solution that works?
- How does this fit with existing architecture?
```

### Phase 3: Technical Planning
```
Questions to explore:
- What database changes are needed?
- What API endpoints?
- What UI components?
- What are the edge cases?
```

### Phase 4: Task Breakdown
```
Questions to explore:
- What's the logical order of implementation?
- What can be parallelized?
- What are the risky parts?
- How long will each part take?
```

## FlowMetrics-Specific Sections

For FlowMetrics PRDs, also include:

### Multi-Tenant Considerations
```markdown
## Multi-Tenant Impact

### RLS Policies Needed
- [ ] Table X needs client_id filter

### Client Isolation
- [ ] Data properly scoped
- [ ] No cross-client leakage

### Per-Client Configuration
- [ ] Feature flag needed?
- [ ] Client-specific settings?
```

### Data Processing Considerations
```markdown
## Data Processing Impact

### Platform Schema Changes
- [ ] Asgard mapping updates
- [ ] Netwealth mapping updates
- [ ] Hub24 mapping updates

### Validation Rules
- [ ] New validation needed?
- [ ] Quality scoring impact?

### Report Impact
- [ ] Existing reports affected?
- [ ] New reports needed?
```

## Handoff to DevOps Agent

### PRD Ready Checklist
Before marking a PRD as "Ready" for autonomous implementation:

- [ ] All acceptance criteria are specific and testable
- [ ] Tasks are broken down to <4 hour chunks
- [ ] Database changes have explicit SQL
- [ ] API changes have TypeScript types
- [ ] No open questions remain
- [ ] Dependencies are met or noted

### PRD File Location
```
repo/
└── prds/
    └── feature-name/
        ├── PRD.md           # Main PRD document
        ├── schema.sql       # Database changes (optional)
        ├── types.ts         # Type definitions (optional)
        └── mockup.png       # UI mockups (optional)
```

### Triggering Implementation

Option 1: Slack command
```
/dev start feature-name
```

Option 2: GitHub push triggers n8n

Option 3: Manual agent start
```bash
ssh devops-agent
./run-task.sh --prd prds/feature-name/PRD.md
```

## Example PRD Creation Session

```
USER: I want to add a feature where clients can export their data to Excel 
      with custom date ranges.

CLAUDE: Good feature idea. Let me understand the requirements...

1. Which data should be exportable?
   - Flow data (transactions)?
   - Summary reports?
   - Raw platform data?

USER: Flow data primarily, with the option to include summaries.

CLAUDE: And for date ranges:
- Preset options (This month, Last quarter, YTD)?
- Custom date picker?
- Both?

USER: Both - presets for convenience, custom for flexibility.

CLAUDE: Here's what I'm thinking for the technical approach:

**Backend:**
- New API endpoint: POST /api/export/flows
- Accepts: { startDate, endDate, includesSummary, format: 'xlsx' }
- Uses existing flow query with date filters
- Generates Excel via xlsx library (already in stack)

**Frontend:**
- New ExportModal component
- Date range picker (reuse from reports)
- Format selector (xlsx for now, csv later)
- Progress indicator for large exports

Does this align with what you're envisioning?

USER: Yes, but we should also consider file size limits for large date ranges.

CLAUDE: Good call. Let's add:
- Row limit (e.g., 100k rows)
- Warning when approaching limit
- Option to split into multiple files
- Background job for very large exports

Let me create the full PRD with these details...

[Creates PRD artifact]

Ready for review. Should I also draft the database migration 
and TypeScript types?
```

## Tips for Good PRDs

1. **Be Specific**: "User can filter by date" → "User can select start and end dates using a date picker, with preset options for common ranges"

2. **Include Examples**: Show sample data, API responses, UI states

3. **Think About Errors**: What happens when things go wrong?

4. **Consider Scale**: Will this work with 10x the data?

5. **Note Assumptions**: What are we assuming that might not be true?

6. **Link Context**: Reference related PRDs, discussions, or code
