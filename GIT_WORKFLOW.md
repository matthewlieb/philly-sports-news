# Git Workflow Best Practices

## Pre-Commit Checklist

### 1. Clean Up Repository
- ✅ Remove `__pycache__/` directories
- ✅ Remove `.pyc` files
- ✅ Remove `.DS_Store` files (macOS)
- ✅ Remove log files
- ✅ Update `.gitignore` to prevent future commits of these files

### 2. Review Changes
- ✅ Check what files have been modified
- ✅ Review new files to ensure they should be committed
- ✅ Remove any temporary or test files

### 3. Commit Strategy
- ✅ Group related changes into logical commits
- ✅ Write clear, descriptive commit messages
- ✅ Don't commit sensitive data (API keys, passwords)

## Recommended Git Workflow

### Step 1: Clean Up
```bash
# Remove Python cache files
find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null
find . -type f -name "*.pyc" -delete

# Remove OS files
find . -name ".DS_Store" -delete

# Remove log files
rm -f *.log /tmp/flask_output.log
```

### Step 2: Check Status
```bash
git status
```

### Step 3: Stage Changes
```bash
# Stage all changes (or specific files)
git add .

# Or stage specific files
git add app.py sbNationScrape.py requirements.txt
git add scrapers/ utils/
git add templates/
```

### Step 4: Commit
```bash
# Write descriptive commit message
git commit -m "Add caching system and RSS feed integration

- Implement Flask-Caching for all routes (1 hour cache)
- Migrate SB Nation sites to RSS feeds with fallback
- Add article quality filtering and merging system
- Add dynamic source names (no hardcoded text)
- Improve article enhancement with complete data fetching
- Update requirements.txt with Flask-Caching and feedparser"
```

### Step 5: Push
```bash
git push origin main
```

## Commit Message Best Practices

### Format
```
Short summary (50 chars or less)

More detailed explanation if needed. Wrap at 72 characters.
Explain what and why, not how.

- Bullet points for multiple changes
- Reference issues if applicable (#123)
```

### Examples
```
✅ Good:
"Add caching system for improved performance"

"Implement RSS feed integration for SB Nation sites

- Add RSS scraper with fallback support
- Migrate Liberty Ballers, Bleeding Green Nation, etc.
- Improve reliability over web scraping"

❌ Bad:
"fix stuff"
"updates"
"changes"
```

## What to Commit

### ✅ Should Commit
- Source code files (`.py`, `.html`, `.css`, `.js`)
- Configuration files (`requirements.txt`, `Procfile`)
- Documentation (`.md` files)
- Templates and static assets
- `.gitignore`, `.gitattributes`

### ❌ Should NOT Commit
- `__pycache__/` directories
- `.pyc` files
- `.DS_Store` files
- Log files (`.log`)
- Environment files (`.env`)
- API keys or secrets
- Temporary files
- IDE settings (`.vscode/`, `.idea/`)

## Branch Strategy (Optional)

For larger projects, consider:
- `main` - Production-ready code
- `develop` - Development branch
- `feature/*` - Feature branches

For this project, `main` branch is sufficient.

## Before Pushing Checklist

- [ ] Code is tested and working
- [ ] No sensitive data in commits
- [ ] `.gitignore` is up to date
- [ ] Commit messages are clear
- [ ] Related changes are grouped together
- [ ] No large binary files accidentally added

