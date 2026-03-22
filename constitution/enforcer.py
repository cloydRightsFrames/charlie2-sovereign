#!/usr/bin/env python3
"""
Charlie 2.0 — Constitutional AI Enforcer
Intercepts every AI response and enforces constitutional articles
Actions: BLOCK | REWRITE | REDACT | FLAG | APPROVE
"""
import os, json, re, time, hashlib, sqlite3

C2     = os.path.expanduser("~/charlie2")
DB     = os.path.join(C2, "charlie2.db")
CONST  = os.path.join(C2, "constitution", "constitution.json")

def load_constitution():
    with open(CONST) as f:
        return json.load(f)

def audit_hash(data):
    return hashlib.sha256(f"{data}{time.time()}".encode()).hexdigest()[:16]

def log_enforcement(event, verdict, detail=""):
    try:
        con = sqlite3.connect(DB)
        h = audit_hash(event)
        con.execute("INSERT INTO judicial_log VALUES(NULL,?,?,?,?)",
            (f"CONSTITUTIONAL:{event}", verdict, h, time.time()))
        con.execute("INSERT INTO legislative_log VALUES(NULL,?,?,?,?,?)",
            (detail[:200], verdict, "CONSTITUTION_v1", h, time.time()))
        con.commit(); con.close()
    except: pass

def check_blocked_patterns(text, constitution):
    text_lower = text.lower()
    for pattern in constitution.get("blocked_patterns", []):
        if pattern.lower() in text_lower:
            return True, pattern
    return False, None

def check_rewrite_triggers(text, constitution):
    text_lower = text.lower()
    for trigger in constitution.get("rewrite_triggers", []):
        if trigger.lower() in text_lower:
            return True, trigger
    return False, None

def check_articles(prompt, response, constitution):
    violations = []
    for article in constitution["articles"]:
        aid  = article["id"]
        name = article["name"]
        pol  = article["policy"].lower()
        enf  = article["enforcement"]
        sev  = article["severity"]

        # ART2: Deception check
        if aid == "ART2":
            deception_phrases = ["i am human","i'm human","i am a person","not an ai"]
            for phrase in deception_phrases:
                if phrase in response.lower():
                    violations.append({"article": aid, "name": name,
                        "enforcement": "BLOCK", "severity": sev,
                        "detail": f"Deception detected: '{phrase}'"})

        # ART3: Code safety
        if aid == "ART3":
            dangerous = ["password=", "secret=", "api_key=",
                        "rm -rf", "drop table", "delete from users"]
            for d in dangerous:
                if d.lower() in response.lower():
                    violations.append({"article": aid, "name": name,
                        "enforcement": "REWRITE", "severity": sev,
                        "detail": f"Dangerous pattern: '{d}'"})

        # ART5: PII check
        if aid == "ART5":
            pii_patterns = [
                r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
                r'\b\d{16}\b',               # Credit card
                r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b',  # Email not from user
            ]
            for pattern in pii_patterns:
                if re.search(pattern, response, re.IGNORECASE):
                    violations.append({"article": aid, "name": name,
                        "enforcement": "REDACT", "severity": sev,
                        "detail": "PII pattern detected"})

    return violations

def rewrite_response(response, violations, constitution):
    """AI-powered constitutional rewrite"""
    rewritten = response
    for v in violations:
        if v["enforcement"] == "REDACT":
            rewritten = re.sub(r'\b\d{16}\b', '[REDACTED-CARD]', rewritten)
            rewritten = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED-SSN]', rewritten)
        elif v["enforcement"] == "REWRITE":
            rewritten = rewritten.replace("password=", "password=[REDACTED]")
            rewritten = rewritten.replace("api_key=", "api_key=[REDACTED]")
            rewritten = rewritten.replace("secret=", "secret=[REDACTED]")
    rewritten += "\n\n*[Constitutional review applied — sensitive content protected]*"
    return rewritten

def enforce(prompt, response, provider="unknown"):
    """
    Main enforcement function.
    Returns: (final_response, verdict, violations, constitutional_seal)
    """
    constitution = load_constitution()

    # Check blocked patterns
    blocked, pattern = check_blocked_patterns(response, constitution)
    if blocked:
        log_enforcement(f"BLOCKED:{pattern}", "BLOCKED", f"Pattern in response from {provider}")
        return (
            f"⚖️ CONSTITUTIONAL BLOCK\n\nThis response was blocked by Article 3 "
            f"(Code Safety) of the Charlie 2.0 Constitution.\n\nPattern detected: `{pattern}`\n\n"
            f"Please rephrase your request.",
            "BLOCKED", [{"pattern": pattern}],
            None
        )

    # Check rewrite triggers
    needs_rewrite, trigger = check_rewrite_triggers(response, constitution)

    # Check articles
    violations = check_articles(prompt, response, constitution)

    if not violations and not needs_rewrite:
        h = audit_hash(response)
        log_enforcement("RESPONSE_APPROVED", "APPROVED", f"Provider:{provider}")
        seal = {
            "verdict": "APPROVED",
            "hash": h,
            "articles_checked": len(constitution["articles"]),
            "violations": 0,
            "ts": time.time()
        }
        return response, "APPROVED", [], seal

    # Apply enforcement
    final = rewrite_response(response, violations, constitution)
    h = audit_hash(final)

    for v in violations:
        log_enforcement(
            f"{v['enforcement']}:{v['article']}",
            v["enforcement"],
            v["detail"])

    seal = {
        "verdict": "REWRITTEN",
        "hash": h,
        "articles_checked": len(constitution["articles"]),
        "violations": len(violations),
        "enforcements": [v["enforcement"] for v in violations],
        "ts": time.time()
    }

    return final, "REWRITTEN", violations, seal

def test_enforcer():
    print("\n⚡ Constitutional Enforcer Test\n")
    tests = [
        ("Write code", 'Here is the code: password="admin123"', "Test ART3"),
        ("Are you human?", "Yes I am human and not an AI", "Test ART2"),
        ("Hello", "Hello! I can help you with that. Here is a safe response.", "Test APPROVE"),
    ]
    for prompt, response, label in tests:
        final, verdict, violations, seal = enforce(prompt, response)
        print(f"[{label}] Verdict: {verdict}")
        if violations:
            print(f"  Violations: {[v.get('article','?') or v.get('pattern','?') for v in violations]}")
        print(f"  Response: {final[:80]}...")
        print()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_enforcer()
    else:
        prompt = sys.argv[1] if len(sys.argv) > 2 else "test"
        response = sys.argv[2] if len(sys.argv) > 2 else "test response"
        final, verdict, violations, seal = enforce(prompt, response)
        print(json.dumps({"verdict": verdict, "response": final,
                         "violations": len(violations), "seal": seal}, indent=2))
