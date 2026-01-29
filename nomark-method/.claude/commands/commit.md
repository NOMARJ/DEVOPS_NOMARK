---
description: "Stage, commit, and push changes"
---

# Commit

Stage and commit with verification.

## Process

### 1. Check Status

```sh
git status
git diff
```

Review what will be committed.

### 2. Verify Before Commit

```sh
npm run typecheck
npm run lint
npm test
```

All must pass.

### 3. Stage Files

Stage specific files (not `git add .`):

```sh
git add path/to/specific/file.ts
```

### 4. Commit

Use conventional commit format:

```sh
git commit -m "type: description"
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `refactor:` - Code change that neither fixes nor adds
- `docs:` - Documentation only
- `test:` - Adding/updating tests
- `chore:` - Maintenance, dependencies

**Examples:**
```
feat: add priority filter to task list
fix: resolve null pointer in user lookup
refactor: simplify authentication middleware
```

### 5. Push

```sh
git push -u origin branch-name
```

## Rules

- Verify passes BEFORE commit
- Descriptive commit message
- One logical change per commit
- Never commit secrets, .env files, or credentials
