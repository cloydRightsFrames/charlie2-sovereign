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
