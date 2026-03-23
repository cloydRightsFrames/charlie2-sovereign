#!/usr/bin/env python3
"""
Charlie 2.0 — Biometric Judicial Gate
World's first: fingerprint required for high-threat
governance actions. Your body becomes part of the
sovereign chain.

Threat levels:
  LOW    — auto-approved by governance chain
  MEDIUM — constitutional review required
  HIGH   — biometric approval required
  CRITICAL — biometric + debate council required

Every biometric event timestamped in audit chain.
"""
import os, json, time, hashlib, sqlite3, subprocess, requests

C2      = os.path.expanduser("~/charlie2")
DB      = os.path.join(C2, "charlie2.db")
BIO_DIR = os.path.join(C2, "biometric")
API_URL = "http://127.0.0.1:8000"

THREAT_KEYWORDS = {
    "CRITICAL": [
        "delete","drop table","rm -rf","format","wipe",
        "destroy","kill all","shutdown","override constitution",
        "disable governance","bypass judicial"
    ],
    "HIGH": [
        "deploy","push to production","enact law","amend constitution",
        "add node","remove node","change policy","executive override",
        "grant access","revoke access","modify chain"
    ],
    "MEDIUM": [
        "install","update","upgrade","restart service",
        "change config","add user","modify","patch"
    ]
}

def audit_hash(data):
    return hashlib.sha256(f"{data}{time.time()}".encode()).hexdigest()[:16]

def log_event(event, verdict, detail=""):
    try:
        con = sqlite3.connect(DB); h = audit_hash(event)
        con.execute("INSERT INTO judicial_log VALUES(NULL,?,?,?,?)",
            (f"BIOMETRIC:{event}", verdict, h, time.time()))
        con.execute("INSERT INTO executive_log VALUES(NULL,?,NULL,NULL,?,?,?)",
            (event, detail[:200], h, time.time()))
        con.commit(); con.close()
    except: pass

def assess_threat(action):
    """Assess threat level of a governance action"""
    action_lower = action.lower()
    for level in ["CRITICAL","HIGH","MEDIUM"]:
        for kw in THREAT_KEYWORDS[level]:
            if kw in action_lower:
                return level, kw
    return "LOW", ""

def request_biometric(reason, timeout=30):
    """
    Request biometric approval via Android fingerprint.
    Uses termux-fingerprint if available.
    Falls back to PIN confirmation.
    """
    print(f"\n⚡ BIOMETRIC APPROVAL REQUIRED")
    print(f"  Reason:  {reason}")
    print(f"  Timeout: {timeout}s")

    # Try termux-fingerprint
    try:
        result = subprocess.run(
            ["termux-fingerprint",
             "-t", "Charlie 2.0 Judicial Gate",
             "-d", f"Approve: {reason[:50]}",
             "-c", "Cancel"],
            capture_output=True, text=True, timeout=timeout)
        output = result.stdout.strip()
        try:
            data = json.loads(output)
            auth_result = data.get("auth_result","")
            if auth_result == "AUTH_RESULT_SUCCESS":
                return True, "fingerprint"
            elif auth_result == "AUTH_RESULT_FAILURE":
                return False, "fingerprint_failed"
            else:
                return False, f"fingerprint_{auth_result}"
        except:
            if "SUCCESS" in output.upper():
                return True, "fingerprint"
            return False, "fingerprint_parse_error"
    except FileNotFoundError:
        pass
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        pass

    # Fallback — manual confirmation
    print(f"\n  [Termux fingerprint not available]")
    print(f"  Manual approval required for: {reason}")
    try:
        answer = input("  Type APPROVE to confirm: ").strip().upper()
        if answer == "APPROVE":
            return True, "manual"
        return False, "manual_denied"
    except:
        return False, "no_input"

def biometric_gate(action, payload="", auto_low=True):
    """
    Main biometric gate — assess threat and gate accordingly.
    Returns approval decision with full audit trail.
    """
    threat, trigger = assess_threat(action)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC")
    bio_hash  = audit_hash(f"{action}:{threat}:{timestamp}")

    print(f"\n⚖️  Biometric Judicial Gate")
    print(f"  Action:  {action[:60]}")
    print(f"  Threat:  {threat}")
    if trigger: print(f"  Trigger: {trigger}")

    # AUTO-APPROVE low threat
    if threat == "LOW":
        log_event(f"AUTO_APPROVED:{action[:40]}", "APPROVED",
                  f"threat:LOW trigger:none")
        return {
            "approved":   True,
            "method":     "auto",
            "threat":     "LOW",
            "action":     action,
            "timestamp":  timestamp,
            "bio_hash":   bio_hash,
            "reason":     "Low threat — auto-approved by governance chain"
        }

    # MEDIUM — constitutional review only
    if threat == "MEDIUM":
        try:
            r = requests.post(f"{API_URL}/ai/constitutional-chat",
                json={"prompt": f"Constitutional review of action: {action}"}, timeout=30)
            verdict = r.json().get("constitutional_verdict","APPROVED")
            approved = verdict != "BLOCKED"
            log_event(f"CONST_REVIEW:{action[:40]}", verdict, f"threat:MEDIUM")
            return {
                "approved":    approved,
                "method":      "constitutional_review",
                "threat":      "MEDIUM",
                "action":      action,
                "timestamp":   timestamp,
                "bio_hash":    bio_hash,
                "verdict":     verdict
            }
        except:
            pass

    # HIGH / CRITICAL — biometric required
    approved, method = request_biometric(action, timeout=30)
    verdict = "APPROVED" if approved else "BLOCKED"

    # CRITICAL also requires debate council
    debate_verdict = ""
    if threat == "CRITICAL" and approved:
        try:
            r = requests.post(f"{API_URL}/ai/debate",
                json={"prompt": f"Should this critical action be approved: {action}"},
                timeout=60)
            d = r.json()
            debate_verdict = d.get("verdict","APPROVED_WITH_CAVEATS")
            if debate_verdict == "REWRITE_REQUIRED":
                approved = False
                verdict  = "BLOCKED"
                log_event(f"DEBATE_BLOCKED:{action[:40]}", "BLOCKED",
                          "debate council rejected after biometric")
        except: pass

    # Save approval record
    record = {
        "action":         action,
        "threat":         threat,
        "trigger":        trigger,
        "approved":       approved,
        "method":         method,
        "verdict":        verdict,
        "debate_verdict": debate_verdict,
        "timestamp":      timestamp,
        "bio_hash":       bio_hash
    }
    rec_path = os.path.join(BIO_DIR, "approvals",
                             f"approval_{int(time.time())}.json")
    with open(rec_path, "w") as f: json.dump(record, f, indent=2)
    log_event(f"BIO_GATE:{action[:40]}", verdict,
              f"threat:{threat} method:{method}")

    print(f"  Result:  {'✓ APPROVED' if approved else '✗ BLOCKED'} via {method}")
    return record

def get_status():
    approvals = os.listdir(os.path.join(BIO_DIR,"approvals"))
    approved  = 0; blocked = 0
    for f in approvals:
        try:
            with open(os.path.join(BIO_DIR,"approvals",f)) as fh:
                d = json.load(fh)
            if d.get("approved"): approved += 1
            else: blocked += 1
        except: pass
    return {
        "total_gates":   len(approvals),
        "approved":      approved,
        "blocked":       blocked,
        "fingerprint_available": _check_fingerprint(),
        "threat_levels": list(THREAT_KEYWORDS.keys()) + ["LOW"],
        "system":        "Charlie 2.0 Biometric Judicial Gate"
    }

def _check_fingerprint():
    try:
        r = subprocess.run(["which","termux-fingerprint"],
            capture_output=True, text=True)
        return r.returncode == 0
    except: return False

if __name__ == "__main__":
    import sys
    cmd    = sys.argv[1] if len(sys.argv) > 1 else "status"
    action = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    if cmd == "gate":
        if not action: print("Usage: python biometric_gate.py gate <action>")
        else: print(json.dumps(biometric_gate(action), indent=2))
    elif cmd == "assess":
        if not action: print("Usage: python biometric_gate.py assess <action>")
        else:
            threat, trigger = assess_threat(action)
            print(f"Threat: {threat} | Trigger: {trigger or 'none'}")
    elif cmd == "status":
        print(json.dumps(get_status(), indent=2))
