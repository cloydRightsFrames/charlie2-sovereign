FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn aiofiles requests
COPY cloud_api/main.py ./cloud_api/main.py
RUN python -c "import sqlite3; c=sqlite3.connect('charlie2.db'); c.executescript('''CREATE TABLE IF NOT EXISTS judicial_log(id INTEGER PRIMARY KEY AUTOINCREMENT,event TEXT,verdict TEXT,hash TEXT,ts REAL);CREATE TABLE IF NOT EXISTS legislative_log(id INTEGER PRIMARY KEY AUTOINCREMENT,policy TEXT,status TEXT,constitution TEXT,hash TEXT,ts REAL);CREATE TABLE IF NOT EXISTS executive_log(id INTEGER PRIMARY KEY AUTOINCREMENT,action TEXT,path TEXT,payload TEXT,result TEXT,hash TEXT,ts REAL);'''); c.commit()"
EXPOSE 8000
ENV PORT=8000
CMD ["python","-m","uvicorn","cloud_api.main:app","--host","0.0.0.0","--port","8000","--workers","2"]
