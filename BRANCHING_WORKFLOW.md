# Git Branching Workflow

## Branch Structure

```
main       → Stable backup (manual merges only, doesn't deploy)
develop    → Working branch - auto-deploys to Railway
```

## Simple Daily Workflow

### 1. Start Working

```bash
# Make sure you're on develop
git checkout develop
git pull origin develop
```

### 2. Make Changes & Test Locally

```bash
# Make your changes
# ... edit files ...

# Test locally FIRST
python app.py
# Or however you run the app locally
# Make sure everything works!
```

### 3. Commit & Push to Railway

```bash
# Commit your changes
git add .
git commit -m "Feat: Your feature description"

# Push to GitHub → triggers Railway deployment
git push origin develop

# 🚀 Railway automatically deploys
# Wait for deployment to complete
# Test on Railway URL
```

### 4. If Railway Works → Mark as Stable

```bash
# When everything is tested and working on Railway:
git checkout main
git merge develop
git push origin main

# Back to develop for next work
git checkout develop
```

### 5. If Railway Breaks → Fix It

```bash
# Still on develop
# Fix the issue
# ... make fixes ...

# Test locally again
python app.py

# Commit and push
git commit -am "Fix: Issue description"
git push origin develop

# → Railway redeploys automatically
# → Test again on Railway
```

## Railway Configuration

### Current Setup
- **Branch**: `develop` (auto-deploys on every push)
- **Purpose**: Live testing environment
- **URL**: Your Railway app URL

### Important
- Railway **ONLY** deploys from `develop`
- `main` is just a stable backup, doesn't deploy anywhere
- Always test locally before pushing to `develop`

## Commit Message Convention

```
Type: Short description

Types:
- Feat: New feature
- Fix: Bug fix
- Docs: Documentation
- Refactor: Code restructuring
- Test: Adding tests
- Chore: Maintenance

Examples:
✅ Feat: Add ESCO skill normalization
✅ Fix: Resolve matching timeout on large datasets
✅ Docs: Update branching workflow
❌ fixed stuff
❌ changes
```

## Important Rules

### ✅ DO:
- Always test locally before pushing
- Work directly on `develop` for day-to-day changes
- Push to `develop` to deploy to Railway
- Merge to `main` when `develop` is stable
- Use clear commit messages

### ❌ DON'T:
- Push to `develop` without local testing
- Commit directly to `main`
- Push broken code to `develop` (Railway will deploy it!)
- Forget to pull before starting work

## Example: Full Development Flow

```bash
# Morning: Start working
git checkout develop
git pull origin develop

# Add new feature
# ... code ESCO integration ...

# Test locally
python app.py
# Everything works!

# Commit
git commit -am "Feat: Add ESCO skill normalization database"
git push origin develop

# → Railway deploys (wait ~2 minutes)
# → Test on Railway
# ✅ Works!

# Add mapper logic
# ... code mapper ...

# Test locally
python app.py
# Works locally!

# Commit and push
git commit -am "Feat: Add ESCO skill mapper with semantic matching"
git push origin develop

# → Railway deploys
# → Test on Railway
# ❌ Found a bug!

# Fix locally
# ... fix bug ...

# Test locally
python app.py
# Fixed!

# Commit fix
git commit -am "Fix: Handle null ESCO descriptions gracefully"
git push origin develop

# → Railway deploys
# → Test on Railway
# ✅ Everything works!

# End of day: Mark as stable
git checkout main
git merge develop
git push origin main
git checkout develop

# → develop continues to be your working branch
# → main has stable snapshot
```

## Quick Reference

```bash
# Check current branch
git branch

# Switch branches
git checkout develop
git checkout main

# See changes
git status
git diff

# Pull latest
git pull origin develop

# Commit shortcut (add all + commit)
git commit -am "Feat: Message"

# Push to Railway
git push origin develop

# Check recent history
git log --oneline -10

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Discard all uncommitted changes
git reset --hard  # ⚠️ Dangerous!
```

## Troubleshooting

### Railway Deploy Failed
```bash
# Check Railway logs for the error
# Fix the issue locally
# Test locally to confirm fix
git commit -am "Fix: Railway deployment issue"
git push origin develop
```

### Pushed Broken Code to develop
```bash
# Option 1: Quick fix
# ... fix the issue ...
git commit -am "Fix: Hotfix for broken deploy"
git push origin develop

# Option 2: Revert to last stable
git log --oneline -5  # Find last good commit
git revert <commit-hash>
git push origin develop
```

### Need to Match develop with main
```bash
# Reset develop to match main (nuclear option)
git checkout develop
git reset --hard main
git push --force origin develop
# ⚠️ Only do this if you're sure!
```

### Accidentally Committed to main
```bash
# Don't panic!
git log  # Find your commit hash

# Create a branch with your changes
git checkout -b develop-temp

# Reset main to origin
git checkout main
git reset --hard origin/main

# Merge your changes into develop
git checkout develop
git merge develop-temp
git push origin develop

# Delete temp branch
git branch -d develop-temp
```

## Pro Tips

1. **Always test locally first** - Don't use Railway as your testing environment
2. **Commit often** - Small commits are easier to debug than large ones
3. **Use descriptive messages** - "Fix bug" is useless, "Fix: Handle null competencies in matcher" is helpful
4. **Pull before you start** - Avoid merge conflicts
5. **Merge to main weekly** - Keep a stable reference point
6. **Don't fear mistakes** - Git can undo almost anything

## Current Branch Status

```bash
# Quick check what you're on
git branch
# * develop  ← You should usually see this
#   main
```
