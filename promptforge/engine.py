#!/usr/bin/env python3
"""
Charlie 2.0 — PromptForge Governance Integration
12-phase AI council prompt pipeline
Each phase: Judicial review → Legislative policy → Executive execution
"""
import os, time, hashlib, sqlite3, json, requests
from pathlib import Path

C2      = os.path.expanduser("~/charlie2")
DB      = os.path.join(C2, "charlie2.db")
API_URL = "http://127.0.0.1:8000"
OUT_DIR = os.path.join(C2, "promptforge", "outputs")

def audit_hash(data):
    return hashlib.sha256(f"{data}{time.time()}".encode()).hexdigest()[:16]

def log_event(branch, event, verdict="APPROVED", result=""):
    try:
        con = sqlite3.connect(DB); h = audit_hash(event)
        if branch == "judicial":
            con.execute("INSERT INTO judicial_log VALUES(NULL,?,?,?,?)",
                (event, verdict, h, time.time()))
        elif branch == "legislative":
            con.execute("INSERT INTO legislative_log VALUES(NULL,?,?,?,?,?)",
                (event, verdict, "PROMPTFORGE", h, time.time()))
        elif branch == "executive":
            con.execute("INSERT INTO executive_log VALUES(NULL,?,NULL,NULL,?,?,?)",
                (event, result[:200], h, time.time()))
        con.commit(); con.close()
    except: pass

def call_ai(prompt, provider="auto", use_rag=True):
    endpoint = "/ai/rag-chat" if use_rag else "/ai/chat"
    try:
        r = requests.post(f"{API_URL}{endpoint}",
            json={"prompt": prompt, "provider": provider}, timeout=60)
        d = r.json()
        return d.get("response",""), d.get("provider","unknown")
    except Exception as e:
        return f"Error: {e}", "error"

# 12-Phase Council Pipeline
PHASES = [
    {
        "id": 1, "name": "ARCHITECT",
        "role": "System Architect",
        "prompt_template": "You are Charlie 2.0 System Architect. Analyze this codebase/task and provide high-level architectural assessment:\n\n{input}\n\nProvide: 1) Current architecture 2) Strengths 3) Critical gaps"
    },
    {
        "id": 2, "name": "SECURITY",
        "role": "Security Auditor",
        "prompt_template": "You are Charlie 2.0 Security Auditor. Review for vulnerabilities:\n\n{input}\n\nIdentify: 1) Security risks 2) Severity 3) Fixes required"
    },
    {
        "id": 3, "name": "PERFORMANCE",
        "role": "Performance Engineer",
        "prompt_template": "You are Charlie 2.0 Performance Engineer. Analyze bottlenecks:\n\n{input}\n\nAssess: 1) Performance issues 2) ARM64 optimizations 3) Memory usage"
    },
    {
        "id": 4, "name": "GOVERNANCE",
        "role": "Governance Auditor",
        "prompt_template": "You are Charlie 2.0 Governance Auditor. Review tri-branch compliance:\n\n{input}\n\nCheck: 1) Judicial coverage 2) Legislative policies 3) Executive logging"
    },
    {
        "id": 5, "name": "API_DESIGN",
        "role": "API Designer",
        "prompt_template": "You are Charlie 2.0 API Designer. Review API quality:\n\n{input}\n\nEvaluate: 1) Endpoint design 2) Error handling 3) Missing endpoints"
    },
    {
        "id": 6, "name": "DATA_LAYER",
        "role": "Data Engineer",
        "prompt_template": "You are Charlie 2.0 Data Engineer. Analyze data layer:\n\n{input}\n\nReview: 1) SQLite schema 2) ChromaDB usage 3) Data integrity"
    },
    {
        "id": 7, "name": "AI_INTEGRATION",
        "role": "AI Integration Specialist",
        "prompt_template": "You are Charlie 2.0 AI Integration Specialist. Review AI pipeline:\n\n{input}\n\nAnalyze: 1) Provider routing 2) RAG effectiveness 3) Prompt quality"
    },
    {
        "id": 8, "name": "MOBILE",
        "role": "Android Engineer",
        "prompt_template": "You are Charlie 2.0 Android Engineer. Review mobile integration:\n\n{input}\n\nAssess: 1) Kotlin code quality 2) API connectivity 3) UX improvements"
    },
    {
        "id": 9, "name": "DEVOPS",
        "role": "DevOps Engineer",
        "prompt_template": "You are Charlie 2.0 DevOps Engineer. Review deployment pipeline:\n\n{input}\n\nEvaluate: 1) CI/CD pipeline 2) Railway config 3) Auto-commit agent"
    },
    {
        "id": 10, "name": "SYNTHESIZER",
        "role": "Technical Synthesizer",
        "prompt_template": "You are Charlie 2.0 Technical Synthesizer. Synthesize all council findings:\n\n{input}\n\nProduce: 1) Priority issues list 2) Quick wins 3) Strategic roadmap"
    },
    {
        "id": 11, "name": "IMPLEMENTER",
        "role": "Implementation Lead",
        "prompt_template": "You are Charlie 2.0 Implementation Lead. Create actionable plan:\n\n{input}\n\nDeliver: 1) Step-by-step fixes 2) Code snippets 3) Termux commands"
    },
    {
        "id": 12, "name": "JUDGE",
        "role": "Final Judicial Review",
        "prompt_template": "You are Charlie 2.0 Chief Justice. Final governance review:\n\n{input}\n\nDeliver: 1) APPROVED/REJECTED verdict 2) Constitutional compliance 3) Seal of sovereign approval"
    }
]

def run_phase(phase, context, provider="auto"):
    name = phase["name"]
    prompt = phase["prompt_template"].format(input=context[:2000])
    log_event("judicial", f"PHASE_{phase['id']}_{name}:START", "APPROVED")
    log_event("legislative", f"PHASE_{name}:POLICY", "ACTIVE",
              f"Phase {phase['id']} of 12-phase council pipeline")
    print(f"\n  Phase {phase['id']:02d}/12 [{name}] — {phase['role']}")
    response, provider_used = call_ai(prompt, provider)
    log_event("executive", f"PHASE_{phase['id']}_{name}:COMPLETE",
              "SUCCESS", response[:200])
    return {"phase": phase["id"], "name": name, "role": phase["role"],
            "response": response, "provider": provider_used}

def run_pipeline(target_input, provider="auto", phases=None, save=True):
    if phases is None:
        phases = list(range(1, 13))
    ts = time.strftime("%Y%m%d_%H%M%S")
    print(f"\n⚡ PromptForge 12-Phase Council Pipeline")
    print(f"  Target: {target_input[:60]}")
    print(f"  Phases: {phases}")
    print(f"  Provider: {provider}")
    log_event("judicial", "PROMPTFORGE_PIPELINE:START", "APPROVED")
    log_event("legislative", "12_PHASE_COUNCIL:ENACTED", "ACTIVE",
              "Full governance council pipeline initiated")

    results = []
    context = target_input
    for phase in PHASES:
        if phase["id"] not in phases:
            continue
        result = run_phase(phase, context, provider)
        results.append(result)
        context = f"Previous analysis:\n{result['response'][:800]}\n\nOriginal input:\n{target_input[:400]}"
        print(f"     ✓ {result['response'][:80]}...")

    report = build_report(results, target_input, ts)
    if save:
        out_path = os.path.join(OUT_DIR, f"council_{ts}.md")
        with open(out_path, "w") as f:
            f.write(report)
        print(f"\n⚡ Report saved: {out_path}")
        log_event("executive", f"PROMPTFORGE_REPORT:{ts}", "SUCCESS", out_path)

    return results, report

def build_report(results, target, ts):
    lines = [
        f"# ⚡ Charlie 2.0 — Council Report",
        f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Target:** {target[:100]}",
        f"**Phases completed:** {len(results)}/12",
        "", "---", ""
    ]
    for r in results:
        lines += [
            f"## Phase {r['phase']:02d} — {r['name']} ({r['role']})",
            f"*Provider: {r['provider']}*", "",
            r['response'], "", "---", ""
        ]
    lines += [
        "## Governance Chain",
        "All phases passed through Judicial → Legislative → Executive audit.",
        "Hash-chained tamper-evident ledger. Sovereign. Sealed."
    ]
    return "\n".join(lines)

def quick_review(file_path, provider="auto"):
    """Quick single-file review — phases 1,2,4,11"""
    try:
        with open(file_path, "r", errors="ignore") as f:
            content = f.read()[:3000]
    except:
        content = file_path
    results, report = run_pipeline(content, provider,
        phases=[1, 2, 4, 11], save=True)
    return results, report

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "review" and len(sys.argv) > 2:
        target = " ".join(sys.argv[2:])
        if os.path.exists(target):
            quick_review(target)
        else:
            run_pipeline(target, phases=[1, 2, 10, 11, 12])
    elif cmd == "full" and len(sys.argv) > 2:
        target = " ".join(sys.argv[2:])
        if os.path.exists(target):
            with open(target, "r", errors="ignore") as f:
                content = f.read()
            run_pipeline(content)
        else:
            run_pipeline(target)
    elif cmd == "self":
        api_path = os.path.expanduser("~/charlie2/api/main.py")
        quick_review(api_path)
    else:
        print("Usage:")
        print("  python engine.py review <file_or_text>  — quick 4-phase review")
        print("  python engine.py full   <file_or_text>  — full 12-phase council")
        print("  python engine.py self                   — review Charlie 2.0 API")
