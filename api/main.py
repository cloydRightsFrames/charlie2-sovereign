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

# Multi-Agent Debate Endpoints
@app.post("/ai/debate")
async def ai_debate(payload: dict):
    prompt   = payload.get("prompt", "")
    provider = payload.get("provider", "auto")
    if not prompt: return {"error": "prompt required"}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("debate",
            os.path.expanduser("~/charlie2/debate/debate_engine.py"))
        db_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(db_mod)
        result = db_mod.quick_debate(prompt, provider)
        return result
    except Exception as e:
        return {"error": str(e)}

@app.post("/ai/debate-review")
async def debate_review(payload: dict):
    prompt   = payload.get("prompt", "")
    response = payload.get("response", "")
    provider = payload.get("provider", "auto")
    if not prompt or not response:
        return {"error": "prompt and response required"}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("debate",
            os.path.expanduser("~/charlie2/debate/debate_engine.py"))
        db_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(db_mod)
        result = db_mod.run_debate(prompt, response, provider)
        return result
    except Exception as e:
        return {"error": str(e)}

@app.post("/ai/supreme-chat")
async def supreme_chat(payload: dict):
    """Constitutional enforcement + Debate council + RAG — the full sovereign stack"""
    prompt   = payload.get("prompt", "")
    provider = payload.get("provider", "auto")
    if not prompt: return {"error": "prompt required"}
    try:
        import importlib.util

        # Step 1: RAG enhanced prompt
        rag_spec = importlib.util.spec_from_file_location("rag",
            os.path.expanduser("~/charlie2/memory/rag_engine.py"))
        rag = importlib.util.module_from_spec(rag_spec)
        rag_spec.loader.exec_module(rag)
        enhanced_prompt, ctx = rag.rag_chat(prompt)

        # Step 2: Get initial AI response
        mp_spec = importlib.util.spec_from_file_location("mp",
            os.path.expanduser("~/charlie2/providers/multi_provider.py"))
        mp = importlib.util.module_from_spec(mp_spec)
        mp_spec.loader.exec_module(mp)
        ai_result = mp.route(enhanced_prompt, provider)
        initial_response = ai_result.get("response", "")

        # Step 3: Constitutional enforcement
        ef_spec = importlib.util.spec_from_file_location("enforcer",
            os.path.expanduser("~/charlie2/constitution/enforcer.py"))
        ef = importlib.util.module_from_spec(ef_spec)
        ef_spec.loader.exec_module(ef)
        const_response, const_verdict, violations, seal = ef.enforce(
            prompt, initial_response, provider)

        # Step 4: Debate council on constitutionally-cleared response
        db_spec = importlib.util.spec_from_file_location("debate",
            os.path.expanduser("~/charlie2/debate/debate_engine.py"))
        db_mod = importlib.util.module_from_spec(db_spec)
        db_spec.loader.exec_module(db_mod)
        debate_result = db_mod.run_debate(prompt, const_response, provider)

        # Step 5: Store final response in memory
        try:
            rag.remember(
                f"Q: {prompt} A: {debate_result['final_response'][:200]}",
                {"source": "supreme-chat", "verdict": debate_result["verdict"]})
        except: pass

        return {
            "response":              debate_result["final_response"],
            "provider":              ai_result.get("provider", ""),
            "pipeline":              "RAG→AI→Constitutional→Debate",
            "rag_memories_used":     ctx,
            "constitutional_verdict": const_verdict,
            "constitutional_violations": len(violations),
            "debate_verdict":        debate_result["verdict"],
            "debate_hash":           debate_result["debate_hash"],
            "debate_rounds":         3,
            "sovereign_seal":        seal
        }
    except Exception as e:
        return {"error": str(e), "pipeline": "supreme-chat"}

# Autonomous Self-Improvement Endpoints
@app.post("/selfimprove/run")
async def selfimprove_run(payload: dict = {}):
    submit_pr = payload.get("submit_pr", False)
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("si",
            os.path.expanduser("~/charlie2/selfimprove/self_improve.py"))
        si = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(si)
        result = si.run_cycle(submit_pr=submit_pr)
        return result
    except Exception as e:
        return {"error": str(e)}

@app.post("/selfimprove/watch/start")
async def selfimprove_watch_start():
    try:
        import subprocess as _sub2
        running = bool(_sub2.run(
            ["pgrep","-f","self_improve.py watch"],
            capture_output=True).stdout.strip())
        if running:
            return {"status": "already running"}
        _sub2.Popen(
            ["nohup","python",
             os.path.expanduser("~/charlie2/selfimprove/self_improve.py"),
             "watch"],
            stdout=open(
                os.path.expanduser("~/charlie2/logs/selfimprove.log"),"a"),
            stderr=_sub2.STDOUT)
        return {"status": "started", "interval": "6h",
                "log": "~/charlie2/logs/selfimprove.log"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/selfimprove/status")
async def selfimprove_status():
    try:
        import glob, json as _json5, subprocess as _sub3
        runs = glob.glob(
            os.path.expanduser("~/charlie2/selfimprove/history/*.json"))
        proposals = glob.glob(
            os.path.expanduser("~/charlie2/selfimprove/proposals/*.json"))
        patches   = glob.glob(
            os.path.expanduser("~/charlie2/selfimprove/patches/*.json"))
        running   = bool(_sub3.run(
            ["pgrep","-f","self_improve.py watch"],
            capture_output=True).stdout.strip())
        latest = {}
        if runs:
            with open(sorted(runs)[-1]) as f:
                latest = _json5.load(f)
        return {
            "cycles_run":      len(runs),
            "proposals_total": len(proposals),
            "patches_written": len(patches),
            "watch_running":   running,
            "latest_cycle":    latest
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/selfimprove/proposals")
async def selfimprove_proposals():
    try:
        import glob, json as _json6
        files = sorted(glob.glob(
            os.path.expanduser("~/charlie2/selfimprove/analysis/*.json")))
        if not files:
            return {"proposals": [], "message": "No cycles run yet"}
        with open(files[-1]) as f:
            data = _json6.load(f)
        return {
            "timestamp":  data.get("timestamp",""),
            "proposals":  data.get("proposals",[]),
            "findings":   len(data.get("findings",[])),
            "audit_count": data.get("audit_count",0)
        }
    except Exception as e:
        return {"error": str(e)}

# Real-Time Streaming Endpoints
from fastapi.responses import StreamingResponse, HTMLResponse
import asyncio as _asyncio
import json as _json_s

@app.post("/ai/stream")
async def ai_stream(payload: dict):
    prompt   = payload.get("prompt", "")
    provider = payload.get("provider", "auto")
    if not prompt:
        return {"error": "prompt required"}

    async def event_gen():
        import importlib.util as _ilu, hashlib as _hs, requests as _rq

        yield f"data: {_json_s.dumps({'event':'start','provider':provider})}\n\n"

        full = ""

        # Try Ollama native stream first
        try:
            test = _rq.get("http://127.0.0.1:11434/api/tags", timeout=2)
            if test.status_code == 200:
                yield f"data: {_json_s.dumps({'event':'provider','provider':'ollama:local'})}\n\n"
                spec = _ilu.spec_from_file_location("se",
                    os.path.expanduser("~/charlie2/streaming/stream_engine.py"))
                se = _ilu.module_from_spec(spec)
                spec.loader.exec_module(se)
                async for token in se.async_stream_ollama(prompt):
                    full += token
                    yield f"data: {_json_s.dumps({'event':'token','token':token,'provider':'ollama:local'})}\n\n"
                    await _asyncio.sleep(0)
                h = _hs.sha256(full.encode()).hexdigest()[:16]
                yield f"data: {_json_s.dumps({'event':'done','provider':'ollama:local','governance_hash':h,'total':len(full)})}\n\n"
                return
        except: pass

        # Fallback: regular AI then word-by-word simulate
        try:
            mp_spec = _ilu.spec_from_file_location("mp",
                os.path.expanduser("~/charlie2/providers/multi_provider.py"))
            mp = _ilu.module_from_spec(mp_spec)
            mp_spec.loader.exec_module(mp)
            result  = mp.route(prompt, provider)
            resp    = result.get("response", "")
            prov    = result.get("provider", "auto")
            yield f"data: {_json_s.dumps({'event':'provider','provider':prov})}\n\n"
            words = resp.split(" ")
            for i, word in enumerate(words):
                token = word + (" " if i < len(words)-1 else "")
                full += token
                yield f"data: {_json_s.dumps({'event':'token','token':token,'provider':prov})}\n\n"
                await _asyncio.sleep(0.025)
            h = _hs.sha256(full.encode()).hexdigest()[:16]
            yield f"data: {_json_s.dumps({'event':'done','provider':prov,'governance_hash':h,'total':len(full)})}\n\n"
        except Exception as e:
            yield f"data: {_json_s.dumps({'event':'error','error':str(e)})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",
            "Access-Control-Allow-Origin": "*"
        })

@app.get("/stream", include_in_schema=False)
async def stream_ui():
    try:
        with open(os.path.expanduser("~/charlie2/streaming/stream_ui.html")) as f:
            return HTMLResponse(f.read())
    except Exception as e:
        return HTMLResponse(f"<pre>Stream UI error: {e}</pre>")

@app.post("/ai/stream/constitutional")
async def stream_constitutional(payload: dict):
    """Stream with constitutional enforcement per completed response"""
    prompt   = payload.get("prompt", "")
    provider = payload.get("provider", "auto")
    if not prompt:
        return {"error": "prompt required"}

    async def const_gen():
        import importlib.util as _ilu, hashlib as _hs

        yield f"data: {_json_s.dumps({'event':'start','mode':'constitutional-stream'})}\n\n"

        full = ""
        prov = provider

        # Stream tokens
        try:
            import requests as _rq
            test = _rq.get("http://127.0.0.1:11434/api/tags", timeout=2)
            if test.status_code == 200:
                spec = _ilu.spec_from_file_location("se",
                    os.path.expanduser("~/charlie2/streaming/stream_engine.py"))
                se = _ilu.module_from_spec(spec)
                spec.loader.exec_module(se)
                prov = "ollama:local"
                yield f"data: {_json_s.dumps({'event':'provider','provider':prov})}\n\n"
                async for token in se.async_stream_ollama(prompt):
                    full += token
                    yield f"data: {_json_s.dumps({'event':'token','token':token})}\n\n"
                    await _asyncio.sleep(0)
        except:
            mp_spec = _ilu.spec_from_file_location("mp",
                os.path.expanduser("~/charlie2/providers/multi_provider.py"))
            mp = _ilu.module_from_spec(mp_spec)
            mp_spec.loader.exec_module(mp)
            result = mp.route(prompt, provider)
            full = result.get("response","")
            prov = result.get("provider","auto")
            for word in full.split(" "):
                yield f"data: {_json_s.dumps({'event':'token','token':word+' '})}\n\n"
                await _asyncio.sleep(0.02)

        # Constitutional review on completed response
        try:
            ef_spec = _ilu.spec_from_file_location("ef",
                os.path.expanduser("~/charlie2/constitution/enforcer.py"))
            ef = _ilu.module_from_spec(ef_spec)
            ef_spec.loader.exec_module(ef)
            final, verdict, violations, seal = ef.enforce(prompt, full, prov)
            h = _hs.sha256(final.encode()).hexdigest()[:16]
            yield f"data: {_json_s.dumps({'event':'done','provider':prov,'governance_hash':h,'constitutional_verdict':verdict,'violations':len(violations),'seal':seal})}\n\n"
        except Exception as e:
            h = _hs.sha256(full.encode()).hexdigest()[:16]
            yield f"data: {_json_s.dumps({'event':'done','provider':prov,'governance_hash':h,'constitutional_note':str(e)})}\n\n"

    return StreamingResponse(
        const_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",
            "Access-Control-Allow-Origin": "*"
        })

# Federated Mesh Network Endpoints
@app.get("/mesh/status")
async def mesh_status():
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("mesh",
            os.path.expanduser("~/charlie2/mesh/mesh_node.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        nodes = m.load_nodes()
        online = sum(1 for n in nodes.values()
                     if n.get("status","online") == "online")
        return {
            "node_id":    m.NODE_ID,
            "mesh_size":  len(nodes),
            "online":     online,
            "offline":    len(nodes) - online,
            "governance_records": m.get_governance_count(),
            "tor_onion":  m.get_tor_onion(),
            "nodes":      nodes
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/mesh/nodes")
async def mesh_nodes():
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("mesh",
            os.path.expanduser("~/charlie2/mesh/mesh_node.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return {"nodes": m.load_nodes(), "this_node": m.NODE_ID}
    except Exception as e:
        return {"error": str(e)}

@app.post("/mesh/join")
async def mesh_join(payload: dict):
    node_info = payload.get("node", {})
    if not node_info.get("node_id"):
        return {"error": "node_id required"}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("mesh",
            os.path.expanduser("~/charlie2/mesh/mesh_node.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        nodes = m.load_nodes()
        node_info["last_seen"] = __import__("time").time()
        node_info["status"]    = "online"
        nodes[node_info["node_id"]] = node_info
        m.save_nodes(nodes)
        m.log_mesh(f"NODE_JOINED:{node_info['node_id'][:8]}",
                   "APPROVED", node_info.get("ip",""))
        return {"status": "joined", "mesh_size": len(nodes),
                "welcome": "Charlie 2.0 Sovereign Mesh"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/mesh/infer")
async def mesh_infer(payload: dict):
    prompt   = payload.get("prompt", "")
    provider = payload.get("provider", "auto")
    if not prompt: return {"error": "prompt required"}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("mesh",
            os.path.expanduser("~/charlie2/mesh/mesh_node.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m.mesh_inference(prompt, provider)
    except Exception as e:
        return {"error": str(e)}

@app.post("/mesh/proof")
async def mesh_proof():
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("mesh",
            os.path.expanduser("~/charlie2/mesh/mesh_node.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m.generate_mesh_proof()
    except Exception as e:
        return {"error": str(e)}

@app.post("/mesh/consensus")
async def mesh_consensus(payload: dict):
    record_hash = payload.get("hash", "")
    if not record_hash: return {"error": "hash required"}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("mesh",
            os.path.expanduser("~/charlie2/mesh/mesh_node.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        nodes = m.load_nodes()
        return m.consensus_check(record_hash, nodes)
    except Exception as e:
        return {"error": str(e)}

@app.get("/mesh/chain-summary")
async def mesh_chain_summary():
    try:
        import sqlite3 as _sq
        con = _sq.connect(os.path.expanduser("~/charlie2/charlie2.db"))
        j = con.execute("SELECT COUNT(*) FROM judicial_log").fetchone()[0]
        e = con.execute("SELECT COUNT(*) FROM executive_log").fetchone()[0]
        latest = con.execute(
            "SELECT hash,ts FROM judicial_log ORDER BY ts DESC LIMIT 1"
        ).fetchone()
        con.close()
        return {
            "count":       j + e,
            "judicial":    j,
            "executive":   e,
            "latest_hash": latest[0] if latest else "",
            "latest_ts":   latest[1] if latest else 0
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/mesh/verify-record")
async def mesh_verify_record(payload: dict):
    record_hash = payload.get("hash", "")
    if not record_hash: return {"verified": False}
    try:
        import sqlite3 as _sq
        con = _sq.connect(os.path.expanduser("~/charlie2/charlie2.db"))
        row = con.execute(
            "SELECT id FROM judicial_log WHERE hash=?",
            (record_hash,)).fetchone()
        con.close()
        return {"verified": bool(row), "hash": record_hash}
    except Exception as e:
        return {"verified": False, "error": str(e)}

@app.post("/mesh/broadcast")
async def mesh_broadcast():
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("mesh",
            os.path.expanduser("~/charlie2/mesh/mesh_node.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        m.discovery_broadcast()
        return {"status": "broadcast sent", "node_id": m.NODE_ID}
    except Exception as e:
        return {"error": str(e)}

# Living Constitutional AI Endpoints
@app.post("/constitution/evolve")
async def constitution_evolve():
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("lc",
            os.path.expanduser("~/charlie2/living_constitution/living_engine.py"))
        lc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lc)
        results = lc.run_evolution_cycle()
        return {
            "amendments_enacted": len(results),
            "amendments": results,
            "version": lc.load_constitution().get("version","?"),
            "system": "Living Constitutional AI"
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/constitution/living/status")
async def constitution_living_status():
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("lc",
            os.path.expanduser("~/charlie2/living_constitution/living_engine.py"))
        lc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lc)
        return lc.get_status()
    except Exception as e:
        return {"error": str(e)}

@app.get("/constitution/living/history")
async def constitution_living_history():
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("lc",
            os.path.expanduser("~/charlie2/living_constitution/living_engine.py"))
        lc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lc)
        history = lc.load_history()
        return {
            "total_amendments": len(history),
            "history": history[-20:],
            "constitution_version": lc.load_constitution().get("version","?")
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/constitution/living/articles")
async def constitution_living_articles():
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("lc",
            os.path.expanduser("~/charlie2/living_constitution/living_engine.py"))
        lc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lc)
        const = lc.load_constitution()
        return {
            "version":  const.get("version","1.0"),
            "articles": const.get("articles",[]),
            "is_living": True
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/constitution/living/schedule")
async def constitution_schedule():
    try:
        import subprocess as _sub
        running = bool(_sub.run(
            ["pgrep","-f","living_engine.py"],
            capture_output=True).stdout.strip())
        if running:
            return {"status": "already scheduled"}
        _sub.Popen(
            ["nohup","python","-c",
             "import time,sys; sys.path.insert(0,''); "
             "exec(open('/data/data/com.termux/files/home/charlie2/living_constitution/living_engine.py').read()); "
             "[(__import__('time').sleep(21600), run_evolution_cycle()) for _ in iter(int, 1)]"],
            stdout=open(os.path.expanduser(
                "~/charlie2/logs/living_const.log"),"a"),
            stderr=_sub.STDOUT)
        return {"status": "scheduled every 6h",
                "log": "~/charlie2/logs/living_const.log"}
    except Exception as e:
        return {"error": str(e)}
