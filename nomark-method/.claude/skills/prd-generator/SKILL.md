---
name: prd-generator
description: "Generate a PRD for a new feature. Creates atomic user stories ready for execution."
---

# PRD Generator

Create detailed Product Requirements Documents with atomic, executable user stories.

## Process

### 1. Clarify Requirements

Ask 3-5 essential questions with lettered options:

```
1. What is the primary goal?
   A. Option 1
   B. Option 2
   C. Option 3
   D. Other: [specify]

2. Who is the target user?
   A. New users
   B. Existing users
   C. All users
   D. Admin users
```

User can respond "1A, 2C" for speed.

### 2. Generate PRD

#### Structure

```markdown
# PRD: [Feature Name]

## Overview
[Brief description of feature and problem it solves]

## Goals
- Goal 1
- Goal 2

## User Stories

### US-001: [Title]
**Description:** As a [user], I want [X] so that [Y].

**Acceptance Criteria:**
- [ ] Specific criterion 1
- [ ] Specific criterion 2
- [ ] Typecheck passes
- [ ] [For UI] Verify in browser

### US-002: [Title]
...

## Functional Requirements
- FR-1: The system must [X]
- FR-2: When [event], the system must [Y]

## Non-Goals
- What this feature will NOT include

## Technical Notes
- Constraints or dependencies
- Existing components to reuse

## Success Metrics
- How success is measured
```

### 3. Story Requirements

Each story MUST be:
- **Atomic** - Completable in one session
- **Ordered** - Dependencies first (schema → backend → frontend)
- **Verifiable** - Concrete acceptance criteria

**Right-sized:**
- Add database column
- Add UI component
- Update server action

**Too big (split):**
- "Build the dashboard"
- "Add authentication"

### 4. Output

Save to `tasks/prd-[feature-name].md`

Create prd.json for execution:

```json
{
  "project": "ProjectName",
  "branchName": "feature/[name]",
  "description": "[description]",
  "userStories": [
    {
      "id": "US-001",
      "title": "[title]",
      "description": "[description]",
      "acceptanceCriteria": ["..."],
      "priority": 1,
      "passes": false,
      "notes": ""
    }
  ]
}
```

## DO NOT

- Start implementing
- Create vague stories
- Skip the clarifying questions
- Create stories that can't be verified
