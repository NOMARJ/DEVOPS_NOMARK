---
description: "Run full verification stack - typecheck, lint, test, browser"
---

# Verify

Run the complete verification stack.

## Verification Layers

### Layer 1: Static Analysis

```sh
npm run typecheck
npm run lint
```

- All type errors must be resolved
- All lint warnings must be addressed
- No compilation errors

### Layer 2: Automated Tests

```sh
npm test
```

- All tests must pass
- Check for skipped tests that should run
- Review test coverage if available

### Layer 3: Browser Verification (for UI changes)

1. Start the application
2. Navigate to affected pages
3. Test the specific feature
4. Test related features that might be affected
5. Check for console errors

### Layer 4: Edge Cases

- Test with invalid inputs
- Test boundary conditions
- Test error handling paths

## Report Format

```markdown
## Verification Report

### Summary
[PASS/FAIL] - Brief explanation

### Static Analysis
- Typecheck: [PASS/FAIL]
- Lint: [PASS/FAIL]

### Tests
- Unit: [X/Y passed]
- Integration: [X/Y passed]

### Browser (if applicable)
- Feature works: [YES/NO]
- Console errors: [NONE/LIST]

### Issues Found
1. [Issue description]
   - File: `path/to/file.ts:123`
   - Fix: [Suggested fix]

### Recommendations
- [Any follow-up actions needed]
```

## Pass Criteria

All must be true:
- [ ] Typecheck passes
- [ ] Lint passes
- [ ] All tests pass
- [ ] Browser verification passes (for UI)
- [ ] No console errors

## If Verification Fails

1. Report the specific failure
2. Do NOT commit
3. Fix the issue
4. Re-run verification
5. Only proceed when all pass
