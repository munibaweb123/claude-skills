import os
from fastapi import FastAPI

app = FastAPI()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
API_HOST = os.getenv("API_HOST", "0.0.0.0")

@app.get("/")
def read_root():
    return {"message": "Hello from Docker!", "log_level": LOG_LEVEL}

@app.get("/health")
def health_check():
    return {"status": "healthy"}