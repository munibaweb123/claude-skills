---
title: Physical AI Book Backend
emoji: 🤖
colorFrom: blue
colorTo: red
sdk: docker
runtime: gpu
app_file: app.py
pinned: false
license: mit
---

# Physical AI Book Backend

This is a RAG (Retrieval-Augmented Generation) chatbot backend for a digital book reader with personalization features. The backend is built with FastAPI and includes:

- Book content ingestion and storage in Qdrant vector database
- Chat functionality with RAG capabilities
- User authentication integration
- Personalization engine for adaptive content
- Chapter personalization features
- User preference management

## Environment Variables

The application requires the following environment variables to be set:

- `OPENAI_API_KEY`: Your OpenAI API key
- `QDRANT_URL`: Your Qdrant Cloud URL
- `QDRANT_API_KEY`: Your Qdrant API key
- `AUTH_SERVER_URL`: URL of the Node.js auth server (defaults to http://localhost:7860)

## API Endpoints

- `/health` - Health check endpoint
- `/ingest` - Ingest book content into the vector database
- `/chat` - Chat with the RAG system
- `/api/content/personalized` - Get personalized content
- Various personalization and user preference endpoints

## Deployment

This backend can be deployed as a Hugging Face Space using the Docker runtime. Make sure to set the required secrets in the Space settings.