# Hugging Face Spaces entry point
from huggingface_app import app

# This file serves as the entry point for Hugging Face Spaces
# The FastAPI app with Hugging Face specific configurations is imported from huggingface_app.py
# Hugging Face will automatically detect and run this app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)