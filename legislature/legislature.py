#!/usr/bin/env python3
"""
Charlie 2.0 — Autonomous AI Legislature
World's first: 3 AI agents draft, debate, vote on, and enact
their own policies. No human required.

Agents:
  DRAFTER   — analyzes system state, drafts bills
  DEBATER   — challenges and defends each bill
  SPEAKER   — presides, calls votes, enacts law
"""
import os, json, time, hashlib, sqlite3, requests

C2     = os.path.expanduser("~/charlie2")
DB     = os.path.join(C2, "charlie2.db")
LEG_DIR = os.path.join(C2, "legislature")
API_URL = "http://127.0.0.1:8000"

def audit_hash(data):
    return hashlib.sha256(f"{data}{time.time()}".encode()).hexdigest()[:16]

def log_event(event, verdict, detail=""):
    try:
        con = sqlite3.connect(DB); h = audit_hash(event)
        con.execute("INSERT INTO judicial_log VALUES(NULL,?,?,?,?)",
            (f"LEGISLATURE:{event}", verdict, h, time.time()))
        con.execute("INSERT INTO legislative_log VALUES(NULL,?,?,?,?,?)",
            (event, verdict, "AI_LEGISLATURE", h, time.time()))
        con.commit(); con.close()
    except: pass

def call_ai(prompt, timeout=45):
    try:
        r = requests.post(f"{API_URL}/ai/chat",
            json={"prompt": prompt, "provider": "auto"}, timeout=timeout)
        return r.json().get("response", "")
    except: return ""

def get_system_state():
    try:
        con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
        j = con.execute("SELECT COUNT(*) FROM judicial_log").fetchone()[0]
        e = con.execute("SELECT COUNT(*) FROM executive_log").fetchone()[0]
        blocked = con.execute(
            "SELECT COUNT(*) FROM judicial_log WHERE verdict='BLOCKED'"
        ).fetchone()[0]
        enacted = len(os.listdir(os.path.join(LEG_DIR,"enacted")))
        con.close()
        return {"judicial": j, "executive": e,
                "blocked": blocked, "enacted_laws": enacted,
                "block_rate": round(blocked/j*100,1) if j > 0 else 0}
    except: return {}

def draft_bill(state):
    prompt = f"""You are the DRAFTER agent in Charlie 2.0's AI Legislature.
System state: {json.dumps(state)}

Draft ONE specific governance policy bill.
Respond ONLY as JSON with:
- "bill_title": short title
- "bill_text": the policy (under 80 words)
- "rationale": why needed (under 40 words)
- "category": one of [SECURITY, PERFORMANCE, GOVERNANCE, AI_ROUTING, MEMORY]
Return ONLY the JSON."""
    resp = call_ai(prompt)
    try:
        resp = resp.strip()
        if "```" in resp: resp = resp.split("```")[1].lstrip("json").strip()
        return json.loads(resp)
    except: return None

def debate_bill(bill):
    prompt = f"""You are the DEBATER in Charlie 2.0's AI Legislature.
Bill: {bill.get('bill_title','')}
Text: {bill.get('bill_text','')}

Give FOR and AGAINST arguments. Then cast your VOTE: AYE or NAY.
Format as JSON:
- "for": argument for (under 40 words)
- "against": argument against (under 40 words)
- "vote": "AYE" or "NAY"
- "reasoning": one sentence
Return ONLY the JSON."""
    resp = call_ai(prompt)
    try:
        resp = resp.strip()
        if "```" in resp: resp = resp.split("```")[1].lstrip("json").strip()
        return json.loads(resp)
    except: return {"vote": "AYE", "for": "", "against": "", "reasoning": ""}

def speaker_ruling(bill, debate):
    prompt = f"""You are the SPEAKER of Charlie 2.0's AI Legislature.
Bill: {bill.get('bill_title','')}
Text: {bill.get('bill_text','')}
Debate: FOR — {debate.get('for','')} | AGAINST — {debate.get('against','')}
Debater vote: {debate.get('vote','')}

As Speaker, cast your deciding vote and rule.
Format as JSON:
- "speaker_vote": "AYE" or "NAY"
- "ruling": "ENACTED" or "VETOED"
- "proclamation": formal enactment statement (under 50 words)
Return ONLY the JSON."""
    resp = call_ai(prompt)
    try:
        resp = resp.strip()
        if "```" in resp: resp = resp.split("```")[1].lstrip("json").strip()
        return json.loads(resp)
    except: return {"speaker_vote":"AYE","ruling":"ENACTED","proclamation":""}

def run_session():
    """Run a full legislative session"""
    session_id = f"SESSION-{int(time.time())}"
    print(f"\n⚡ AI Legislature — {session_id}")
    log_event(f"SESSION_OPEN:{session_id}", "APPROVED")

    state = get_system_state()
    print(f"  System state: {state}")

    results = []
    for bill_num in range(1, 4):
        print(f"\n  Bill {bill_num}/3:")

        bill = draft_bill(state)
        if not bill:
            print("    Draft failed — skipping")
            continue
        bill["bill_id"]   = f"BILL-{session_id}-{bill_num}"
        bill["session"]   = session_id
        bill["drafted_ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"    Drafted: {bill.get('bill_title','')}")

        debate = debate_bill(bill)
        print(f"    Debate vote: {debate.get('vote','?')}")

        ruling = speaker_ruling(bill, debate)
        print(f"    Speaker ruling: {ruling.get('ruling','?')}")

        record = {
            "bill":    bill,
            "debate":  debate,
            "ruling":  ruling,
            "hash":    audit_hash(bill.get("bill_text",""))
        }

        if ruling.get("ruling") == "ENACTED":
            path = os.path.join(LEG_DIR, "enacted",
                                f"{bill['bill_id']}.json")
            with open(path, "w") as f: json.dump(record, f, indent=2)
            log_event(f"BILL_ENACTED:{bill['bill_id']}", "APPROVED",
                      bill.get("bill_title","")[:100])
            print(f"    ✓ ENACTED: {bill.get('bill_title','')}")
        else:
            path = os.path.join(LEG_DIR, "vetoed",
                                f"{bill['bill_id']}.json")
            with open(path, "w") as f: json.dump(record, f, indent=2)
            log_event(f"BILL_VETOED:{bill['bill_id']}", "BLOCKED",
                      bill.get("bill_title","")[:100])
            print(f"    ✗ VETOED: {bill.get('bill_title','')}")

        results.append(record)

    enacted = sum(1 for r in results
                  if r["ruling"].get("ruling")=="ENACTED")
    log_event(f"SESSION_CLOSE:{session_id}", "APPROVED",
              f"enacted:{enacted}/3")
    print(f"\n  Session complete: {enacted}/3 bills enacted")
    return {"session_id": session_id, "bills": len(results),
            "enacted": enacted, "vetoed": len(results)-enacted,
            "records": results}

def get_status():
    enacted = os.listdir(os.path.join(LEG_DIR,"enacted"))
    vetoed  = os.listdir(os.path.join(LEG_DIR,"vetoed"))
    return {
        "enacted_laws": len(enacted),
        "vetoed_bills": len(vetoed),
        "total_sessions": len(enacted)+len(vetoed),
        "system": "Charlie 2.0 Autonomous AI Legislature",
        "agents": ["DRAFTER","DEBATER","SPEAKER"]
    }

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "session": run_session()
    elif cmd == "status": print(json.dumps(get_status(), indent=2))
    elif cmd == "laws":
        laws = os.listdir(os.path.join(LEG_DIR,"enacted"))
        print(f"Enacted laws: {len(laws)}")
        for l in laws[-5:]: print(f"  {l}")
