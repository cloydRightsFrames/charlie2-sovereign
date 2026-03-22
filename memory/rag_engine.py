#!/usr/bin/env python3
"""
Charlie 2.0 — RAG Memory Engine
Persistent vector memory using ChromaDB
Indexes: conversations, codebase, governance logs
"""
import os, time, hashlib, json, sqlite3
from pathlib import Path

CHROMA_DIR = os.path.expanduser("~/charlie2/memory/chroma")
DB         = os.path.expanduser("~/charlie2/charlie2.db")

def get_client():
    import chromadb
    return chromadb.PersistentClient(path=CHROMA_DIR)

def get_collection(name="charlie2_memory"):
    client = get_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"})

def embed(texts):
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model.encode(texts).tolist()
    except Exception as e:
        # Fallback: simple hash embedding
        result = []
        for t in texts:
            h = hashlib.md5(t.encode()).digest()
            result.append([float(b)/255.0 for b in h] * 24)
        return result

def remember(text, metadata=None, collection="charlie2_memory"):
    """Store a memory in ChromaDB"""
    col = get_collection(collection)
    doc_id = hashlib.sha256(f"{text}{time.time()}".encode()).hexdigest()[:16]
    meta = {"ts": str(time.time()), "source": "charlie2"}
    if metadata: meta.update(metadata)
    embeddings = embed([text])
    col.add(documents=[text], embeddings=embeddings,
            metadatas=[meta], ids=[doc_id])
    return doc_id

def recall(query, n=5, collection="charlie2_memory"):
    """Retrieve relevant memories"""
    try:
        col = get_collection(collection)
        count = col.count()
        if count == 0: return []
        embeddings = embed([query])
        results = col.query(query_embeddings=embeddings,
                           n_results=min(n, count))
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        return [{"text": d, "meta": m} for d, m in zip(docs, metas)]
    except Exception as e:
        return []

def index_governance_logs():
    """Index tri-branch governance chain into memory"""
    try:
        con = sqlite3.connect(DB)
        con.row_factory = sqlite3.Row
        indexed = 0
        for table in ["judicial_log", "legislative_log", "executive_log"]:
            rows = con.execute(
                f"SELECT * FROM {table} ORDER BY ts DESC LIMIT 50").fetchall()
            for row in rows:
                d = dict(row)
                event = d.get("event", d.get("policy", d.get("action", "")))
                if event:
                    remember(event,
                        {"source": table, "hash": d.get("hash",""),
                         "ts": str(d.get("ts",""))},
                        collection="governance")
                    indexed += 1
        con.close()
        return indexed
    except Exception as e:
        return 0

def index_codebase(path=None):
    """Index Charlie 2.0 codebase into memory"""
    if path is None:
        path = os.path.expanduser("~/charlie2")
    indexed = 0
    extensions = [".py", ".kt", ".md", ".sh", ".json"]
    skip_dirs = {"__pycache__", ".git", "build", "node_modules",
                 "chroma", "models", "llama.cpp", "whisper.cpp"}
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fname in files:
            if any(fname.endswith(ext) for ext in extensions):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", errors="ignore") as f:
                        content = f.read()
                    if len(content) > 50:
                        chunks = [content[i:i+500]
                                  for i in range(0, min(len(content),2000), 400)]
                        for chunk in chunks:
                            remember(chunk,
                                {"source": "codebase", "file": fpath,
                                 "ts": str(time.time())},
                                collection="codebase")
                            indexed += 1
                except: pass
    return indexed

def rag_chat(prompt, context_n=3):
    """Enhanced chat with RAG context injection"""
    memories = recall(prompt, n=context_n)
    gov_mems = recall(prompt, n=2, collection="governance")
    code_mems = recall(prompt, n=2, collection="codebase")

    context_parts = []
    if memories:
        context_parts.append("Relevant memories:\n" +
            "\n".join(f"- {m['text'][:200]}" for m in memories))
    if gov_mems:
        context_parts.append("Governance context:\n" +
            "\n".join(f"- {m['text'][:150]}" for m in gov_mems))
    if code_mems:
        context_parts.append("Code context:\n" +
            "\n".join(f"- {m['text'][:200]}" for m in code_mems))

    if context_parts:
        enhanced = f"""Context from Charlie 2.0 memory:
{chr(10).join(context_parts)}

Current question: {prompt}

Answer based on the context above when relevant:"""
    else:
        enhanced = prompt

    return enhanced, len(memories) + len(gov_mems) + len(code_mems)

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "index":
        print("Indexing governance logs...")
        n1 = index_governance_logs()
        print(f"Indexed {n1} governance records")
        print("Indexing codebase...")
        n2 = index_codebase()
        print(f"Indexed {n2} code chunks")
        print(f"Total: {n1+n2} memories stored")

    elif cmd == "recall":
        query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Charlie 2.0"
        results = recall(query)
        print(f"Top {len(results)} memories for: {query}")
        for i, r in enumerate(results):
            print(f"\n[{i+1}] {r['text'][:200]}")
            print(f"     source: {r['meta'].get('source','?')}")

    elif cmd == "remember":
        text = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if text:
            doc_id = remember(text, {"source": "manual"})
            print(f"Remembered: [{doc_id}] {text[:60]}")

    elif cmd == "status":
        try:
            col = get_collection("charlie2_memory")
            gov = get_collection("governance")
            code = get_collection("codebase")
            print(f"Memory:     {col.count()} entries")
            print(f"Governance: {gov.count()} entries")
            print(f"Codebase:   {code.count()} entries")
        except Exception as e:
            print(f"Status error: {e}")
