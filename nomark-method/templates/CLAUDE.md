# CLAUDE.md

> Update this file whenever Claude does something incorrectly. Every mistake is a learning opportunity.

## Project Overview

<!-- Describe your project -->

## Tech Stack

<!-- List your technologies -->

## Workflow

1. Make changes
2. Run typecheck: `npm run typecheck`
3. Run tests: `npm test`
4. Lint: `npm run lint`
5. Before PR: Full verification

## Code Style

- Prefer `type` over `interface`
- Never use `enum` (use string literal unions)
- Use descriptive variable names
- Keep functions small and focused
- Handle errors explicitly, don't swallow them

## DO NOT

<!-- Add mistakes as they happen -->

- Use `any` type without explicit approval
- Skip error handling
- Commit without running tests
- Make breaking API changes without discussion
- Over-engineer simple solutions

## Codebase Patterns

<!-- Add patterns as you discover them -->

## Commands Reference

```sh
npm run dev          # Start development server
npm run build        # Production build
npm run typecheck    # Type checking
npm run test         # Run tests
npm run lint         # Lint all files
```

---

_Tag @.claude in PR reviews to add learnings._
