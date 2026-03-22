from fastapi import FastAPI
from app.routers.cvrcc_confidence_engine import router as cvrcc_router

app = FastAPI(title="Charlie 2.0 / RightsFrames Intelligence")
app.include_router(cvrcc_router)


@app.get("/")
def root():
    return {"status": "ok", "app": "Charlie 2.0"}
