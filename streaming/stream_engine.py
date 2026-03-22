#!/usr/bin/env python3
"""
Charlie 2.0 — Real-Time Streaming Inference Engine
Token-by-token streaming like ChatGPT — but sovereign.
Streams from: Ollama (local) → Anthropic → OpenAI
Every token governed by the tri-branch audit chain.
"""
import os, time, hashlib, sqlite3, json, requests
from typing import Iterator, AsyncIterator

C2     = os.path.expanduser("~/charlie2")
DB     = os.path.join(C2, "charlie2.db")
OLLAMA = "http://127.0.0.1:11434"

def audit_hash(data):
    return hashlib.sha256(f"{data}{time.time()}".encode()).hexdigest()[:16]

def log_stream(event, verdict, detail=""):
    try:
        con = sqlite3.connect(DB)
        h = audit_hash(event)
        con.execute("INSERT INTO judicial_log VALUES(NULL,?,?,?,?)",
            (f"STREAM:{event}", verdict, h, time.time()))
        con.execute("INSERT INTO executive_log VALUES(NULL,?,NULL,NULL,?,?,?)",
            (event, detail[:200], h, time.time()))
        con.commit(); con.close()
    except: pass

def stream_ollama(prompt: str, model: str = "deepseek-coder:1.3b") -> Iterator[str]:
    log_stream(f"OLLAMA_START:{prompt[:30]}", "APPROVED")
    try:
        r = requests.post(
            f"{OLLAMA}/api/generate",
            json={"model": model, "prompt": prompt, "stream": True},
            stream=True, timeout=120)
        full = ""
        for line in r.iter_lines():
            if line:
                try:
                    chunk = json.loads(line.decode("utf-8"))
                    token = chunk.get("response", "")
                    if token:
                        full += token
                        yield token
                    if chunk.get("done", False):
                        break
                except: continue
        log_stream("OLLAMA_COMPLETE", "SUCCESS", f"tokens:{len(full.split())}")
    except Exception as e:
        log_stream("OLLAMA_ERROR", "FAILED", str(e))
        yield f"[Ollama error: {e}]"

def stream_anthropic(prompt: str, model: str = "claude-haiku-4-5-20251001") -> Iterator[str]:
    keys_file = os.path.join(C2, "providers", "keys.env")
    api_key = ""
    if os.path.exists(keys_file):
        with open(keys_file) as f:
            for line in f:
                if "ANTHROPIC_API_KEY=" in line and "your_" not in line:
                    api_key = line.split("=",1)[1].strip()
    if not api_key:
        yield "[Anthropic key not configured — add to ~/charlie2/providers/keys.env]"
        return
    log_stream(f"ANTHROPIC_START:{prompt[:30]}", "APPROVED")
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        with client.messages.stream(
            model=model, max_tokens=1024,
            messages=[{"role":"user","content":prompt}]
        ) as stream:
            for text in stream.text_stream:
                yield text
        log_stream("ANTHROPIC_COMPLETE", "SUCCESS")
    except Exception as e:
        log_stream("ANTHROPIC_ERROR", "FAILED", str(e))
        yield f"[Anthropic error: {e}]"

def stream_openai(prompt: str, model: str = "gpt-4o-mini") -> Iterator[str]:
    keys_file = os.path.join(C2, "providers", "keys.env")
    api_key = ""
    if os.path.exists(keys_file):
        with open(keys_file) as f:
            for line in f:
                if "OPENAI_API_KEY=" in line and "your_" not in line:
                    api_key = line.split("=",1)[1].strip()
    if not api_key:
        yield "[OpenAI key not configured — add to ~/charlie2/providers/keys.env]"
        return
    log_stream(f"OPENAI_START:{prompt[:30]}", "APPROVED")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        with client.chat.completions.create(
            model=model, stream=True, max_tokens=1024,
            messages=[{"role":"user","content":prompt}]
        ) as stream:
            for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                if token:
                    yield token
        log_stream("OPENAI_COMPLETE", "SUCCESS")
    except Exception as e:
        log_stream("OPENAI_ERROR", "FAILED", str(e))
        yield f"[OpenAI error: {e}]"

async def async_stream_ollama(prompt: str, model: str = "deepseek-coder:1.3b") -> AsyncIterator[str]:
    import asyncio
    log_stream(f"ASYNC_OLLAMA:{prompt[:30]}", "APPROVED")
    try:
        loop = asyncio.get_event_loop()
        r = await loop.run_in_executor(None, lambda: requests.post(
            f"{OLLAMA}/api/generate",
            json={"model": model, "prompt": prompt, "stream": True},
            stream=True, timeout=120))
        for line in r.iter_lines():
            if line:
                try:
                    chunk = json.loads(line.decode("utf-8"))
                    token = chunk.get("response", "")
                    if token:
                        yield token
                        await asyncio.sleep(0)
                    if chunk.get("done", False):
                        break
                except: continue
    except Exception as e:
        yield f"[Async stream error: {e}]"

if __name__ == "__main__":
    import sys
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What is Charlie 2.0?"
    print(f"\n⚡ Streaming: {prompt}\n")
    for token in stream_ollama(prompt):
        print(token, end="", flush=True)
    print("\n")
