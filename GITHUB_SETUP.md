# 🚀 GitHub Setup & Workflow

**Date** : 2026-05-02  
**Status** : Ready for repository creation  
**Scope** : Complete backup + version control

---

## 📋 STEP 1: CREATE GITHUB REPOSITORY

### On GitHub.com

1. Go to https://github.com/new
2. Create repository:
   ```
   Name: color-communes
   Description: Telegram bot mapping French communes via GPX tracking
   Visibility: Public or Private (your choice)
   Initialize with: (leave empty, we'll push existing)
   ```

3. Get the repository URL:
   ```
   https://github.com/YOUR_USERNAME/color-communes.git
   ```

---

## 📥 STEP 2: INITIALIZE GIT LOCALLY

### Commands to run in X:\color-communes\

```bash
# Initialize git repository
git init

# Add all files (respecting .gitignore)
git add .

# Create initial commit
git commit -m "Initial commit: Phase 8 complete + Phase 9/10 architecture

- Infrastructure: Docker setup + SMB mount
- Code: Main bot + all services (production/)
- Config: Docker compose + Dockerfile
- Scripts: Batch import + utilities
- Documentation: Complete architecture + workflows
- Database: SQLite with 682 communes"

# Add remote origin
git remote add origin https://github.com/YOUR_USERNAME/color-communes.git

# Push to GitHub
git branch -M main
git push -u origin main
```

---

## 🗂️ WHAT GETS BACKED UP

### ✅ TRACKED (in repo)

```
production/
  ├── main.py
  ├── map_service.py
  ├── nominatim_service.py
  ├── database_service.py
  └── geojson_service.py

config/
  ├── docker-compose.yml
  ├── Dockerfile
  ├── requirements.txt
  └── .env (with placeholders, not secrets!)

scripts/
  ├── phase9_import_sorties.py
  ├── batch_import_gpx.py
  ├── gps_utils.py
  └── ... (all utilities)

.gitignore
.github/
  └── workflows/ (CI/CD if added)

CLAUDE.md
README.md
```

### ❌ IGNORED (not in repo - too large or sensitive)

```
data/color_communes.db        (backup separately)
gpx/ (1558 files, 1905 MB)    (too large, regenerate)
geojson_cache/                (cache, regenerate)
__pycache__/                  (build artifact)
.vscode/, .idea/              (IDE config)
.env (secrets)                (use .env.example instead)
archives/                     (old files, don't need versioning)
```

---

## 🔐 SECURITY: ENVIRONMENT VARIABLES

### Create .env.example (template, safe to commit)

```bash
# File: X:\color-communes\.env.example
# Copy this to .env and fill in real values

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_USER_ID=your_user_id_here

# Nominatim
NOMINATIM_EMAIL=your_email_here

# Strava (Phase 10)
STRAVA_CLIENT_ID=your_client_id_here
STRAVA_CLIENT_SECRET=your_client_secret_here
STRAVA_REFRESH_TOKEN=your_refresh_token_here

# Database
DATABASE_PATH=/data/color_communes.db
GEOJSON_CACHE_DIR=/data/geojson_cache
LOG_LEVEL=INFO
```

Add to .gitignore:
```
.env
.env.local
*.local
```

---

## 📝 STEP 3: CREATE GITHUB FILES

### Create .github/workflows/tests.yml (optional CI/CD)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.12
    
    - name: Install dependencies
      run: |
        pip install -r config/requirements.txt
    
    - name: Lint with flake8
      run: |
        flake8 production/ scripts/ --count --select=E9,F63,F7,F82 --show-source --statistics
    
    - name: Run tests (if any)
      run: |
        python -m pytest tests/ || true
```

---

## 📋 GIT WORKFLOW FOR DEVELOPMENT

### Daily Development

```bash
# Before starting work
git pull origin main

# Work on feature (create branch)
git checkout -b feature/phase-9-import

# Commit changes regularly
git add scripts/phase9_import_sorties.py
git commit -m "Implement parse_gpx_and_import function

- Add GPX waypoint parsing
- Integrate Nominatim lookup
- Handle duplicate detection"

# Push to branch
git push origin feature/phase-9-import

# When ready, create Pull Request on GitHub
```

### Creating Pull Requests

```
Title: Implement Phase 9 import system

Description:
## Summary
- Implement batch GPX import (1558 files)
- Add anti-doublon system (3 levels)
- Create imports_log tracking table

## Test plan
- [x] Test with 10 GPX files
- [x] Verify doublons prevented
- [x] Check database integrity
- [x] Validate map generation

Closes #1 (if issue exists)
```

---

## 🔄 GIT COMMANDS REFERENCE

### Basic

```bash
# See status
git status

# See changes
git diff

# Commit
git commit -m "message"

# Push to GitHub
git push origin main

# Pull latest
git pull origin main
```

### Branches

```bash
# Create new branch
git checkout -b feature/my-feature

# Switch branch
git checkout main

# Delete branch
git branch -d feature/my-feature

# List branches
git branch -a
```

### Undo

```bash
# Undo unstaged changes
git restore filename.py

# Undo staged changes
git restore --staged filename.py

# Revert a commit
git revert COMMIT_ID

# View history
git log --oneline
```

---

## 📌 COMMIT MESSAGE CONVENTION

### Format
```
[PHASE] Brief description

Detailed explanation of what and why

Fixes #123 (if related to issue)
```

### Examples

```
[Phase 9] Implement batch GPX import system
[Phase 10] Add Strava webhook integration
[Fix] Handle MultiLineString geometry error
[Docs] Update README with setup instructions
[Refactor] Simplify nominatim_service queries
```

---

## 🏷️ TAGGING RELEASES

### After completing a phase

```bash
# Create tag
git tag -a v1.0.0 -m "Phase 8 complete - Commands implemented"

# Push tag
git push origin v1.0.0

# Or push all tags
git push origin --tags
```

### Tag naming
```
v0.8.0 - Phase 8 complete
v0.9.0 - Phase 9 complete (imports)
v1.0.0 - Phase 10 complete (monitoring + Strava)
```

---

## 📊 REPOSITORY STRUCTURE ON GITHUB

```
color-communes/
├── .github/
│   └── workflows/
│       └── tests.yml
├── .gitignore
├── README.md
├── GITHUB_SETUP.md
├── production/
│   ├── main.py
│   ├── map_service.py
│   └── ...
├── config/
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── scripts/
│   ├── phase9_import_sorties.py
│   ├── batch_import_gpx.py
│   └── ...
├── CLAUDE.md
└── .env (NOT tracked, .env.example is)
```

---

## 🔐 BEST PRACTICES

### Do's
- ✅ Commit regularly (small, focused commits)
- ✅ Use meaningful commit messages
- ✅ Create branches for features
- ✅ Test before pushing
- ✅ Use .env.example for secrets template
- ✅ Keep .gitignore updated
- ✅ Tag releases

### Don'ts
- ❌ Commit .env with real secrets
- ❌ Commit large files (GPX, DB)
- ❌ Force push to main
- ❌ Commit IDE config (.vscode, .idea)
- ❌ Commit build artifacts (__pycache__)
- ❌ Large commit messages (just key info)

---

## 🚀 QUICK START (IF SETTING UP LATER)

### When ready to push to GitHub

```bash
cd X:\color-communes

# Initialize
git init
git add .
git commit -m "Initial commit: Color-communes bot"

# Add GitHub remote
git remote add origin https://github.com/YOUR_USERNAME/color-communes.git

# Push
git branch -M main
git push -u origin main
```

---

## 📚 USEFUL GITHUB FEATURES

### Issues (Track bugs/features)
```
Title: Implement Strava webhook
Labels: Phase-10, feature
Assignee: @yourusername
```

### Projects (Track phases)
```
Board columns:
- To Do (Phase 9)
- In Progress
- In Review
- Done
```

### Wiki (Extended documentation)
```
Add to GitHub Wiki:
- Architecture overview
- API documentation
- Deployment guide
- Troubleshooting
```

### Releases (Version history)
```
Create release for each phase:
- v0.8.0: Phase 8 (commands)
- v0.9.0: Phase 9 (imports)
- v1.0.0: Phase 10 (Strava + monitoring)
```

---

## 🔗 USEFUL LINKS

- GitHub CLI: https://cli.github.com/
- Gitignore templates: https://github.com/github/gitignore
- Git docs: https://git-scm.com/doc
- GitHub Help: https://docs.github.com/

---

## ✅ CHECKLIST

- [ ] Create GitHub repository
- [ ] Add .gitignore to local repo
- [ ] Create .env.example
- [ ] Initialize git locally
- [ ] First commit with entire codebase
- [ ] Push to GitHub
- [ ] Set up CI/CD (optional)
- [ ] Add README.md to GitHub
- [ ] Configure GitHub Settings (if public)
- [ ] Create releases for each phase

---

**Ready to backup your project on GitHub!** 🎉

