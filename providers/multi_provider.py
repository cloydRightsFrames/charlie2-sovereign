#!/usr/bin/env python3
import os, time, hashlib, sqlite3, requests

KEYS_FILE = os.path.expanduser("~/charlie2/providers/keys.env")
if os.path.exists(KEYS_FILE):
    with open(KEYS_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                if 'your_' not in v:
                    os.environ[k.strip()] = v.strip()

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_KEY    = os.environ.get("OPENAI_API_KEY", "")
GEMINI_KEY    = os.environ.get("GEMINI_API_KEY", "")
OLLAMA_URL    = "http://127.0.0.1:11434"
DB            = os.path.expanduser("~/charlie2/charlie2.db")

def audit_hash(data):
    return hashlib.sha256(f"{data}{time.time()}".encode()).hexdigest()[:16]

def log_to_db(branch, event, verdict, result=""):
    try:
        con = sqlite3.connect(DB); h = audit_hash(event)
        if branch == "judicial":
            con.execute("INSERT INTO judicial_log VALUES(NULL,?,?,?,?)",
                (event, verdict, h, time.time()))
        elif branch == "executive":
            con.execute("INSERT INTO executive_log VALUES(NULL,?,NULL,NULL,?,?,?)",
                (event, result[:200], h, time.time()))
        con.commit(); con.close()
    except: pass

def try_ollama(prompt, model="deepseek-coder:1.3b"):
    try:
        r = requests.post(f"{OLLAMA_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False}, timeout=30)
        resp = r.json().get("response", "")
        if resp: return resp, "ollama:local"
    except: pass
    return None, None

def try_anthropic(prompt, model="claude-haiku-4-5-20251001"):
    if not ANTHROPIC_KEY: return None, None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        msg = client.messages.create(model=model, max_tokens=1024,
            messages=[{"role": "user", "content": prompt}])
        return msg.content[0].text, f"anthropic:{model}"
    except: return None, None

def try_openai(prompt, model="gpt-4o-mini"):
    if not OPENAI_KEY: return None, None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_KEY)
        r = client.chat.completions.create(model=model, max_tokens=1024,
            messages=[{"role": "user", "content": prompt}])
        return r.choices[0].message.content, f"openai:{model}"
    except: return None, None

def try_gemini(prompt, model="gemini-1.5-flash"):
    if not GEMINI_KEY: return None, None
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_KEY)
        m = genai.GenerativeModel(model)
        r = m.generate_content(prompt)
        return r.text, f"gemini:{model}"
    except: return None, None

def route(prompt, preferred="auto"):
    log_to_db("judicial", f"INFER:{prompt[:40]}", "APPROVED")
    providers = {"ollama": try_ollama, "anthropic": try_anthropic,
                 "openai": try_openai, "gemini": try_gemini}
    order = ["ollama", "anthropic", "openai", "gemini"]
    if preferred != "auto" and preferred in providers:
        order = [preferred] + [p for p in order if p != preferred]
    for name in order:
        resp, label = providers[name](prompt)
        if resp:
            log_to_db("executive", f"INFER_SUCCESS:{label}", "SUCCESS", resp[:200])
            return {"response": resp, "provider": label, "routed_via": "tri-branch"}
    log_to_db("executive", "INFER_FAILED", "FAILED")
    return {"response": "All providers offline.", "provider": "none"}

if __name__ == "__main__":
    import sys
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Hello Charlie 2.0"
    result = route(prompt)
    print(f"\n⚡ [{result['provider']}]\n{result['response']}")
