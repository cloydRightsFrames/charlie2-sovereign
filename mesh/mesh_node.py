#!/usr/bin/env python3
import os, json, time, hashlib, sqlite3, requests, socket, threading, secrets
C2       = os.path.expanduser("~/charlie2")
DB       = os.path.join(C2, "charlie2.db")
MESH_DIR = os.path.join(C2, "mesh")
NODES_F  = os.path.join(MESH_DIR, "nodes", "known_nodes.json")
API_URL  = "http://127.0.0.1:8000"
NODE_ID  = hashlib.sha256(f"RIGHTSFRAMES:{socket.gethostname()}:{secrets.token_hex(8)}".encode()).hexdigest()[:16]

def audit_hash(data):
    return hashlib.sha256(f"{data}{time.time()}".encode()).hexdigest()[:16]

def log_mesh(event, verdict, detail=""):
    try:
        con = sqlite3.connect(DB); h = audit_hash(event)
        con.execute("INSERT INTO judicial_log VALUES(NULL,?,?,?,?)",
            (f"MESH:{event}", verdict, h, time.time()))
        con.execute("INSERT INTO executive_log VALUES(NULL,?,NULL,NULL,?,?,?)",
            (event, detail[:200], h, time.time()))
        con.commit(); con.close()
    except: pass

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"

def load_nodes():
    try:
        with open(NODES_F) as f: return json.load(f)
    except: return {}

def save_nodes(nodes):
    with open(NODES_F, "w") as f: json.dump(nodes, f, indent=2)

def get_governance_count():
    try:
        con = sqlite3.connect(DB)
        n = con.execute("SELECT COUNT(*) FROM judicial_log").fetchone()[0]
        con.close(); return n
    except: return 0

def get_tor_onion():
    try:
        with open(os.path.join(C2, "tor_service", "hostname")) as f:
            return f.read().strip()
    except: return ""

def save_self():
    nodes = load_nodes()
    nodes[NODE_ID] = {
        "node_id":    NODE_ID,
        "ip":         get_local_ip(),
        "wireguard":  "10.99.0.1",
        "api_port":   8000,
        "device":     "Samsung Galaxy A16",
        "arch":       "aarch64",
        "owner":      "cloydRightsFrames",
        "system":     "Charlie 2.0 Sovereign",
        "joined":     time.strftime("%Y-%m-%d %H:%M:%S"),
        "last_seen":  time.time(),
        "governance_count": get_governance_count(),
        "tor_onion":  get_tor_onion(),
        "capabilities": ["inference","governance","rag","constitutional","debate","zkp","streaming"]
    }
    save_nodes(nodes); return nodes[NODE_ID]

def ping_node(info, timeout=5):
    ip = info.get("wireguard", info.get("ip",""))
    port = info.get("api_port", 8000)
    try:
        r = requests.get(f"http://{ip}:{port}/health", timeout=timeout)
        return r.status_code == 200
    except: return False

def mesh_inference(prompt, provider="auto"):
    nodes = load_nodes()
    local_load = os.getloadavg()[0] if hasattr(os,'getloadavg') else 0
    log_mesh(f"MESH_INFER:{prompt[:30]}", "APPROVED", f"load:{local_load:.1f}")
    try:
        r = requests.post(f"{API_URL}/ai/chat",
            json={"prompt": prompt, "provider": provider}, timeout=60)
        result = r.json()
        result["mesh_node"]    = NODE_ID
        result["mesh_routing"] = "local"
        result["mesh_size"]    = len(nodes)
        log_mesh("MESH_LOCAL_INFERENCE", "SUCCESS", result.get("provider",""))
        return result
    except:
        return {"response": "Mesh inference failed", "mesh_routing": "error"}

def consensus_check(record_hash, nodes):
    confirmations = 1
    total = len(nodes)
    responses = {NODE_ID: "local"}
    for nid, info in nodes.items():
        if nid == NODE_ID: continue
        ip = info.get("wireguard", info.get("ip",""))
        port = info.get("api_port", 8000)
        try:
            r = requests.post(f"http://{ip}:{port}/mesh/verify-record",
                json={"hash": record_hash}, timeout=5)
            d = r.json()
            if d.get("verified"):
                confirmations += 1; responses[nid] = "confirmed"
            else: responses[nid] = "not_found"
        except: responses[nid] = "offline"
    pct = round(confirmations/total*100, 1) if total > 0 else 0
    return {"record_hash": record_hash, "confirmations": confirmations,
            "total_nodes": total, "consensus_pct": pct,
            "consensus": pct >= 51, "responses": responses}

def generate_mesh_proof():
    nodes = load_nodes(); gov = get_governance_count()
    mesh_hash = hashlib.sha256(f"{NODE_ID}:{len(nodes)}:{gov}:{time.time()}".encode()).hexdigest()
    proof = {
        "proof_type": "MESH_PARTICIPATION", "node_id": NODE_ID,
        "mesh_size": len(nodes), "governance_records": gov,
        "tor_onion": get_tor_onion(), "local_ip": get_local_ip(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "mesh_hash": mesh_hash,
        "sovereign_seal": hashlib.sha256(f"RIGHTSFRAMES:{mesh_hash}:{gov}".encode()).hexdigest(),
        "nodes": {nid: {"ip": i.get("ip",""), "device": i.get("device",""),
                        "governance_count": i.get("governance_count",0)}
                  for nid, i in nodes.items()}
    }
    path = os.path.join(MESH_DIR, "consensus", f"mesh_proof_{int(time.time())}.json")
    with open(path, "w") as f: json.dump(proof, f, indent=2)
    log_mesh("MESH_PROOF_GENERATED", "APPROVED", f"nodes:{len(nodes)} records:{gov}")
    return proof

def discovery_broadcast():
    node_info = save_self()
    msg = json.dumps({"type": "CHARLIE2_NODE", "node": node_info, "version": "2.0.0"}).encode()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(msg, ("255.255.255.255", 8199)); sock.close()
        log_mesh("DISCOVERY_BROADCAST", "APPROVED", node_info.get("ip",""))
    except: pass

def discovery_listen(stop_event):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", 8199)); sock.settimeout(2)
        while not stop_event.is_set():
            try:
                data, addr = sock.recvfrom(4096)
                msg = json.loads(data.decode())
                if msg.get("type") == "CHARLIE2_NODE":
                    node = msg.get("node",{}); nid = node.get("node_id","")
                    if nid and nid != NODE_ID:
                        nodes = load_nodes(); node["last_seen"] = time.time()
                        nodes[nid] = node; save_nodes(nodes)
                        log_mesh(f"NODE_DISCOVERED:{nid[:8]}", "APPROVED", addr[0])
                        print(f"  ⚡ Node discovered: {nid[:8]} @ {addr[0]}")
            except: continue
        sock.close()
    except: pass

def run_mesh_daemon():
    print(f"⚡ Mesh Daemon starting — Node: {NODE_ID}")
    save_self()
    stop = threading.Event()
    threading.Thread(target=discovery_listen, args=(stop,), daemon=True).start()
    log_mesh("MESH_DAEMON_START", "APPROVED", NODE_ID)
    cycle = 0
    while True:
        try:
            cycle += 1
            if cycle % 6 == 0: discovery_broadcast()
            nodes = load_nodes()
            online = 0
            for nid, info in list(nodes.items()):
                if nid == NODE_ID: online += 1; continue
                alive = ping_node(info, timeout=3)
                nodes[nid]["status"] = "online" if alive else "offline"
                if alive:
                    nodes[nid]["last_seen"] = time.time(); online += 1
            save_nodes(nodes)
            if cycle % 10 == 0:
                print(f"  Mesh: {online}/{len(nodes)} nodes | cycle:{cycle} | records:{get_governance_count()}")
            time.sleep(10)
        except KeyboardInterrupt:
            stop.set(); print("\n⚡ Mesh daemon stopped"); break
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "daemon"
    if cmd == "daemon":   run_mesh_daemon()
    elif cmd == "proof":  print(json.dumps(generate_mesh_proof(), indent=2))
    elif cmd == "nodes":
        nodes = load_nodes()
        print(f"Mesh nodes: {len(nodes)}")
        for nid, info in nodes.items():
            print(f"  {nid[:8]} | {info.get('ip','')} | {info.get('status','?')} | {info.get('governance_count',0)} records")
    elif cmd == "self":   print(json.dumps(save_self(), indent=2))
