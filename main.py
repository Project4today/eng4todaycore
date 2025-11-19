from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers and lifespan manager
from api import personas, chat, users
from db.session import lifespan
# Import the new logging middleware
from core.logging_middleware import RequestLoggingMiddleware

# Initialize the FastAPI app with the lifespan manager
app = FastAPI(
    title="AI Chatbox API",
    description="Backend API for an AI Chatbox application with session management.",
    version="1.3.0", # Bump version for new logging feature
    lifespan=lifespan
)

# --- Add Middleware ---

# IMPORTANT: Add the logging middleware first to ensure it logs all requests.
app.add_middleware(RequestLoggingMiddleware)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include Routers ---
# Mount the persona, chat, and user endpoints with logical prefixes
app.include_router(personas.router, prefix="/api/personas", tags=["Personas"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])

# A simple root endpoint to confirm the API is running
@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the AI Chatbox API"}
