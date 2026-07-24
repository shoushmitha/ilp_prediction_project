# ================================================================
# setup_github.ps1
# Run this script ONCE after installing Git to push your project
# to GitHub.
#
# BEFORE RUNNING:
#   1. Install Git from: https://git-scm.com/download/win
#   2. Create an empty GitHub repo (no README, no .gitignore)
#   3. Set your values below
# ================================================================

# ── YOUR SETTINGS ───────────────────────────────────────────────
$GIT_USER_NAME  = "YourGitHubUsername"       # Change this
$GIT_USER_EMAIL = "you@example.com"           # Change this
$GITHUB_REPO    = "https://github.com/YourGitHubUsername/ipl_prediction_project.git"
# ────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "=== IPL Prediction Project — GitHub Setup ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Configure Git identity
Write-Host "[1/6] Configuring Git identity..." -ForegroundColor Yellow
git config --global user.name  $GIT_USER_NAME
git config --global user.email $GIT_USER_EMAIL

# Step 2: Initialize repo
Write-Host "[2/6] Initializing local Git repository..." -ForegroundColor Yellow
git init
git branch -M main

# Step 3: Stage safe files (large JSON + secrets excluded via .gitignore)
Write-Host "[3/6] Staging project files..." -ForegroundColor Yellow
git add api.py
git add scraper.py
git add requirements.txt
git add .gitignore
git add README.md
git add generate_icons.py
git add chrome_extension/manifest.json
git add chrome_extension/popup.html
git add chrome_extension/popup.js
git add chrome_extension/background.js
git add chrome_extension/options.html
git add chrome_extension/options.js
git add chrome_extension/icons/

# Add streamlit app (from data/ipl_json/)
git add "data/ipl_json/streamlit_app.py"

# Show what will be committed
Write-Host ""
Write-Host "[4/6] Files staged for commit:" -ForegroundColor Yellow
git status --short

# Step 4: First commit
Write-Host ""
Write-Host "[5/6] Creating initial commit..." -ForegroundColor Yellow
git commit -m "Initial commit: IPL Prediction Dashboard + Chrome Extension + Web Scraper"

# Step 5: Push to GitHub
Write-Host ""
Write-Host "[6/6] Pushing to GitHub..." -ForegroundColor Yellow
git remote add origin $GITHUB_REPO
git push -u origin main

Write-Host ""
Write-Host "=== SUCCESS! Your project is now on GitHub ===" -ForegroundColor Green
Write-Host "Visit: $GITHUB_REPO" -ForegroundColor Cyan
Write-Host ""
