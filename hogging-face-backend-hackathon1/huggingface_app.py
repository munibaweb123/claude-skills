import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import the main app components
from main import app, startup_event, shutdown_event

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add lifespan to handle startup and shutdown events gracefully
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await startup_event()
        logger.info("Application started successfully")
        yield
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        # Don't prevent the app from starting even if external services are unavailable
        logger.info("Continuing to start server despite initialization errors")
        yield
    finally:
        try:
            await shutdown_event()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Override the main app's lifespan
app.router.lifespan_context = lifespan

# Add a simple root endpoint for Hugging Face health check
@app.get("/")
async def root():
    return {"message": "Physical AI Book Backend is running", "status": "healthy"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)