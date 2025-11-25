from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers from the api directory
from api import personas, chat, users, voices
# Import the lifespan manager from the db directory
from db.session import lifespan
# Import the application version from the config
from core.config import APP_VERSION
# Import the logging middleware
from core.logging_middleware import RequestLoggingMiddleware

# Initialize the FastAPI app with the lifespan manager and the dynamic version
app = FastAPI(
    title="AI Chatbox API",
    description="Backend API for an AI Chatbox application with session management.",
    version=APP_VERSION,
    lifespan=lifespan
)

# --- Add Middleware ---
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include Routers ---
app.include_router(personas.router, prefix="/api/personas", tags=["Personas"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(voices.router, prefix="/api/voices", tags=["Voices"])

# A simple root endpoint to confirm the API is running
@app.get("/", tags=["Root"])
async def read_root():
    return {"message": f"Welcome to the AI Chatbox API v{APP_VERSION}"}
