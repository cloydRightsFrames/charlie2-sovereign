from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sqlite3, time, hashlib, os, platform

app = FastAPI(title="Charlie 2.0 Sovereign Cloud API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB = os.environ.get("DB_PATH", "charlie2.db")

def db():
    con = sqlite3.connect(DB, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.executescript("""
        CREATE TABLE IF NOT EXISTS judicial_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT, verdict TEXT, hash TEXT, ts REAL);
        CREATE TABLE IF NOT EXISTS legislative_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy TEXT, status TEXT, constitution TEXT, hash TEXT, ts REAL);
        CREATE TABLE IF NOT EXISTS executive_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT, path TEXT, payload TEXT, result TEXT, hash TEXT, ts REAL);
    """)
    con.commit(); con.close()

def audit_hash(data):
    return hashlib.sha256(f"{data}{time.time()}".encode()).hexdigest()[:16]

@app.on_event("startup")
async def startup():
    init_db()
    con = db(); h = audit_hash("CLOUD_BOOT")
    con.execute("INSERT INTO judicial_log VALUES(NULL,'CLOUD_BOOT','APPROVED',?,?)",(h,time.time()))
    con.execute("INSERT INTO legislative_log VALUES(NULL,'Cloud API online','ACTIVE','CONSTITUTION_v1',?,?)",(h,time.time()))
    con.execute("INSERT INTO executive_log VALUES(NULL,'CLOUD_BOOT','/',NULL,'SUCCESS',?,?)",(h,time.time()))
    con.commit(); con.close()

@app.middleware("http")
async def tri_branch(request: Request, call_next):
    start = time.time()
    verdict = "BLOCKED" if any(x in request.url.path for x in ["/admin/drop","/delete-all"]) else "APPROVED"
    response = await call_next(request)
    dur = round(time.time()-start, 4)
    con = db(); h = audit_hash(str(request.url))
    con.execute("INSERT INTO judicial_log VALUES(NULL,?,?,?,?)",
        (f"REQ:{request.url.path}", verdict, h, time.time()))
    con.execute("INSERT INTO executive_log VALUES(NULL,?,?,NULL,?,?,?)",
        ("HTTP", str(request.url.path), f"status:{response.status_code} dur:{dur}s", h, time.time()))
    con.commit(); con.close()
    if verdict == "BLOCKED":
        return JSONResponse({"error":"BLOCKED by Judicial branch"}, status_code=403)
    return response

@app.get("/")
async def root():
    return {
        "system": "CHARLIE 2.0 SOVEREIGN CLOUD",
        "status": "ONLINE",
        "node": "railway",
        "platform": platform.machine(),
        "branches": ["judicial","legislative","executive"],
        "ts": time.time()
    }

@app.get("/health")
async def health():
    con = db()
    j = con.execute("SELECT COUNT(*) FROM judicial_log").fetchone()[0]
    l = con.execute("SELECT COUNT(*) FROM legislative_log").fetchone()[0]
    e = con.execute("SELECT COUNT(*) FROM executive_log").fetchone()[0]
    con.close()
    return {"status":"OK","node":"railway","judicial":j,"legislative":l,"executive":e,"ts":time.time()}

@app.get("/judicial")
async def judicial():
    con = db()
    rows = [dict(r) for r in con.execute(
        "SELECT * FROM judicial_log ORDER BY ts DESC LIMIT 100").fetchall()]
    con.close(); return {"branch":"judicial","log":rows,"count":len(rows)}

@app.get("/legislative")
async def legislative():
    con = db()
    rows = [dict(r) for r in con.execute(
        "SELECT * FROM legislative_log ORDER BY ts DESC LIMIT 50").fetchall()]
    con.close(); return {"branch":"legislative","constitutions":rows}

@app.post("/legislative/enact")
async def enact(payload: dict):
    policy = payload.get("policy",""); h = audit_hash(policy)
    con = db()
    con.execute("INSERT INTO legislative_log VALUES(NULL,?,?,?,?,?)",
        (policy,"ACTIVE",payload.get("constitution","CUSTOM"),h,time.time()))
    con.commit(); con.close()
    return {"enacted":policy,"hash":h,"status":"ACTIVE"}

@app.get("/executive")
async def executive():
    con = db()
    rows = [dict(r) for r in con.execute(
        "SELECT * FROM executive_log ORDER BY ts DESC LIMIT 100").fetchall()]
    con.close(); return {"branch":"executive","log":rows}

@app.get("/audit")
async def audit():
    con = db()
    j = [dict(r) for r in con.execute("SELECT * FROM judicial_log ORDER BY ts DESC LIMIT 50").fetchall()]
    l = [dict(r) for r in con.execute("SELECT * FROM legislative_log ORDER BY ts DESC LIMIT 25").fetchall()]
    e = [dict(r) for r in con.execute("SELECT * FROM executive_log ORDER BY ts DESC LIMIT 50").fetchall()]
    con.close(); return {"judicial":j,"legislative":l,"executive":e}

@app.post("/infer")
async def infer(payload: dict):
    prompt = payload.get("prompt","")
    h = audit_hash(prompt)
    con = db()
    con.execute("INSERT INTO judicial_log VALUES(NULL,?,?,?,?)",
        (f"INFER:{prompt[:40]}","APPROVED",h,time.time()))
    con.commit(); con.close()
    return {
        "response": f"Charlie 2.0 Cloud received: {prompt[:100]}",
        "node": "railway",
        "hash": h,
        "note": "Connect Ollama phone node for full LLM inference"
    }

@app.get("/cluster")
async def cluster():
    return {
        "cloud_node": {"status":"ONLINE","platform":platform.machine(),"node":"railway"},
        "phone_node": {"status":"UNKNOWN","note":"Connect via WireGuard for phone telemetry"},
        "routing": "CLOUD"
    }
