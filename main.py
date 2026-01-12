from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers from the api directory
from api import personas, chat, users, voices, report
# Import the lifespan manager from the db directory
from db.session import lifespan
# Import the application version from the config
from core.config import APP_VERSION

# Initialize the FastAPI app with the lifespan manager and the dynamic version
app = FastAPI(
    title="AI Chatbox API",
    description="Backend API for an AI Chatbox application with session management.",
    version=APP_VERSION,
    lifespan=lifespan
)

# --- CORS Middleware ---
# Allows the frontend to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

# --- Include Routers ---
# Mount the persona, chat, and user endpoints with logical prefixes
app.include_router(personas.router, prefix="/api/personas", tags=["Personas"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(voices.router, prefix="/api/voices", tags=["Voices"])
app.include_router(report.router, prefix="/api/report", tags=["Report"])

# A simple root endpoint to confirm the API is running
@app.get("/", tags=["Root"])
async def read_root():
    return {"message": f"Welcome to the AI Chatbox API v{APP_VERSION}"}
