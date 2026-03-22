#!/usr/bin/env python3
import subprocess, requests, time, os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
app = FastAPI(title="Charlie 2.0 Inference Router")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
PHONE = "http://127.0.0.1:8000"
PC    = "http://10.99.0.2:8001"
def get_load():
    try:
        out = subprocess.run(['uptime'], capture_output=True, text=True).stdout
        return float(out.split('load average:')[1].split(',')[0].strip())
    except: return 0.0
def pc_online():
    try: return requests.get(f"{PC}/health", timeout=2).status_code == 200
    except: return False
@app.get("/cluster-status")
async def cluster_status():
    load = get_load(); pc_up = pc_online()
    return {"phone": {"node":"ARM64-Termux","status":"ONLINE","load":load,"endpoint":PHONE},
            "pc": {"node":"Windows11-x86_64","status":"ONLINE" if pc_up else "OFFLINE","endpoint":PC},
            "routing": "PC" if (pc_up and load > 1.5) else "PHONE"}
@app.post("/infer")
async def route_infer(payload: dict):
    load = get_load(); pc_up = pc_online()
    target, node = (PC,"PC") if (pc_up and load > 1.5) else (PHONE,"PHONE")
    try:
        resp = requests.post(f"{target}/infer", json=payload, timeout=60)
        return {"node": node, "load": load, "result": resp.json()}
    except Exception as e:
        if node == "PC":
            try:
                resp = requests.post(f"{PHONE}/infer", json=payload, timeout=60)
                return {"node":"PHONE-FALLBACK","result":resp.json()}
            except: pass
        return {"error": str(e), "node": node}
@app.get("/health")
async def health(): return {"status":"OK","router":"ONLINE","ts":time.time()}
if __name__ == "__main__": uvicorn.run(app, host="0.0.0.0", port=8002, log_level="warning")
