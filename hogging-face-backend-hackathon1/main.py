import os
import asyncio
import logging
import uuid # Added import for UUID generation
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient, models

from datetime import datetime
import httpx # Import httpx

from services.personalization_engine import PersonalizationEngine

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Pydantic Settings Model ---
class Settings(BaseSettings):
    OPENAI_API_KEY: str = Field(..., description="OpenAI API Key")
    QDRANT_URL: str = Field(..., description="Qdrant Cloud URL")
    QDRANT_API_KEY: str = Field(..., description="Qdrant API Key")
    AUTH_SERVER_URL: str = Field("http://localhost:7860", description="URL of the Node.js auth server")


    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings() # Instantiate settings

# --- FastAPI App Initialization ---
app = FastAPI(
    title="RAG Chatbot Backend",
    description="FastAPI backend for a RAG Chatbot embedded in a digital book reader.",
    version="1.0.0",
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global Clients and Connection Pools ---
openai_client: Optional[AsyncOpenAI] = None
qdrant_client: Optional[AsyncQdrantClient] = None
http_client: Optional[httpx.AsyncClient] = None # Add httpx client
personalization_engine: Optional[PersonalizationEngine] = None

QDRANT_COLLECTION_NAME = "book_chunks"
EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_CHAT_MODEL = "gpt-4o" # or "gpt-3.5-turbo"

# --- Authentication Dependency ---
async def authenticate_user(authorization: str = Header(...)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated: Missing or invalid Authorization header")

    session_id = authorization.split(" ")[1] # Extract session ID from Bearer token

    try:
        # Call the Node.js auth server to verify the session
        response = await http_client.post(
            f"{settings.AUTH_SERVER_URL}/api/auth/verify-session",
            json={"token": session_id} # Pass session ID (token) in body
        )
        response.raise_for_status() # Raise for HTTP errors (4xx or 5xx)

        user_data = response.json()
        if not user_data.get("success"):
            raise HTTPException(status_code=401, detail="Not authenticated: Invalid session")

        return user_data["user"] # Return user info if authenticated
    except httpx.HTTPStatusError as e:
        logger.error(f"Auth server responded with error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=401, detail="Not authenticated: Session verification failed")
    except httpx.RequestError as e:
        logger.error(f"Could not connect to auth server: {e}")
        raise HTTPException(status_code=500, detail="Authentication service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during authentication")


async def get_user_background(user_id: str, auth_token: str) -> Dict[str, Any]:
    """
    Retrieve user's background information from the auth server.

    Args:
        user_id: The ID of the user
        auth_token: The authentication token for the request

    Returns:
        Dictionary containing user's background information
    """
    try:
        # Call the Node.js auth server to get user background information
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        response = await http_client.get(
            f"{settings.AUTH_SERVER_URL}/api/auth/user/background",
            headers=headers
        )
        response.raise_for_status() # Raise for HTTP errors (4xx or 5xx)

        user_background = response.json()
        return user_background
    except httpx.HTTPStatusError as e:
        logger.error(f"Auth server responded with error when fetching background: {e.response.status_code} - {e.response.text}")
        # Return empty profile if background info is not available
        return {}
    except httpx.RequestError as e:
        logger.error(f"Could not connect to auth server when fetching background: {e}")
        # Return empty profile if we can't reach the auth server
        return {}
    except Exception as e:
        logger.error(f"Unexpected error when fetching user background: {e}", exc_info=True)
        # Return empty profile on any error
        return {}


# --- Pydantic Models ---
class IngestRequest(BaseModel):
    raw_text: str
    chapter_title: str
    page_numbers: Optional[str] = None # Assuming page_numbers can be a string range or similar

class ChatRequest(BaseModel):
    user_query: str
    selected_text: Optional[str] = None
    mode: Optional[str] = "standard" # "standard" or "socratic"

class ChatResponse(BaseModel):
    response: str
    # Optionally, include source information here
    # sources: List[Dict[str, Any]] = []

class PersonalizedContentItem(BaseModel):
    id: str
    title: str
    description: str
    level: str
    tags: List[str]
    relevanceScore: float
    url: str

class PersonalizedContentResponse(BaseModel):
    content: List[PersonalizedContentItem]
    total: int
    page: int
    limit: int


# --- Chapter Personalization Models ---
class ChapterPersonalizationRequest(BaseModel):
    activate: bool
    preferences: Optional[Dict[str, Any]] = None


class ChapterPersonalizationResponse(BaseModel):
    success: bool
    chapterId: str
    personalizationActive: bool
    adaptationsApplied: List[str]
    message: str


# --- Personalization Preferences Models ---
class PersonalizationPreferencesRequest(BaseModel):
    complexityLevel: Optional[str] = None
    preferredExamples: Optional[List[str]] = None
    focusAreas: Optional[List[str]] = None
    enabledFeatures: Optional[Dict[str, bool]] = None


class PersonalizationPreferencesResponse(BaseModel):
    success: bool
    message: str
    preferences: Dict[str, Any]
    updatedAt: Optional[str] = None


class PersonalizationPreferencesGetResponse(BaseModel):
    complexityLevel: Optional[str] = None
    preferredExamples: Optional[List[str]] = None
    focusAreas: Optional[List[str]] = None
    enabledFeatures: Optional[Dict[str, bool]] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class UserBackgroundResponse(BaseModel):
    userId: str
    softwareExperienceLevel: Optional[str] = None
    hardwareExperienceLevel: Optional[str] = None
    preferredDevelopmentEnvironments: Optional[List[str]] = None
    technicalSkills: Optional[List[str]] = None
    hardwareSpecs: Optional[str] = None
    updatedAt: str

# --- System Prompts ---
SYSTEM_PROMPTS = {
    "standard": (
        "You are a helpful assistant for a digital book reader. "
        "Answer the user's question based strictly on the provided context from the book. "
        "If the answer cannot be found in the context, state that you don't have enough information from the book. "
        "Do not hallucinate content. Be concise and to the point."
    ),
    "socratic": "" # Will be loaded from file
}

def load_socratic_prompt():
    try:
        with open("agent/socratic_tutor.md", "r", encoding="utf-8") as f:
            SYSTEM_PROMPTS["socratic"] = f.read()
        logger.info("Loaded Socratic Tutor prompt from agent/socratic_tutor.md")
    except Exception as e:
        logger.error(f"Failed to load Socratic Tutor prompt: {e}")
        # Fallback to a basic Socratic prompt if file fails
        SYSTEM_PROMPTS["socratic"] = (
            "You are a Socratic Tutor. Guide the user to the answer using the provided context. "
            "Do not provide the direct answer immediately. Ask a guiding question."
        )



# --- FastAPI Lifecycle Events ---
@app.on_event("startup")
async def startup_event():
    """
    Initialize clients and database connections on app startup.
    """
    global openai_client, qdrant_client, http_client, personalization_engine

    logger.info("Initializing application resources...")

    try:
        openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        qdrant_client = AsyncQdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
        http_client = httpx.AsyncClient() # Initialize httpx client
        personalization_engine = PersonalizationEngine() # Initialize personalization engine

        # Load system prompts
        load_socratic_prompt()

        # Ensure Qdrant collection exists
        try:
            await qdrant_client.get_collection(QDRANT_COLLECTION_NAME)
            logger.info(f"Qdrant collection '{QDRANT_COLLECTION_NAME}' exists.")
        except Exception:
            logger.info(f"Qdrant collection '{QDRANT_COLLECTION_NAME}' not found. Creating...")
            await qdrant_client.create_collection(
                collection_name=QDRANT_COLLECTION_NAME,
                vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
            )
            logger.info(f"Qdrant collection '{QDRANT_COLLECTION_NAME}' created.")



        logger.info("Application resources initialized successfully.")

    except Exception as e:
        logger.error(f"Failed to initialize resources: {e}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """
    Close clients and database connections on app shutdown.
    """
    global qdrant_client, http_client

    logger.info("Shutting down application resources...")

    if qdrant_client:
        await qdrant_client.close()
        logger.info("Qdrant client closed.")
    
    if http_client:
        await http_client.aclose()
        logger.info("HTTP client closed.")


    logger.info("Application resources shut down.")

# --- RAG Helper Functions ---
async def generate_embeddings(text: str) -> List[float]:
    """
    Generates embeddings for the given text using OpenAI's embedding model.
    """
    try:
        response = await openai_client.embeddings.create(
            input=text,
            model=EMBEDDING_MODEL
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate embeddings.")

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Simple text chunking function. In a real-world scenario, a more sophisticated
    chunking strategy (e.g., based on sentences or paragraphs) would be used.
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
        if start >= len(text): # Ensure the last chunk is processed even if it's smaller than chunk_size
            break
    return chunks



async def upsert_qdrant(
    chunks_with_metadata: List[Dict[str, Any]],
    embeddings: List[List[float]]
):
    """
    Upserts chunks and their embeddings into Qdrant.
    `chunks_with_metadata` should contain {'text': str, 'chapter_title': str, 'page_numbers': Optional[str]}
    """
    if not chunks_with_metadata or not embeddings:
        return

    points = []
    for i, chunk_data in enumerate(chunks_with_metadata):
        # Generate a UUID for each point, as there's no Postgres ID anymore
        point_id = str(uuid.uuid4())
        payload = {
            "text": chunk_data["text"],
            "chapter_title": chunk_data["chapter_title"],
            "page_numbers": chunk_data.get("page_numbers") # Include page numbers if available
        }
        points.append(
            models.PointStruct(
                id=point_id,
                vector=embeddings[i],
                payload=payload
            )
        )
    
    try:
        await qdrant_client.upsert(
            collection_name=QDRANT_COLLECTION_NAME,
            points=points,
            wait=True
        )
        logger.info(f"Upserted {len(points)} points into Qdrant collection '{QDRANT_COLLECTION_NAME}'.")
    except Exception as e:
        logger.error(f"Error upserting to Qdrant: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upsert vectors to Qdrant.")

async def search_qdrant(query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
    """
    Searches Qdrant for the top relevant book chunks.
    """
    try:
        search_result = await qdrant_client.query_points(
            collection_name=QDRANT_COLLECTION_NAME,
            query=query_embedding,
            limit=limit,
            with_payload=True # Retrieve the full payload (metadata)
        )
        return [{"text": hit.payload["text"], "chapter_title": hit.payload["chapter_title"]} for hit in search_result.points if hit.payload]
    except Exception as e:
        logger.error(f"Error searching Qdrant: {e}", exc_info=True)
        return [] # Return empty list on error, allowing chat to proceed with less context

# --- FastAPI Endpoints ---
@app.post("/ingest", response_model=Dict[str, str])
async def ingest_data(request: IngestRequest, user: Dict[str, Any] = Depends(authenticate_user)):
    """
    Ingests raw text (e.g., a book chapter), chunks it, generates embeddings,
    and stores it in Qdrant.
    """
    logger.info(f"Ingesting data for chapter: {request.chapter_title}")

    # 1. Chunk the raw text
    chunks = chunk_text(request.raw_text)
    if not chunks:
        raise HTTPException(status_code=400, detail="No chunks generated from the provided text.")

    # Prepare chunks for embedding and storage
    chunks_to_process: List[Dict[str, Any]] = []
    for chunk_content in chunks:
        chunks_to_process.append({
            "text": chunk_content,
            "chapter_title": request.chapter_title,
            "page_numbers": request.page_numbers # Include page numbers if available
        })

    # 2. Generate embeddings for all chunks
    all_embeddings = []
    for chunk_data in chunks_to_process:
        embedding = await generate_embeddings(chunk_data["text"])
        all_embeddings.append(embedding)

    # 3. Upsert vectors into Qdrant
    if all_embeddings:
        await upsert_qdrant(chunks_to_process, all_embeddings)
    else:
        logger.warning(f"No embeddings generated for chapter: {request.chapter_title}")

    logger.info(f"Successfully ingested {len(chunks)} chunks for chapter: {request.chapter_title}")
    return {"message": f"Successfully ingested {len(chunks)} chunks for chapter: {request.chapter_title}"}


@app.post("/chat", response_model=ChatResponse)
async def chat_with_rag(request: ChatRequest, user: Dict[str, Any] = Depends(authenticate_user)):
    """
    Answers user queries using Retrieval-Augmented Generation (RAG).
    Prioritizes `selected_text` if provided.
    """
    logger.info(f"Received chat query: '{request.user_query}' with selected_text: {'Yes' if request.selected_text else 'No'}")

    context_chunks: List[str] = []
    system_prompt_parts: List[str] = []

    # Scenario B: Selected Text provided
    if request.selected_text:
        system_prompt_parts.append(f"Immediate Context (User Selected Text): {request.selected_text}")
        logger.info("Prioritizing user-selected text as immediate context.")

    # Scenario A: Standard RAG (or supplementing selected text with more context)
    try:
        query_embedding = await generate_embeddings(request.user_query)
        relevant_qdrant_results = await search_qdrant(query_embedding)

        if relevant_qdrant_results:
            context_chunks.extend([res["text"] for res in relevant_qdrant_results])
            logger.info(f"Retrieved {len(relevant_qdrant_results)} relevant chunks from Qdrant.")
        else:
            logger.warning("Qdrant search returned no relevant results.")

    except HTTPException:
        logger.error("Skipping Qdrant search due to embedding generation failure.")
    except Exception as e:
        logger.error(f"An unexpected error occurred during Qdrant search: {e}", exc_info=True)

    # Construct the final system prompt
    if system_prompt_parts: # If selected text was provided
        system_prompt_parts.append("\n\nAdditional Context from Book (Vector Search):")
        if context_chunks:
            system_prompt_parts.append("\n".join(f"- {chunk}" for chunk in context_chunks))
        else:
            system_prompt_parts.append("No additional relevant context found.")
        system_prompt_content = "\n\n".join(system_prompt_parts)
    elif context_chunks: # Only vector search results
        system_prompt_content = "Context from Book (Vector Search):\n" + "\n".join(f"- {chunk}" for chunk in context_chunks)
    else: # No context found at all
        system_prompt_content = "No relevant context from the book was found."
        logger.warning("No context (neither selected text nor vector search) available for the query.")


    # --- OpenAI Chat Completion ---

    # Determine base system prompt
    mode = request.mode if request.mode in SYSTEM_PROMPTS else "standard"
    base_system_prompt = SYSTEM_PROMPTS[mode]

    messages = [
        {"role": "system", "content": (
            f"{base_system_prompt}"
            f"\n\n{system_prompt_content}"
        )},
        {"role": "user", "content": request.user_query}
    ]

    try:
        chat_completion = await openai_client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            messages=messages,
            temperature=0.0 # Keep responses factual
        )
        response_content = chat_completion.choices[0].message.content
        logger.info(f"OpenAI chat completion successful for query: '{request.user_query}'")
        return ChatResponse(response=response_content)

    except Exception as e:
        logger.error(f"Error calling OpenAI Chat Completion API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get response from AI model.")


@app.get("/api/content/personalized", response_model=PersonalizedContentResponse)
async def get_personalized_content(
    request: Request,
    limit: int = 10,
    page: int = 1,
    user: Dict[str, Any] = Depends(authenticate_user)
):
    """
    Retrieve personalized content based on user's background information.
    """
    global personalization_engine

    if not personalization_engine:
        raise HTTPException(status_code=500, detail="Personalization engine not initialized")

    try:
        # Get user's background information
        auth_header = request.headers.get("authorization", "")
        user_background = await get_user_background(user["id"], auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else "")

        # Create some sample content for demonstration
        # In a real application, this would come from a database or content management system
        sample_content = [
            {
                "id": "content-1",
                "title": "Getting Started with React for Beginners",
                "description": "A beginner-friendly guide to React",
                "level": "beginner",
                "tags": ["react", "javascript", "frontend"],
                "url": "/docs/react/beginners-guide"
            },
            {
                "id": "content-2",
                "title": "Advanced TypeScript Patterns",
                "description": "Deep dive into advanced TypeScript concepts",
                "level": "advanced",
                "tags": ["typescript", "javascript"],
                "url": "/docs/typescript/advanced-patterns"
            },
            {
                "id": "content-3",
                "title": "Docker for Developers",
                "description": "Learn how to containerize your applications",
                "level": "intermediate",
                "tags": ["docker", "devops"],
                "url": "/docs/docker/getting-started"
            },
            {
                "id": "content-4",
                "title": "Introduction to Machine Learning",
                "description": "Basic concepts and algorithms in ML",
                "level": "beginner",
                "tags": ["machine-learning", "python", "data-science"],
                "url": "/docs/ml/intro"
            },
            {
                "id": "content-5",
                "title": "Building Microservices with FastAPI",
                "description": "Design and implement scalable microservices",
                "level": "advanced",
                "tags": ["python", "fastapi", "microservices"],
                "url": "/docs/microservices/fastapi"
            }
        ]

        # Use the personalization engine to get personalized content
        offset = (page - 1) * limit
        personalized_result = personalization_engine.get_personalized_content(
            user_profile=user_background,
            all_content=sample_content,
            limit=limit,
            offset=offset
        )

        # Convert to the expected response format
        content_items = []
        for item in personalized_result['content']:
            content_items.append(PersonalizedContentItem(
                id=item['id'],
                title=item['title'],
                description=item['description'],
                level=item.get('level', ''),
                tags=item.get('tags', []),
                relevanceScore=item.get('relevanceScore', 0.0),
                url=item.get('url', '')
            ))

        return PersonalizedContentResponse(
            content=content_items,
            total=personalized_result['total'],
            page=personalized_result['page'],
            limit=personalized_result['limit']
        )

    except Exception as e:
        logger.error(f"Error retrieving personalized content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve personalized content")


# --- Chapter Personalization Endpoints ---
@app.post("/api/chapters/{chapter_id}/personalize", response_model=ChapterPersonalizationResponse)
async def toggle_chapter_personalization(
    chapter_id: str,
    request: ChapterPersonalizationRequest,
    user: Dict[str, Any] = Depends(authenticate_user)
):
    """
    Toggle personalization for a specific chapter.

    Args:
        chapter_id: The ID of the chapter
        request: Request body containing activation flag and preferences
        user: Authenticated user information

    Returns:
        Chapter personalization state
    """
    global personalization_engine

    if not personalization_engine:
        raise HTTPException(status_code=500, detail="Personalization engine not initialized")

    try:
        # Get user's background information to use for personalization
        auth_header = request.headers.get("authorization", "")
        token = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else ""
        user_background = await get_user_background(user["id"], token)

        # Update the personalization state for this chapter
        personalization_state = personalization_engine.update_chapter_personalization_state(
            user_id=user["id"],
            chapter_id=chapter_id,
            is_active=request.activate,
            adaptations_applied=[],  # Will be populated based on user profile
            override_settings=request.preferences or {}
        )

        # Determine adaptations based on user profile and preferences
        adaptations = []
        if request.activate:
            # Add adaptations based on user profile
            if user_background.get('softwareExperienceLevel'):
                adaptations.append('complexity-adjustment')
            if user_background.get('technicalSkills'):
                adaptations.append('example-substitution')
            if user_background.get('preferredDevelopmentEnvironments'):
                adaptations.append('environment-focus')

        return ChapterPersonalizationResponse(
            success=True,
            chapterId=chapter_id,
            personalizationActive=request.activate,
            adaptationsApplied=adaptations,
            message=f"Personalization {'activated' if request.activate else 'deactivated'} for chapter {chapter_id}"
        )
    except Exception as e:
        logger.error(f"Error toggling chapter personalization: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update chapter personalization")


@app.get("/api/chapters/{chapter_id}/personalize", response_model=ChapterPersonalizationResponse)
async def get_chapter_personalization_state(
    chapter_id: str,
    user: Dict[str, Any] = Depends(authenticate_user)
):
    """
    Get the personalization state for a specific chapter.

    Args:
        chapter_id: The ID of the chapter
        user: Authenticated user information

    Returns:
        Chapter personalization state
    """
    global personalization_engine

    if not personalization_engine:
        raise HTTPException(status_code=500, detail="Personalization engine not initialized")

    try:
        # Get the personalization state for this chapter
        state = personalization_engine.get_chapter_personalization_state(
            user_id=user["id"],
            chapter_id=chapter_id
        )

        return ChapterPersonalizationResponse(
            success=True,
            chapterId=chapter_id,
            personalizationActive=state.get('isActive', False),
            adaptationsApplied=state.get('adaptationsApplied', []),
            message="Personalization state retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error getting chapter personalization state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve chapter personalization state")


# --- Personalization Preferences Endpoints ---
@app.put("/api/user/personalization/preferences", response_model=PersonalizationPreferencesResponse)
async def update_user_personalization_preferences(
    request: PersonalizationPreferencesRequest,
    user: Dict[str, Any] = Depends(authenticate_user)
):
    """
    Update user's global personalization preferences.

    Args:
        request: Request body containing preferences to update
        user: Authenticated user information

    Returns:
        Updated preferences with success message
    """
    global personalization_engine

    if not personalization_engine:
        raise HTTPException(status_code=500, detail="Personalization engine not initialized")

    try:
        # Prepare the preferences dict from the request
        preferences_to_update = {}
        if request.complexityLevel is not None:
            preferences_to_update['complexityLevel'] = request.complexityLevel
        if request.preferredExamples is not None:
            preferences_to_update['preferredExamples'] = request.preferredExamples
        if request.focusAreas is not None:
            preferences_to_update['focusAreas'] = request.focusAreas
        if request.enabledFeatures is not None:
            preferences_to_update['enabledFeatures'] = request.enabledFeatures

        # Update the user's preferences
        updated_prefs = personalization_engine.update_user_personalization_preferences(
            user_id=user["id"],
            preferences=preferences_to_update
        )

        # Return the updated preferences
        return PersonalizationPreferencesResponse(
            success=True,
            message="Personalization preferences updated successfully",
            preferences=updated_prefs,
            updatedAt=updated_prefs.get('updatedAt')
        )
    except Exception as e:
        logger.error(f"Error updating user personalization preferences: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update personalization preferences")


@app.get("/api/user/personalization/preferences", response_model=PersonalizationPreferencesGetResponse)
async def get_user_personalization_preferences(
    user: Dict[str, Any] = Depends(authenticate_user)
):
    """
    Get user's global personalization preferences.

    Args:
        user: Authenticated user information

    Returns:
        User's personalization preferences
    """
    global personalization_engine

    if not personalization_engine:
        raise HTTPException(status_code=500, detail="Personalization engine not initialized")

    try:
        # Get the user's preferences
        prefs = personalization_engine.get_user_personalization_preferences(
            user_id=user["id"]
        )

        return PersonalizationPreferencesGetResponse(
            complexityLevel=prefs.get('complexityLevel'),
            preferredExamples=prefs.get('preferredExamples'),
            focusAreas=prefs.get('focusAreas'),
            enabledFeatures=prefs.get('enabledFeatures'),
            createdAt=prefs.get('createdAt'),
            updatedAt=prefs.get('updatedAt')
        )
    except Exception as e:
        logger.error(f"Error getting user personalization preferences: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve personalization preferences")


# --- Content Adaptation Endpoints ---
class PersonalizedChapterContentResponse(BaseModel):
    chapterId: str
    title: str
    content: str
    adaptationsApplied: List[Dict[str, Any]]
    relevanceScore: float
    metadata: Dict[str, Any]


@app.get("/api/chapters/{chapter_id}/content/personalized", response_model=PersonalizedChapterContentResponse)
async def get_personalized_chapter_content(
    chapter_id: str,
    complexityOverride: Optional[str] = None,
    focusAreaOverride: Optional[str] = None,
    user: Dict[str, Any] = Depends(authenticate_user)
):
    """
    Get personalized chapter content based on user's preferences and profile.

    Args:
        chapter_id: The ID of the chapter
        complexityOverride: Optional override for complexity level
        focusAreaOverride: Optional override for focus area
        user: Authenticated user information

    Returns:
        Personalized chapter content with adaptation information
    """
    global personalization_engine

    if not personalization_engine:
        raise HTTPException(status_code=500, detail="Personalization engine not initialized")

    try:
        # Get user's preferences
        user_prefs = personalization_engine.get_user_personalization_preferences(
            user_id=user["id"]
        )

        # Apply overrides if provided
        if complexityOverride:
            user_prefs['complexityLevel'] = complexityOverride
        if focusAreaOverride:
            user_prefs['focusAreas'] = [focusAreaOverride]  # Override focus areas with single value

        # For now, we'll return placeholder content
        # In a real implementation, this would fetch the actual chapter content and adapt it
        placeholder_content = f"Personalized content for chapter {chapter_id} based on user preferences."

        # Adapt the content based on user profile and preferences
        adapted_result = personalization_engine.adapt_content_for_chapter(
            content=placeholder_content,
            user_profile=user_prefs,
            chapter_id=chapter_id,
            override_settings={}
        )

        return PersonalizedChapterContentResponse(
            chapterId=chapter_id,
            title=f"Chapter {chapter_id} - Personalized Content",
            content=adapted_result['adaptedContent'],
            adaptationsApplied=[
                {
                    "type": adaptation,
                    "appliedRule": adaptation,
                    "originalText": placeholder_content,
                    "adaptedText": adapted_result['adaptedContent']
                }
                for adaptation in adapted_result['adaptationsApplied']
            ],
            relevanceScore=adapted_result['relevanceScore'],
            metadata=adapted_result['metadata']
        )
    except Exception as e:
        logger.error(f"Error getting personalized chapter content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve personalized content")


# --- Personalization History Endpoints ---
class PersonalizationHistoryItem(BaseModel):
    id: str
    chapterId: str
    chapterTitle: str
    personalizationActive: bool
    engagementMetrics: Dict[str, Any]
    adaptationsCount: int
    relevanceScore: float
    personalizedAt: str
    viewedAt: str


class PersonalizationHistoryResponse(BaseModel):
    history: List[PersonalizationHistoryItem]
    total: int
    page: int
    limit: int


@app.get("/api/user/personalization/history", response_model=PersonalizationHistoryResponse)
async def get_personalization_history(
    request: Request,
    limit: int = 10,
    page: int = 1,
    chapterId: Optional[str] = None,
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    user: Dict[str, Any] = Depends(authenticate_user)
):
    """
    Get user's personalization history and engagement metrics.

    Args:
        request: The HTTP request object
        limit: Number of records to return (default: 10, max: 50)
        page: Page number for pagination (default: 1)
        chapterId: Optional filter for specific chapter
        startDate: Optional filter for start date (ISO 8601 format)
        endDate: Optional filter for end date (ISO 8601 format)
        user: Authenticated user information

    Returns:
        Personalization history with pagination information
    """
    global personalization_engine

    if not personalization_engine:
        raise HTTPException(status_code=500, detail="Personalization engine not initialized")

    # Validate parameters
    if limit > 50:
        limit = 50
    if limit < 1:
        limit = 10
    if page < 1:
        page = 1

    try:
        # Get the user's personalization history
        # In a real implementation, this would fetch from a database
        # For now, we'll simulate with some sample data

        # Extract query parameters from the request
        query_params = dict(request.query_params)

        # In a real implementation, we would filter based on the parameters
        # For now, we'll return sample data
        sample_history = []
        for i in range((page - 1) * limit, min(page * limit, 25)):  # Generate up to 25 sample items
            sample_history.append({
                "id": f"hist-{i+1}",
                "chapterId": f"chapter-{i+1}",
                "chapterTitle": f"Chapter {i+1}: Introduction to AI",
                "personalizationActive": i % 3 != 0,  # Every third chapter is inactive
                "engagementMetrics": {
                    "timeSpent": (i + 1) * 120,  # Time in seconds
                    "scrollDepth": round(0.3 + (i % 7) * 0.1, 2),  # Scroll depth between 0.3 and 1.0
                    "completions": i % 4,
                    "helpRequests": i % 5
                },
                "adaptationsCount": 3 + (i % 5),  # Between 3-7 adaptations
                "relevanceScore": round(0.6 + (i % 4) * 0.1, 2),  # Between 0.6 and 0.9
                "personalizedAt": f"2025-12-{str(10 + (i % 10)).zfill(2)}T09:30:00Z",
                "viewedAt": f"2025-12-{str(10 + (i % 10)).zfill(2)}T10:00:00Z"
            })

        # In a real implementation, we would apply filters here
        # For now, we'll just return the sample data
        total = 25  # Total number of items in the system

        history_items = [
            PersonalizationHistoryItem(
                id=item["id"],
                chapterId=item["chapterId"],
                chapterTitle=item["chapterTitle"],
                personalizationActive=item["personalizationActive"],
                engagementMetrics=item["engagementMetrics"],
                adaptationsCount=item["adaptationsCount"],
                relevanceScore=item["relevanceScore"],
                personalizedAt=item["personalizedAt"],
                viewedAt=item["viewedAt"]
            )
            for item in sample_history
        ]

        return PersonalizationHistoryResponse(
            history=history_items,
            total=total,
            page=page,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Error getting personalization history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve personalization history")


# --- GDPR Compliance Endpoints ---
class UserPersonalizationDataExport(BaseModel):
    userId: str
    timestamp: str
    preferences: Dict[str, Any]
    chapterPersonalizationStates: Dict[str, Any]
    preferenceHistory: List[Dict[str, Any]]
    personalizationSettings: Dict[str, Any]


@app.get("/api/user/personalization/data/export", response_model=UserPersonalizationDataExport)
async def export_user_personalization_data(
    user: Dict[str, Any] = Depends(authenticate_user)
):
    """
    Export all personalization data for the authenticated user (GDPR compliance).

    Args:
        user: Authenticated user information

    Returns:
        All personalization data for the user
    """
    global personalization_engine

    if not personalization_engine:
        raise HTTPException(status_code=500, detail="Personalization engine not initialized")

    try:
        # Export the user's personalization data
        export_data = personalization_engine.export_user_personalization_data(
            user_id=user["id"]
        )

        return export_data
    except Exception as e:
        logger.error(f"Error exporting user personalization data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to export personalization data")


@app.delete("/api/user/personalization/data/delete", status_code=204)
async def delete_user_personalization_data(
    user: Dict[str, Any] = Depends(authenticate_user)
):
    """
    Delete all personalization data for the authenticated user (GDPR compliance).

    Args:
        user: Authenticated user information

    Returns:
        204 No Content on successful deletion
    """
    global personalization_engine

    if not personalization_engine:
        raise HTTPException(status_code=500, detail="Personalization engine not initialized")

    try:
        # Delete the user's personalization data
        success = personalization_engine.delete_user_personalization_data(
            user_id=user["id"]
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete personalization data")

        logger.info(f"Personalization data deleted for user: {user['id']}")
        return  # 204 No Content
    except Exception as e:
        logger.error(f"Error deleting user personalization data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete personalization data")


# --- Health Check Endpoint (Optional but Recommended) ---
@app.get("/health")
async def health_check():
    """
    Basic health check to verify the API is running and can connect to its dependencies.
    """
    try:
        # Check Qdrant connection
        await qdrant_client.get_collections()

        # OpenAI client is checked implicitly when generating embeddings/chat
        return {"status": "ok", "message": "All services are operational."}
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")

if __name__ == "__main__":
    import uvicorn
    # To run: uvicorn main:app --reload
    uvicorn.run(app, host="0.0.0.0", port=8000)
