"""
Push IPL Prediction Project to GitHub via REST API (no Git installation needed).
"""
import requests
import os
import base64
import json

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "YOUR_GITHUB_TOKEN_HERE")
GITHUB_USERNAME = "shoushmitha"
REPO_NAME = "ilp_prediction_project"
BRANCH = "main"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "Content-Type": "application/json",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Files/dirs to skip
SKIP_NAMES = {
    ".git", "__pycache__", ".env", "node_modules",
    "push_to_github.py",  # skip this script itself
    "xgb_model.pkl",      # skip large binary model file
}
SKIP_EXTENSIONS = {".pyc", ".pyo", ".pkl"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB limit per file

def collect_files(base_dir):
    """Walk the directory and collect all files to push."""
    files = []
    for root, dirs, filenames in os.walk(base_dir):
        # Skip hidden/ignored directories
        dirs[:] = [d for d in dirs if d not in SKIP_NAMES and not d.startswith(".")]
        for filename in filenames:
            if filename in SKIP_NAMES:
                continue
            ext = os.path.splitext(filename)[1].lower()
            if ext in SKIP_EXTENSIONS:
                continue
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, base_dir).replace("\\", "/")
            file_size = os.path.getsize(full_path)
            if file_size > MAX_FILE_SIZE:
                print(f"  [Skipping too large]: {rel_path} ({file_size/1024/1024:.1f} MB)")
                continue
            files.append((rel_path, full_path))
    return files


def create_repo():
    """Create the GitHub repo if it doesn't exist."""
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{REPO_NAME}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        print(f"[OK] Repo already exists: https://github.com/{GITHUB_USERNAME}/{REPO_NAME}")
        return True
    
    print(f"[Creating repo]: {REPO_NAME}...")
    url = "https://api.github.com/user/repos"
    payload = {
        "name": REPO_NAME,
        "description": "IPL 2026 AI Prediction & Analytics Dashboard -- Streamlit + XGBoost + Groq AI",
        "private": False,
        "auto_init": True,
    }
    r = requests.post(url, headers=HEADERS, json=payload)
    if r.status_code in (200, 201):
        print(f"[OK] Repo created: https://github.com/{GITHUB_USERNAME}/{REPO_NAME}")
        return True
    else:
        print(f"[FAIL] Failed to create repo: {r.status_code} -- {r.text}")
        return False


def get_file_sha(repo_path):
    """Get existing file SHA (needed to update existing files)."""
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{REPO_NAME}/contents/{repo_path}"
    r = requests.get(url, headers=HEADERS, params={"ref": BRANCH})
    if r.status_code == 200:
        return r.json().get("sha")
    return None


def push_file(repo_path, local_path):
    """Push a single file to GitHub."""
    with open(local_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")
    
    sha = get_file_sha(repo_path)
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{REPO_NAME}/contents/{repo_path}"
    payload = {
        "message": f"Update {repo_path} -- IPL 2026 Champion Banner & Season Concluded",
        "content": content,
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha  # required for updating existing files
    
    r = requests.put(url, headers=HEADERS, json=payload)
    return r.status_code in (200, 201)


def main():
    print("=" * 55)
    print("IPL Prediction Project -> GitHub Pusher")
    print("=" * 55)
    print(f"User: {GITHUB_USERNAME}")
    print(f"Repo: {REPO_NAME}")
    print()

    # Check if repo is accessible
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{REPO_NAME}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        print(f"Repo found: https://github.com/{GITHUB_USERNAME}/{REPO_NAME}")
    else:
        print(f"Cannot access repo ({r.status_code}). Make sure '{REPO_NAME}' exists on GitHub.")
        print("Please create the repo manually at https://github.com/new then re-run this script.")
        return

    # Step 2: Collect files
    files = collect_files(BASE_DIR)
    print(f"\n[Found {len(files)} files to push]:\n")

    # Step 3: Push each file
    success, failed = 0, []
    for i, (repo_path, local_path) in enumerate(files, 1):
        print(f"  [{i}/{len(files)}] Pushing: {repo_path} ... ", end="", flush=True)
        try:
            ok = push_file(repo_path, local_path)
            if ok:
                print("SUCCESS")
                success += 1
            else:
                print("FAILED")
                failed.append(repo_path)
        except Exception as e:
            print(f"ERROR: {e}")
            failed.append(repo_path)

    print("\n" + "=" * 55)
    print(f"Successfully pushed: {success}/{len(files)} files")
    if failed:
        print(f"Failed ({len(failed)}):")
        for f in failed:
            print(f"   - {f}")
    print(f"\nView your repo: https://github.com/{GITHUB_USERNAME}/{REPO_NAME}")
    print("=" * 55)


if __name__ == "__main__":
    main()
