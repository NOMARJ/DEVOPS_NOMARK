---
description: "Simplify recently written code without changing behavior"
---

# Simplify

Clean up code after implementation.

## Purpose

Review recently modified code and simplify it WITHOUT changing functionality.

## Process

### 1. Identify Recent Changes

```sh
git diff HEAD~1
```

Or: Review files from the last story implemented.

### 2. Look For

**Complexity to reduce:**
- Nested conditionals
- Deeply nested structures
- Unnecessary abstractions
- Complex expressions

**Readability to improve:**
- Unclear variable names
- Long functions
- Commented-out code
- Dense logic

**Redundancy to remove:**
- Dead code
- Duplicate logic
- Unnecessary type assertions
- Unused imports

### 3. Make Simplifications

Apply changes that:
- Reduce cognitive load
- Make code more obvious
- Remove unnecessary layers

### 4. Verify

```sh
npm run typecheck
npm test
```

Behavior MUST remain identical.

### 5. Report

```markdown
## Simplification Report

### Files Modified
- `path/to/file.ts`

### Changes Made
1. Simplified nested conditional in `functionName`
2. Extracted repeated logic to `helperFunction`
3. Removed unused import

### Before/After Example
```typescript
// Before
if (x) {
  if (y) {
    if (z) { ... }
  }
}

// After
if (x && y && z) { ... }
```

### Verification
- Typecheck: PASS
- Tests: PASS
```

## Rules

**DO:**
- Simplify
- Clarify
- Remove redundancy
- Run tests after changes

**DO NOT:**
- Add features
- Change behavior
- Add dependencies
- Refactor unrelated code

## The Goal

Code that reads like well-written prose. No clever tricks. No unnecessary abstraction. Just clear, obvious, simple code.
