#!/usr/bin/env python3
"""
Charlie 2.0 — Auto-Commit Coding Agent
Watches codebase → detects changes → asks AI for review
→ judicial approval → auto-commits to GitHub
"""
import os, time, hashlib, sqlite3, subprocess, json, requests
from pathlib import Path

C2      = os.path.expanduser("~/charlie2")
DB      = os.path.join(C2, "charlie2.db")
REPO    = C2
WATCH   = [
    os.path.join(C2, "api"),
    os.path.join(C2, "providers"),
    os.path.join(C2, "memory"),
    os.path.join(C2, "agent"),
]
EXTS    = {".py", ".kt", ".sh", ".md", ".json"}
API_URL = "http://127.0.0.1:8000"
INTERVAL = 60  # seconds between checks

def audit_hash(data):
    return hashlib.sha256(f"{data}{time.time()}".encode()).hexdigest()[:16]

def log_event(branch, event, verdict="APPROVED", result=""):
    try:
        con = sqlite3.connect(DB)
        h = audit_hash(event)
        if branch == "judicial":
            con.execute("INSERT INTO judicial_log VALUES(NULL,?,?,?,?)",
                (event, verdict, h, time.time()))
        elif branch == "executive":
            con.execute("INSERT INTO executive_log VALUES(NULL,?,NULL,NULL,?,?,?)",
                (event, result[:200], h, time.time()))
        con.commit(); con.close()
    except: pass

def get_file_hash(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except: return ""

def scan_files():
    state = {}
    for watch_dir in WATCH:
        if not os.path.exists(watch_dir): continue
        for root, dirs, files in os.walk(watch_dir):
            dirs[:] = [d for d in dirs if d not in
                       {"__pycache__",".git","build","node_modules"}]
            for fname in files:
                if any(fname.endswith(e) for e in EXTS):
                    fpath = os.path.join(root, fname)
                    state[fpath] = get_file_hash(fpath)
    return state

def get_diff():
    try:
        result = subprocess.run(
            ["git", "diff", "--stat", "HEAD"],
            capture_output=True, text=True, cwd=REPO)
        return result.stdout.strip()
    except: return ""

def get_changed_files():
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=REPO)
        lines = result.stdout.strip().split("\n")
        return [l[3:].strip() for l in lines if l.strip()]
    except: return []

def ai_review(changed_files, diff_stat):
    """Ask AI to review changes via governance API"""
    if not changed_files: return "No changes to review.", True
    prompt = f"""You are Charlie 2.0 code reviewer.
Changed files: {', '.join(changed_files[:5])}
Diff summary: {diff_stat[:300] if diff_stat else 'new files added'}

In 1-2 sentences: Are these changes safe to commit? Reply APPROVE or REJECT then reason."""
    try:
        r = requests.post(f"{API_URL}/ai/chat",
            json={"prompt": prompt, "provider": "auto"}, timeout=30)
        resp = r.json().get("response", "")
        approved = "APPROVE" in resp.upper() or "SAFE" in resp.upper()
        return resp, approved
    except:
        return "AI review unavailable — auto-approving", True

def judicial_review(changed_files):
    """Tri-branch judicial review before commit"""
    blocked_patterns = ["password", "secret_key", "private_key",
                        "api_key", ".env", "credentials"]
    for f in changed_files:
        for pattern in blocked_patterns:
            if pattern in f.lower():
                log_event("judicial", f"BLOCK_SENSITIVE:{f}", "BLOCKED")
                return False, f"BLOCKED: sensitive file {f}"
    log_event("judicial", f"COMMIT_REVIEW:{len(changed_files)}_files", "APPROVED")
    return True, "APPROVED"

def auto_commit(changed_files, ai_review_text):
    """Execute commit via Executive branch"""
    if not changed_files: return False, "nothing to commit"
    try:
        subprocess.run(["git", "add", "-A"], cwd=REPO,
            capture_output=True)
        msg = f"⚡ Charlie 2.0 Agent: {len(changed_files)} file(s) — {time.strftime('%Y-%m-%d %H:%M')}"
        result = subprocess.run(
            ["git", "commit", "-m", msg],
            capture_output=True, text=True, cwd=REPO)
        if result.returncode == 0:
            log_event("executive", f"AUTO_COMMIT:{len(changed_files)}_files",
                "SUCCESS", msg)
            return True, msg
        else:
            return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)

def auto_push():
    """Push to GitHub"""
    try:
        result = subprocess.run(
            ["git", "push"], capture_output=True, text=True, cwd=REPO,
            timeout=30)
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)

def run_agent(dry_run=False, push=False):
    """Single agent cycle"""
    print(f"\n⚡ Charlie 2.0 Agent — {time.strftime('%H:%M:%S')}")
    changed = get_changed_files()
    if not changed:
        print("  ✓ No changes detected")
        return

    print(f"  📝 {len(changed)} changed files:")
    for f in changed[:5]: print(f"     {f}")

    # Judicial review
    approved, reason = judicial_review(changed)
    print(f"  ⚖️  Judicial: {reason}")
    if not approved:
        print(f"  ✗ Commit blocked by Judicial branch")
        return

    # AI review
    diff = get_diff()
    review_text, ai_approved = ai_review(changed, diff)
    print(f"  🧠 AI review: {review_text[:100]}")
    if not ai_approved:
        print(f"  ✗ Commit rejected by AI review")
        log_event("judicial", "AI_REJECTED_COMMIT", "BLOCKED", review_text[:100])
        return

    if dry_run:
        print(f"  DRY RUN — would commit {len(changed)} files")
        return

    # Executive commit
    committed, msg = auto_commit(changed, review_text)
    if committed:
        print(f"  ✅ Committed: {msg}")
        if push:
            pushed, push_msg = auto_push()
            if pushed:
                print(f"  🚀 Pushed to GitHub")
                log_event("executive", "AUTO_PUSH_SUCCESS", "SUCCESS")
            else:
                print(f"  ⚠️  Push failed: {push_msg[:60]}")
    else:
        print(f"  ✗ Commit failed: {msg}")

def watch_mode(interval=60, push=False):
    """Continuous watch mode"""
    print(f"⚡ Charlie 2.0 Coding Agent — Watch Mode")
    print(f"  Watching: {', '.join([os.path.basename(w) for w in WATCH])}")
    print(f"  Interval: {interval}s  Push: {push}")
    print(f"  Press Ctrl+C to stop\n")
    last_state = scan_files()
    while True:
        try:
            time.sleep(interval)
            current_state = scan_files()
            changed_files = [f for f, h in current_state.items()
                           if h != last_state.get(f)]
            new_files = [f for f in current_state if f not in last_state]
            all_changed = changed_files + new_files
            if all_changed:
                print(f"\n🔔 Changes detected: {len(all_changed)} files")
                run_agent(push=push)
                last_state = current_state
        except KeyboardInterrupt:
            print("\n⚡ Agent stopped")
            break

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    push = "--push" in sys.argv
    if cmd == "watch":
        watch_mode(INTERVAL, push=push)
    elif cmd == "dry":
        run_agent(dry_run=True)
    elif cmd == "run":
        run_agent(push=push)
    elif cmd == "status":
        changed = get_changed_files()
        diff = get_diff()
        print(f"Changed files: {len(changed)}")
        for f in changed: print(f"  {f}")
        if diff: print(f"\nDiff:\n{diff}")
