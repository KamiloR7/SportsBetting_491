from fastapi import FastAPI

app = FastAPI(
    title="Sports Match Prediction API",
    description="Backend API for the CPSC 491 sports match-prediction application.",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}
