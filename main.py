from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers from the api directory
from api import personas, chat, users
# Import the lifespan manager from the db directory
from db.session import lifespan

# Initialize the FastAPI app with the lifespan manager
app = FastAPI(
    title="AI Chatbox API",
    description="Backend API for an AI Chatbox application with session management.",
    version="1.2.0", # Bump version for new structure
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

# A simple root endpoint to confirm the API is running
@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the AI Chatbox API"}
