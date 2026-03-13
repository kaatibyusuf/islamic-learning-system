from fastapi import FastAPI

app = FastAPI(title="Islamic Learning Intelligence System")


@app.get("/health")
def health_check():
    return {"status": "ok"}