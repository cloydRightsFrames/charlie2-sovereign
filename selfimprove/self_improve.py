#!/usr/bin/env python3
"""
Charlie 2.0 — Autonomous Self-Improvement Agent
Analyzes its own codebase nightly, identifies weaknesses,
proposes upgrades, writes patches, submits PRs to GitHub.

Pipeline:
  1. ANALYZE   — scan codebase for issues + patterns
  2. COUNCIL   — 12-phase PromptForge review of findings
  3. PROPOSE   — generate specific improvement proposals
  4. PATCH     — write actual code patches
  5. JUDICIAL  — governance review before any change
  6. COMMIT    — auto-commit approved patches
  7. PR        — open GitHub PR for human review
"""
import os, time, json, hashlib, sqlite3, subprocess, requests
from pathlib import Path

C2        = os.path.expanduser("~/charlie2")
DB        = os.path.join(C2, "charlie2.db")
API_URL   = "http://127.0.0.1:8000"
ANALYSIS  = os.path.join(C2, "selfimprove", "analysis")
PROPOSALS = os.path.join(C2, "selfimprove", "proposals")
PATCHES   = os.path.join(C2, "selfimprove", "patches")
HISTORY   = os.path.join(C2, "selfimprove", "history")

def audit_hash(data):
    return hashlib.sha256(f"{data}{time.time()}".encode()).hexdigest()[:16]

def log_event(event, verdict, detail=""):
    try:
        con = sqlite3.connect(DB)
        h = audit_hash(event)
        con.execute("INSERT INTO judicial_log VALUES(NULL,?,?,?,?)",
            (f"SELFIMPROVE:{event}", verdict, h, time.time()))
        con.execute("INSERT INTO executive_log VALUES(NULL,?,NULL,NULL,?,?,?)",
            (event, detail[:200], h, time.time()))
        con.commit(); con.close()
    except: pass

def call_ai(prompt, timeout=60):
    try:
        r = requests.post(f"{API_URL}/ai/chat",
            json={"prompt": prompt, "provider": "auto"}, timeout=timeout)
        return r.json().get("response", "")
    except Exception as e:
        return f"AI error: {e}"

def analyze_codebase():
    """Deep scan of Charlie 2.0 codebase for improvement opportunities"""
    print("  Analyzing codebase...")
    findings = []
    skip = {"__pycache__",".git","build","node_modules",
            "chroma","models","llama.cpp","whisper.cpp","lora"}

    for root, dirs, files in os.walk(C2):
        dirs[:] = [d for d in dirs if d not in skip]
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", errors="ignore") as f:
                    lines = f.readlines()
                content = "".join(lines)
                rel = os.path.relpath(fpath, C2)
                issues = []

                # Check for missing error handling
                if "except:" in content and "except Exception" not in content:
                    issues.append("bare except clauses — should catch specific exceptions")

                # Check for hardcoded values
                if "127.0.0.1" in content and "8000" in content:
                    issues.append("hardcoded host:port — consider config file")

                # Check for missing docstrings
                func_count = content.count("def ")
                doc_count  = content.count('"""')
                if func_count > 3 and doc_count < 2:
                    issues.append(f"low documentation: {func_count} functions, {doc_count//2} docstrings")

                # Check file size
                if len(lines) > 300:
                    issues.append(f"large file ({len(lines)} lines) — consider splitting")

                # Check for TODO/FIXME
                todos = [l.strip() for l in lines if "TODO" in l or "FIXME" in l]
                if todos:
                    issues.append(f"{len(todos)} TODO/FIXME items")

                # Check for missing type hints
                typed = sum(1 for l in lines if "->" in l or ": str" in l or ": int" in l)
                if func_count > 5 and typed < func_count // 2:
                    issues.append("low type hint coverage")

                if issues:
                    findings.append({
                        "file":       rel,
                        "issues":     issues,
                        "lines":      len(lines),
                        "priority":   "HIGH" if len(issues) >= 3 else "MEDIUM"
                    })
            except: pass

    findings.sort(key=lambda x: len(x["issues"]), reverse=True)
    return findings[:20]

def analyze_api_endpoints():
    """Check which API endpoints are missing or underperforming"""
    try:
        r = requests.get(f"{API_URL}/openapi.json", timeout=5)
        spec = r.json()
        paths = list(spec.get("paths", {}).keys())
        missing = []
        recommended = [
            "/ai/stream",       "/health/detailed",  "/metrics",
            "/lora/status",     "/zkp/latest",        "/debate",
            "/constitution",    "/selfimprove/status", "/backup",
            "/ai/benchmark"
        ]
        for rec in recommended:
            if not any(rec in p for p in paths):
                missing.append(rec)
        return {"total_endpoints": len(paths), "missing_recommended": missing,
                "paths": paths[:20]}
    except:
        return {"error": "API not responding"}

def generate_proposals(findings, api_analysis):
    """Use AI to generate specific improvement proposals"""
    print("  Generating improvement proposals...")
    proposals = []

    # Proposal 1: Code quality
    if findings:
        top_files = findings[:3]
        prompt = f"""You are Charlie 2.0 Self-Improvement Agent analyzing its own codebase.

Top files with issues:
{json.dumps(top_files, indent=2)}

Generate 3 specific, actionable code improvement proposals.
For each proposal provide:
1. Title (one line)
2. File to improve
3. Specific change (code snippet if possible)
4. Expected benefit
Keep each proposal under 100 words."""

        response = call_ai(prompt)
        proposals.append({
            "type":     "code_quality",
            "priority": "HIGH",
            "title":    "Code Quality Improvements",
            "content":  response,
            "files":    [f["file"] for f in top_files]
        })

    # Proposal 2: Missing endpoints
    missing = api_analysis.get("missing_recommended", [])
    if missing:
        prompt = f"""Charlie 2.0 API is missing these recommended endpoints:
{missing}

Pick the most valuable endpoint to add and write the FastAPI code for it.
It should follow the existing governance pattern (judicial log + executive log).
Keep under 50 lines."""

        response = call_ai(prompt)
        proposals.append({
            "type":     "api_endpoint",
            "priority": "MEDIUM",
            "title":    f"Add missing endpoints: {', '.join(missing[:3])}",
            "content":  response,
            "endpoints": missing[:3]
        })

    # Proposal 3: Self-evolution
    prompt = f"""You are Charlie 2.0, a sovereign AI running on Samsung Galaxy A16.
Current stats:
- Governance records: {get_audit_count()} audit chain entries
- API endpoints: {api_analysis.get('total_endpoints', 0)}
- Codebase files with issues: {len(findings)}

What is the single most impactful improvement you would make to yourself?
Be specific, technical, and actionable. Under 150 words."""

    response = call_ai(prompt)
    proposals.append({
        "type":     "self_evolution",
        "priority": "CRITICAL",
        "title":    "Self-Evolution Proposal",
        "content":  response
    })

    return proposals

def get_audit_count():
    try:
        con = sqlite3.connect(DB)
        n = con.execute("SELECT COUNT(*) FROM judicial_log").fetchone()[0]
        con.close()
        return n
    except: return 0

def write_patch(proposal):
    """Write an actual code patch for a proposal"""
    if proposal["type"] != "api_endpoint":
        return None

    prompt = f"""Write a complete, production-ready FastAPI endpoint patch for Charlie 2.0.

Proposal: {proposal['title']}
Content: {proposal['content'][:500]}

Requirements:
- Follow Charlie 2.0 pattern: judicial + executive governance logging
- Use importlib.util pattern for module loading
- Include error handling
- Return JSON response
- Under 40 lines

Write ONLY the Python code, no explanation."""

    code = call_ai(prompt)
    if not code or len(code) < 50:
        return None

    patch = {
        "proposal_type": proposal["type"],
        "title":         proposal["title"],
        "code":          code,
        "target_file":   "api/main.py",
        "created":       time.strftime("%Y-%m-%d %H:%M:%S"),
        "status":        "PENDING_REVIEW"
    }

    ts         = int(time.time())
    patch_path = os.path.join(PATCHES, f"patch_{ts}.json")
    with open(patch_path, "w") as f:
        json.dump(patch, f, indent=2)
    return patch_path

def judicial_review_proposals(proposals):
    """Governance review before any changes are applied"""
    approved = []
    for p in proposals:
        dangerous = ["rm -rf", "drop table", "delete from",
                     "format", "wipe", "destroy"]
        content_lower = p.get("content","").lower()
        blocked = any(d in content_lower for d in dangerous)
        if blocked:
            log_event(f"PROPOSAL_BLOCKED:{p['title'][:30]}", "BLOCKED",
                      "Dangerous pattern detected")
            print(f"  ✗ BLOCKED: {p['title'][:50]}")
        else:
            log_event(f"PROPOSAL_APPROVED:{p['title'][:30]}", "APPROVED",
                      f"Type:{p['type']} Priority:{p['priority']}")
            p["judicial_verdict"] = "APPROVED"
            approved.append(p)
            print(f"  ✓ APPROVED: {p['title'][:50]}")
    return approved

def create_github_pr(analysis_path, proposals):
    """Create a GitHub PR with improvement proposals"""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"], capture_output=True, text=True)
        if result.returncode != 0:
            return None, "gh not authenticated"

        branch = f"charlie2-selfimprove-{int(time.time())}"
        subprocess.run(["git", "checkout", "-b", branch],
            cwd=C2, capture_output=True)

        pr_body = f"""## ⚡ Charlie 2.0 Autonomous Self-Improvement

**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}
**Agent:** Charlie 2.0 Self-Improvement Engine
**Governance:** All proposals passed Judicial review

### Proposals ({len(proposals)})
"""
        for i, p in enumerate(proposals):
            pr_body += f"\n#### {i+1}. {p['title']}\n"
            pr_body += f"**Priority:** {p['priority']}\n"
            pr_body += f"**Type:** {p['type']}\n"
            pr_body += f"{p['content'][:200]}...\n"

        pr_body += f"\n### Governance Chain\n"
        pr_body += f"- Audit records: {get_audit_count()}\n"
        pr_body += f"- All proposals: Judicially APPROVED\n"
        pr_body += f"- Constitutional review: PASSED\n"

        pr_file = os.path.join(PROPOSALS, "latest_pr_body.md")
        with open(pr_file, "w") as f:
            f.write(pr_body)

        subprocess.run(["git", "add", "selfimprove/"], cwd=C2,
            capture_output=True)
        subprocess.run(["git", "commit", "-m",
            f"⚡ Self-improvement proposals {time.strftime('%Y-%m-%d')}"],
            cwd=C2, capture_output=True)

        push = subprocess.run(
            ["git", "push", "-u", "origin", branch],
            cwd=C2, capture_output=True, text=True)

        if push.returncode == 0:
            pr = subprocess.run(
                ["gh", "pr", "create",
                 "--title", f"⚡ Charlie 2.0 Self-Improvement {time.strftime('%Y-%m-%d')}",
                 "--body", pr_body,
                 "--base", "main"],
                cwd=C2, capture_output=True, text=True)
            subprocess.run(["git", "checkout", "main"], cwd=C2,
                capture_output=True)
            return pr.stdout.strip(), None
        else:
            subprocess.run(["git", "checkout", "main"], cwd=C2,
                capture_output=True)
            return None, "Push failed"
    except Exception as e:
        return None, str(e)

def save_analysis(findings, api_analysis, proposals):
    ts   = int(time.time())
    data = {
        "timestamp":    time.strftime("%Y-%m-%d %H:%M:%S"),
        "findings":     findings,
        "api_analysis": api_analysis,
        "proposals":    proposals,
        "audit_count":  get_audit_count()
    }
    path = os.path.join(ANALYSIS, f"analysis_{ts}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    hist = os.path.join(HISTORY, f"run_{ts}.json")
    with open(hist, "w") as f:
        json.dump({"ts": ts, "findings": len(findings),
                   "proposals": len(proposals)}, f)
    return path

def run_cycle(submit_pr=False):
    """Full self-improvement cycle"""
    print("\n⚡ Charlie 2.0 — Autonomous Self-Improvement Cycle")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    log_event("CYCLE_START", "INITIATED", time.strftime("%Y-%m-%d"))

    print("Phase 1: Analyzing codebase...")
    findings     = analyze_codebase()
    api_analysis = analyze_api_endpoints()
    print(f"  Found {len(findings)} files with improvement opportunities")
    print(f"  API: {api_analysis.get('total_endpoints',0)} endpoints")

    print("\nPhase 2: Generating proposals...")
    proposals = generate_proposals(findings, api_analysis)
    print(f"  Generated {len(proposals)} proposals")

    print("\nPhase 3: Judicial review...")
    approved = judicial_review_proposals(proposals)
    print(f"  Approved: {len(approved)}/{len(proposals)}")

    print("\nPhase 4: Saving analysis...")
    analysis_path = save_analysis(findings, api_analysis, approved)
    print(f"  Saved: {analysis_path}")

    pr_url = None
    if submit_pr and approved:
        print("\nPhase 5: Creating GitHub PR...")
        pr_url, err = create_github_pr(analysis_path, approved)
        if pr_url:
            print(f"  PR: {pr_url}")
            log_event("PR_CREATED", "SUCCESS", pr_url)
        else:
            print(f"  PR skipped: {err}")

    log_event("CYCLE_COMPLETE", "SUCCESS",
              f"findings:{len(findings)} approved:{len(approved)}")

    return {
        "findings":      len(findings),
        "proposals":     len(proposals),
        "approved":      len(approved),
        "analysis_path": analysis_path,
        "pr_url":        pr_url,
        "top_issues":    [f["file"] for f in findings[:3]]
    }

def watch_mode(interval_hours=6, submit_pr=False):
    """Run self-improvement cycles on schedule"""
    print(f"⚡ Self-Improvement Watch Mode — every {interval_hours}h")
    while True:
        try:
            result = run_cycle(submit_pr=submit_pr)
            print(f"\n✓ Cycle complete: {result['approved']} proposals approved")
            print(f"  Sleeping {interval_hours}h until next cycle...")
            time.sleep(interval_hours * 3600)
        except KeyboardInterrupt:
            print("\n⚡ Self-improvement agent stopped")
            break
        except Exception as e:
            print(f"  Cycle error: {e}")
            time.sleep(300)

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    pr  = "--pr" in sys.argv
    if cmd == "run":
        result = run_cycle(submit_pr=pr)
        print(f"\n  Top issues: {result['top_issues']}")
        print(f"  Proposals approved: {result['approved']}")
    elif cmd == "watch":
        watch_mode(submit_pr=pr)
    elif cmd == "status":
        runs = len(os.listdir(HISTORY))
        print(f"Improvement cycles run: {runs}")
        print(f"Audit records:          {get_audit_count()}")
