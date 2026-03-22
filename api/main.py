from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sqlite3, time, hashlib, os, platform, subprocess

app = FastAPI(title="Charlie 2.0 Sovereign API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
DB = os.path.expanduser("~/charlie2/charlie2.db")

def db():
    con = sqlite3.connect(DB, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

def audit_hash(data):
    return hashlib.sha256(f"{data}{time.time()}".encode()).hexdigest()[:16]

@app.on_event("startup")
async def startup():
    con = db()
    h = audit_hash("BOOT")
    con.execute("INSERT INTO judicial_log VALUES (NULL,'SYSTEM_BOOT','APPROVED',?,?)",(h,time.time()))
    con.execute("INSERT INTO executive_log VALUES (NULL,'BOOT','/',NULL,'SUCCESS',?,?)",(h,time.time()))
    con.commit(); con.close()

@app.middleware("http")
async def tri_branch(request: Request, call_next):
    start = time.time()
    verdict = "BLOCKED" if any(x in request.url.path for x in ["/admin/drop","/delete-all"]) else "APPROVED"
    response = await call_next(request)
    dur = round(time.time()-start,4)
    con = db(); h = audit_hash(str(request.url))
    con.execute("INSERT INTO judicial_log VALUES (NULL,?,?,?,?)",(f"REQ:{request.url.path}",verdict,h,time.time()))
    con.execute("INSERT INTO executive_log VALUES (NULL,?,?,NULL,?,?,?)",("HTTP",str(request.url.path),f"status:{response.status_code} dur:{dur}s",h,time.time()))
    con.commit(); con.close()
    if verdict=="BLOCKED": return JSONResponse({"error":"BLOCKED"},status_code=403)
    return response

@app.get("/")
async def root():
    return {"system":"CHARLIE 2.0","status":"ONLINE","branches":["judicial","legislative","executive"],
            "uptime":subprocess.getoutput("uptime -p"),"platform":platform.machine()}

@app.get("/health")
async def health():
    mem = subprocess.getoutput("free -h | awk 'NR==2{print $3\"/\"$2}'")
    return {"status":"OK","memory":mem,"ts":time.time()}

@app.get("/judicial")
async def judicial():
    con = db()
    rows = [dict(r) for r in con.execute("SELECT * FROM judicial_log ORDER BY ts DESC LIMIT 100").fetchall()]
    con.close(); return {"branch":"judicial","log":rows,"count":len(rows)}

@app.get("/legislative")
async def legislative():
    con = db()
    rows = [dict(r) for r in con.execute("SELECT * FROM legislative_log ORDER BY ts DESC LIMIT 50").fetchall()]
    con.close(); return {"branch":"legislative","constitutions":rows}

@app.post("/legislative/enact")
async def enact(payload: dict):
    policy=payload.get("policy",""); h=audit_hash(policy)
    con=db(); con.execute("INSERT INTO legislative_log VALUES (NULL,?,?,?,?,?)",(policy,"ACTIVE",payload.get("constitution","CUSTOM"),h,time.time()))
    con.commit(); con.close(); return {"enacted":policy,"hash":h}

@app.get("/executive")
async def executive():
    con=db()
    rows=[dict(r) for r in con.execute("SELECT * FROM executive_log ORDER BY ts DESC LIMIT 100").fetchall()]
    con.close(); return {"branch":"executive","log":rows}

@app.get("/audit")
async def audit():
    con=db()
    j=[dict(r) for r in con.execute("SELECT * FROM judicial_log ORDER BY ts DESC LIMIT 25").fetchall()]
    l=[dict(r) for r in con.execute("SELECT * FROM legislative_log ORDER BY ts DESC LIMIT 25").fetchall()]
    e=[dict(r) for r in con.execute("SELECT * FROM executive_log ORDER BY ts DESC LIMIT 25").fetchall()]
    con.close(); return {"judicial":j,"legislative":l,"executive":e}

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json as _json

try:
    app.mount("/static", StaticFiles(
        directory=os.path.expanduser("~/charlie2/dashboard")), name="static")
except: pass

@app.get("/dashboard", include_in_schema=False)
async def dashboard():
    return FileResponse(os.path.expanduser("~/charlie2/dashboard/index.html"))

@app.get("/sensor")
async def sensor_data():
    try:
        with open(os.path.expanduser("~/charlie2/sensor_context.json")) as f:
            return _json.load(f)
    except:
        return {"error": "sensor feed not active"}

# Multi-Provider AI Endpoint
@app.post("/ai/chat")
async def ai_chat(payload: dict):
    prompt = payload.get("prompt", "")
    preferred = payload.get("provider", "auto")
    if not prompt: return {"error": "prompt required"}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("mp",
            os.path.expanduser("~/charlie2/providers/multi_provider.py"))
        mp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mp)
        return mp.route(prompt, preferred)
    except Exception as e:
        return {"error": str(e), "provider": "none"}

@app.get("/ai/providers")
async def ai_providers():
    available = ["ollama"]
    try:
        with open(os.path.expanduser("~/charlie2/providers/keys.env")) as f:
            content = f.read()
        for name, key in [("anthropic","ANTHROPIC_API_KEY"),
                          ("openai","OPENAI_API_KEY"),
                          ("gemini","GEMINI_API_KEY")]:
            if key in content:
                val = content.split(key+"=")[1].split("\n")[0].strip()
                if val and "your_" not in val:
                    available.append(name)
    except: pass
    return {"available": available, "routing": "judicial-governed"}

# RAG Memory Endpoints
@app.post("/memory/remember")
async def memory_remember(payload: dict):
    text = payload.get("text", "")
    meta = payload.get("metadata", {})
    if not text: return {"error": "text required"}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("rag",
            os.path.expanduser("~/charlie2/memory/rag_engine.py"))
        rag = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rag)
        doc_id = rag.remember(text, meta)
        return {"stored": True, "id": doc_id, "text": text[:80]}
    except Exception as e:
        return {"error": str(e)}

@app.post("/memory/recall")
async def memory_recall(payload: dict):
    query = payload.get("query", "")
    n = payload.get("n", 5)
    if not query: return {"error": "query required"}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("rag",
            os.path.expanduser("~/charlie2/memory/rag_engine.py"))
        rag = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rag)
        results = rag.recall(query, n=n)
        return {"query": query, "results": results, "count": len(results)}
    except Exception as e:
        return {"error": str(e)}

@app.get("/memory/status")
async def memory_status():
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("rag",
            os.path.expanduser("~/charlie2/memory/rag_engine.py"))
        rag = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rag)
        mem  = rag.get_collection("charlie2_memory").count()
        gov  = rag.get_collection("governance").count()
        code = rag.get_collection("codebase").count()
        return {"memory": mem, "governance": gov,
                "codebase": code, "total": mem+gov+code}
    except Exception as e:
        return {"error": str(e)}

@app.post("/ai/rag-chat")
async def rag_chat_endpoint(payload: dict):
    prompt = payload.get("prompt", "")
    if not prompt: return {"error": "prompt required"}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("rag",
            os.path.expanduser("~/charlie2/memory/rag_engine.py"))
        rag = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rag)
        enhanced_prompt, ctx_count = rag.rag_chat(prompt)
        mp_spec = importlib.util.spec_from_file_location("mp",
            os.path.expanduser("~/charlie2/providers/multi_provider.py"))
        mp = importlib.util.module_from_spec(mp_spec)
        mp_spec.loader.exec_module(mp)
        result = mp.route(enhanced_prompt)
        result["context_memories_used"] = ctx_count
        result["rag_enhanced"] = True
        rag.remember(f"Q: {prompt} A: {result['response'][:200]}",
            {"source": "conversation", "provider": result.get("provider","")})
        return result
    except Exception as e:
        return {"error": str(e)}

# Web UI Route
@app.get("/ui", include_in_schema=False)
async def webui():
    return FileResponse(os.path.expanduser("~/charlie2/webui/index.html"))

@app.get("/ui/{path:path}", include_in_schema=False)
async def webui_path(path: str):
    return FileResponse(os.path.expanduser("~/charlie2/webui/index.html"))

# Auto-Commit Agent Endpoints
import subprocess as _sub

@app.post("/agent/run")
async def agent_run(payload: dict = {}):
    dry = payload.get("dry_run", False)
    push = payload.get("push", False)
    try:
        args = ["python",
            os.path.expanduser("~/charlie2/agent/coding_agent.py"),
            "dry" if dry else "run"]
        if push: args.append("--push")
        result = _sub.run(args, capture_output=True, text=True, timeout=60)
        return {"output": result.stdout, "error": result.stderr,
                "code": result.returncode}
    except Exception as e:
        return {"error": str(e)}

@app.get("/agent/status")
async def agent_status():
    try:
        result = _sub.run(
            ["python", os.path.expanduser("~/charlie2/agent/coding_agent.py"),
             "status"],
            capture_output=True, text=True, timeout=15)
        running = bool(_sub.run(["pgrep","-f","coding_agent.py watch"],
            capture_output=True).stdout.strip())
        return {"output": result.stdout, "watch_running": running}
    except Exception as e:
        return {"error": str(e)}

@app.post("/agent/watch/start")
async def agent_watch_start():
    try:
        running = bool(_sub.run(["pgrep","-f","coding_agent.py watch"],
            capture_output=True).stdout.strip())
        if running:
            return {"status": "already running"}
        _sub.Popen(
            ["nohup","python",
             os.path.expanduser("~/charlie2/agent/coding_agent.py"),
             "watch","--push"],
            stdout=open(os.path.expanduser("~/charlie2/logs/agent.log"),"a"),
            stderr=_sub.STDOUT)
        return {"status": "started", "log": "~/charlie2/logs/agent.log"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/agent/watch/stop")
async def agent_watch_stop():
    try:
        _sub.run(["pkill","-f","coding_agent.py watch"], capture_output=True)
        return {"status": "stopped"}
    except Exception as e:
        return {"error": str(e)}

# PromptForge Endpoints
@app.post("/promptforge/review")
async def pf_review(payload: dict):
    target = payload.get("target", "")
    provider = payload.get("provider", "auto")
    phases = payload.get("phases", [1, 2, 4, 11])
    if not target: return {"error": "target required"}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("pf",
            os.path.expanduser("~/charlie2/promptforge/engine.py"))
        pf = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pf)
        results, report = pf.run_pipeline(target, provider, phases)
        return {"phases_run": len(results), "report": report[:3000],
                "results": [{"phase":r["phase"],"name":r["name"],
                             "summary":r["response"][:200]} for r in results]}
    except Exception as e:
        return {"error": str(e)}

@app.post("/promptforge/full")
async def pf_full(payload: dict):
    target = payload.get("target", "")
    provider = payload.get("provider", "auto")
    if not target: return {"error": "target required"}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("pf",
            os.path.expanduser("~/charlie2/promptforge/engine.py"))
        pf = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pf)
        results, report = pf.run_pipeline(target, provider)
        return {"phases_run": len(results), "report_preview": report[:2000],
                "saved_to": "~/charlie2/promptforge/outputs/"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/promptforge/self-review")
async def pf_self():
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("pf",
            os.path.expanduser("~/charlie2/promptforge/engine.py"))
        pf = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pf)
        api_path = os.path.expanduser("~/charlie2/api/main.py")
        results, report = pf.quick_review(api_path)
        return {"phases_run": len(results),
                "verdict": results[-1]["response"][:300] if results else "no result",
                "report_preview": report[:1500]}
    except Exception as e:
        return {"error": str(e)}

@app.get("/promptforge/outputs")
async def pf_outputs():
    out_dir = os.path.expanduser("~/charlie2/promptforge/outputs")
    try:
        files = sorted(os.listdir(out_dir), reverse=True)[:10]
        return {"outputs": files, "directory": out_dir}
    except:
        return {"outputs": [], "directory": out_dir}

# Constitutional AI Enforcement
@app.post("/ai/constitutional-chat")
async def constitutional_chat(payload: dict):
    prompt   = payload.get("prompt", "")
    provider = payload.get("provider", "auto")
    if not prompt: return {"error": "prompt required"}
    try:
        import importlib.util
        mp_spec = importlib.util.spec_from_file_location("mp",
            os.path.expanduser("~/charlie2/providers/multi_provider.py"))
        mp = importlib.util.module_from_spec(mp_spec)
        mp_spec.loader.exec_module(mp)
        result = mp.route(prompt, provider)
        raw_response = result.get("response","")

        ef_spec = importlib.util.spec_from_file_location("enforcer",
            os.path.expanduser("~/charlie2/constitution/enforcer.py"))
        ef = importlib.util.module_from_spec(ef_spec)
        ef_spec.loader.exec_module(ef)
        final, verdict, violations, seal = ef.enforce(prompt, raw_response, provider)

        return {
            "response": final,
            "provider": result.get("provider",""),
            "constitutional_verdict": verdict,
            "violations": len(violations),
            "seal": seal,
            "routed_via": "constitutional-tri-branch"
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/constitution")
async def get_constitution():
    try:
        with open(os.path.expanduser("~/charlie2/constitution/constitution.json")) as f:
            import json as _json2
            return _json2.load(f)
    except Exception as e:
        return {"error": str(e)}

@app.post("/constitution/test")
async def test_constitution(payload: dict):
    prompt   = payload.get("prompt", "test")
    response = payload.get("response", "test response")
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("enforcer",
            os.path.expanduser("~/charlie2/constitution/enforcer.py"))
        ef = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ef)
        final, verdict, violations, seal = ef.enforce(prompt, response)
        return {"verdict": verdict, "violations": len(violations),
                "seal": seal, "response_preview": final[:200]}
    except Exception as e:
        return {"error": str(e)}
