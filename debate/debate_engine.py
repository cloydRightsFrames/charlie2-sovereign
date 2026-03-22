#!/usr/bin/env python3
"""
Charlie 2.0 — Multi-Agent Debate System
3 sovereign AI agents argue every response before delivery:
  PROSECUTOR  — challenges, finds flaws, steelmans opposition
  DEFENDER    — defends, validates, finds strengths
  JUDGE       — weighs both sides, delivers final verdict + synthesis
All debate rounds logged to tri-branch governance chain.
"""
import os, time, hashlib, sqlite3, json, requests

C2      = os.path.expanduser("~/charlie2")
DB      = os.path.join(C2, "charlie2.db")
API_URL = "http://127.0.0.1:8000"

def audit_hash(data):
    return hashlib.sha256(f"{data}{time.time()}".encode()).hexdigest()[:16]

def log_debate(event, verdict, detail=""):
    try:
        con = sqlite3.connect(DB)
        h = audit_hash(event)
        con.execute("INSERT INTO judicial_log VALUES(NULL,?,?,?,?)",
            (f"DEBATE:{event}", verdict, h, time.time()))
        con.execute("INSERT INTO executive_log VALUES(NULL,?,NULL,NULL,?,?,?)",
            (event, detail[:200], h, time.time()))
        con.commit(); con.close()
    except: pass

def call_ai(prompt, system_role, provider="auto", timeout=45):
    full_prompt = f"{system_role}\n\n{prompt}"
    try:
        r = requests.post(f"{API_URL}/ai/chat",
            json={"prompt": full_prompt, "provider": provider},
            timeout=timeout)
        d = r.json()
        return d.get("response", "No response"), d.get("provider", "unknown")
    except Exception as e:
        return f"Agent error: {e}", "error"

PROSECUTOR_ROLE = """You are the PROSECUTOR agent in Charlie 2.0's multi-agent debate system.
Your role: Challenge the proposed response with maximum intellectual rigor.
- Find factual errors, logical fallacies, missing caveats
- Steelman the strongest opposing argument
- Identify what could go wrong if this response is taken as truth
- Be adversarial but intellectually honest
- Keep response under 150 words
Format: Start with PROSECUTION: then your argument."""

DEFENDER_ROLE = """You are the DEFENDER agent in Charlie 2.0's multi-agent debate system.
Your role: Defend and strengthen the proposed response.
- Validate what is correct and useful
- Add supporting evidence or reasoning
- Identify the strongest points in the response
- Address the prosecution's likely objections preemptively
- Keep response under 150 words
Format: Start with DEFENSE: then your argument."""

JUDGE_ROLE = """You are the JUDGE agent in Charlie 2.0's multi-agent debate system.
You have heard both the Prosecution and Defense arguments.
Your role: Deliver the final synthesized verdict.
- Weigh prosecution vs defense arguments
- Identify what parts of the original response survive scrutiny
- Identify what must be corrected or caveated
- Deliver a FINAL VERDICT: APPROVED / APPROVED_WITH_CAVEATS / REWRITE_REQUIRED
- Write the final improved response incorporating debate insights
- Keep total response under 250 words
Format:
VERDICT: [APPROVED|APPROVED_WITH_CAVEATS|REWRITE_REQUIRED]
REASONING: [2-3 sentences]
FINAL RESPONSE: [the synthesized answer]"""

def run_debate(original_prompt, initial_response, provider="auto"):
    print(f"\n⚡ Debate Council initiating for: {original_prompt[:50]}...")
    log_debate("DEBATE_START", "INITIATED", original_prompt[:100])

    debate_context = f"""Original question: {original_prompt}
Proposed response: {initial_response[:600]}"""

    # Round 1: Prosecution
    print("  ⚖️  Round 1: Prosecutor examining response...")
    prosecution, p_provider = call_ai(debate_context, PROSECUTOR_ROLE, provider)
    log_debate("PROSECUTION_ROUND", "COMPLETE", prosecution[:150])
    print(f"     {prosecution[:100]}...")

    # Round 2: Defense
    print("  🛡️  Round 2: Defender responding...")
    defense_context = f"{debate_context}\n\nProsecution argument:\n{prosecution}"
    defense, d_provider = call_ai(defense_context, DEFENDER_ROLE, provider)
    log_debate("DEFENSE_ROUND", "COMPLETE", defense[:150])
    print(f"     {defense[:100]}...")

    # Round 3: Judge deliberates
    print("  👨‍⚖️  Round 3: Judge deliberating...")
    judge_context = f"""{debate_context}

PROSECUTION ARGUMENT:
{prosecution}

DEFENSE ARGUMENT:
{defense}

Now deliver your final verdict and synthesized response."""

    judgment, j_provider = call_ai(judge_context, JUDGE_ROLE, provider)
    log_debate("JUDGMENT_DELIVERED", "COMPLETE", judgment[:150])
    print(f"     {judgment[:100]}...")

    # Parse verdict
    verdict = "APPROVED"
    if "REWRITE_REQUIRED" in judgment.upper():
        verdict = "REWRITE_REQUIRED"
    elif "APPROVED_WITH_CAVEATS" in judgment.upper():
        verdict = "APPROVED_WITH_CAVEATS"

    # Extract final response
    final_response = initial_response
    if "FINAL RESPONSE:" in judgment:
        final_response = judgment.split("FINAL RESPONSE:")[-1].strip()
    elif verdict == "APPROVED":
        final_response = initial_response

    h = audit_hash(final_response)
    log_debate(f"DEBATE_COMPLETE:{verdict}", verdict, f"hash:{h}")

    return {
        "original_prompt":   original_prompt,
        "initial_response":  initial_response,
        "prosecution":       prosecution,
        "defense":           defense,
        "judgment":          judgment,
        "final_response":    final_response,
        "verdict":           verdict,
        "debate_hash":       h,
        "rounds":            3,
        "providers": {
            "prosecutor": p_provider,
            "defender":   d_provider,
            "judge":      j_provider
        },
        "ts": time.time()
    }

def quick_debate(prompt, provider="auto"):
    """Get initial response then debate it"""
    print(f"\n⚡ Charlie 2.0 Debate Council")
    print(f"  Question: {prompt[:60]}")
    print(f"  Fetching initial response...")
    try:
        r = requests.post(f"{API_URL}/ai/chat",
            json={"prompt": prompt, "provider": provider}, timeout=45)
        initial = r.json().get("response", "")
    except Exception as e:
        return {"error": str(e)}
    if not initial:
        return {"error": "No initial response from AI"}
    return run_debate(prompt, initial, provider)

if __name__ == "__main__":
    import sys
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else \
        "What is the best approach to building sovereign AI systems?"
    result = quick_debate(prompt)
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"\n{'='*50}")
        print(f"VERDICT:        {result['verdict']}")
        print(f"DEBATE HASH:    {result['debate_hash']}")
        print(f"FINAL RESPONSE: {result['final_response'][:300]}")
