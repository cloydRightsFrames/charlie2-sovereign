#!/usr/bin/env python3
"""
Charlie 2.0 — Living Constitutional AI
World's first: constitution that rewrites itself based on
evidence from its own governance chain.

Every enforcement, debate verdict, and ZK proof feeds back
into the constitutional articles. The AI evolves its own law.
"""
import os, json, time, hashlib, sqlite3, requests

C2      = os.path.expanduser("~/charlie2")
DB      = os.path.join(C2, "charlie2.db")
LC_DIR  = os.path.join(C2, "living_constitution")
CONST_F = os.path.join(C2, "constitution", "constitution.json")
HIST_F  = os.path.join(LC_DIR, "history", "amendment_history.json")
API_URL = "http://127.0.0.1:8000"

def audit_hash(data):
    return hashlib.sha256(f"{data}{time.time()}".encode()).hexdigest()[:16]

def log_event(event, verdict, detail=""):
    try:
        con = sqlite3.connect(DB); h = audit_hash(event)
        con.execute("INSERT INTO judicial_log VALUES(NULL,?,?,?,?)",
            (f"LIVING_CONST:{event}", verdict, h, time.time()))
        con.execute("INSERT INTO legislative_log VALUES(NULL,?,?,?,?,?)",
            (event, verdict, "LIVING_CONSTITUTION", h, time.time()))
        con.commit(); con.close()
    except: pass

def load_constitution():
    try:
        with open(CONST_F) as f: return json.load(f)
    except: return {"articles": [], "version": "1.0"}

def save_constitution(const):
    with open(CONST_F, "w") as f:
        json.dump(const, f, indent=2)

def load_history():
    try:
        with open(HIST_F) as f: return json.load(f)
    except: return []

def save_history(hist):
    with open(HIST_F, "w") as f: json.dump(hist, f, indent=2)

def get_governance_stats():
    """Analyze the governance chain for patterns"""
    try:
        con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
        judicial = con.execute(
            "SELECT event, verdict FROM judicial_log ORDER BY ts DESC LIMIT 200"
        ).fetchall()
        legislative = con.execute(
            "SELECT policy, status FROM legislative_log ORDER BY ts DESC LIMIT 50"
        ).fetchall()
        con.close()
        blocked  = sum(1 for r in judicial if r["verdict"] == "BLOCKED")
        approved = sum(1 for r in judicial if r["verdict"] == "APPROVED")
        total    = len(judicial)
        block_rate = round(blocked/total*100, 1) if total > 0 else 0
        patterns = {}
        for r in judicial:
            ev = r["event"][:30]
            if ev not in patterns: patterns[ev] = 0
            patterns[ev] += 1
        top_patterns = sorted(patterns.items(),
                               key=lambda x: x[1], reverse=True)[:5]
        return {
            "total":       total,
            "blocked":     blocked,
            "approved":    approved,
            "block_rate":  block_rate,
            "top_patterns": top_patterns,
            "legislative":  len(legislative)
        }
    except: return {}

def propose_amendment(article_id, stats):
    """Use AI to propose a constitutional amendment based on data"""
    const = load_constitution()
    article = next((a for a in const["articles"]
                    if a["id"] == article_id), None)
    if not article: return None

    prompt = f"""You are the Charlie 2.0 Constitutional AI.
Current Article {article_id} — {article['name']}:
Policy: {article['policy']}
Enforcement: {article['enforcement']}

Governance data from last 200 decisions:
- Total decisions: {stats.get('total',0)}
- Blocked: {stats.get('blocked',0)} ({stats.get('block_rate',0)}%)
- Approved: {stats.get('approved',0)}
- Top patterns: {stats.get('top_patterns',[])}

Based on this evidence, propose ONE specific amendment to improve this article.
Format your response as JSON with fields:
- "amendment": the new policy text (under 100 words)
- "reasoning": why this change is needed (under 50 words)
- "severity_change": "HIGHER" / "LOWER" / "SAME"
Return ONLY the JSON, no other text."""

    try:
        r = requests.post(f"{API_URL}/ai/chat",
            json={"prompt": prompt, "provider": "auto"}, timeout=45)
        resp = r.json().get("response","")
        resp = resp.strip()
        if resp.startswith("```"):
            resp = resp.split("```")[1]
            if resp.startswith("json"): resp = resp[4:]
        return json.loads(resp)
    except: return None

def enact_amendment(article_id, amendment_data, stats):
    """Formally enact a constitutional amendment"""
    const = load_constitution()
    history = load_history()

    for i, article in enumerate(const["articles"]):
        if article["id"] != article_id: continue
        old_policy = article["policy"]
        new_policy = amendment_data.get("amendment", old_policy)

        # Record amendment
        amendment = {
            "amendment_id":   f"AMD-{int(time.time())}",
            "article_id":     article_id,
            "article_name":   article["name"],
            "old_policy":     old_policy,
            "new_policy":     new_policy,
            "reasoning":      amendment_data.get("reasoning",""),
            "severity_change": amendment_data.get("severity_change","SAME"),
            "enacted":        time.strftime("%Y-%m-%d %H:%M:%S"),
            "governance_evidence": stats,
            "hash":           audit_hash(new_policy)
        }

        # Update article
        const["articles"][i]["policy"]      = new_policy
        const["articles"][i]["last_amended"] = time.strftime("%Y-%m-%d %H:%M:%S")
        const["articles"][i]["amendment_count"] = \
            const["articles"][i].get("amendment_count", 0) + 1

        # Increment version
        v = const.get("version","1.0").split(".")
        const["version"] = f"{v[0]}.{int(v[1])+1}"

        history.append(amendment)
        save_constitution(const)
        save_history(history)

        log_event(f"AMENDMENT_ENACTED:{article_id}", "APPROVED",
                  f"v{const['version']} {new_policy[:80]}")

        return amendment
    return None

def run_evolution_cycle():
    """Full living constitution evolution cycle"""
    print("\n⚡ Living Constitution Evolution Cycle")
    stats = get_governance_stats()
    print(f"  Governance data: {stats.get('total',0)} decisions "
          f"({stats.get('block_rate',0)}% blocked)")

    const  = load_constitution()
    results = []

    for article in const["articles"]:
        aid  = article["id"]
        name = article["name"]
        count = article.get("amendment_count", 0)
        print(f"\n  Analyzing Article {aid} — {name} ({count} prior amendments)...")

        proposal = propose_amendment(aid, stats)
        if not proposal:
            print(f"    No amendment proposed")
            continue

        print(f"    Proposal: {proposal.get('amendment','')[:60]}...")
        print(f"    Reasoning: {proposal.get('reasoning','')[:50]}...")

        # Only enact if meaningfully different
        if proposal.get("amendment","") != article["policy"]:
            amendment = enact_amendment(aid, proposal, stats)
            if amendment:
                print(f"    ✓ ENACTED: {amendment['amendment_id']}")
                results.append(amendment)
            else:
                print(f"    Enactment failed")
        else:
            print(f"    Article unchanged — already optimal")

    print(f"\n⚡ Cycle complete: {len(results)} amendments enacted")
    print(f"   Constitution version: {const.get('version','?')}")
    log_event("EVOLUTION_CYCLE_COMPLETE", "APPROVED",
              f"amendments:{len(results)}")
    return results

def get_status():
    const   = load_constitution()
    history = load_history()
    stats   = get_governance_stats()
    return {
        "version":         const.get("version","1.0"),
        "articles":        len(const.get("articles",[])),
        "total_amendments": len(history),
        "last_evolution":  history[-1].get("enacted","never") if history else "never",
        "governance_stats": stats,
        "is_living":       True,
        "system":          "Charlie 2.0 Living Constitutional AI"
    }

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "evolve":   run_evolution_cycle()
    elif cmd == "status":
        print(json.dumps(get_status(), indent=2))
    elif cmd == "history":
        hist = load_history()
        print(f"Amendments: {len(hist)}")
        for a in hist[-5:]:
            print(f"  {a['amendment_id']} — {a['article_name']}: {a['new_policy'][:60]}")
