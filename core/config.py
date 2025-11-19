import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Application Version ---
# This is the single source of truth for the application's version.
APP_VERSION = "0.1.0-beta"

# --- Constants ---
MAX_CONVERSATION_TOKENS = 20000

# --- API Key and Model Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_VERSION = os.getenv("GEMINI_MODEL_VERSION", "gemini-1.5-pro")

# --- Database Configuration ---
DATABASE_URL = os.getenv("DATABASE_URL")

# --- Validation ---
if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
    raise ValueError("GEMINI_API_KEY environment variable not set or is still a placeholder. Please update your .env file.")

if not DATABASE_URL or "user:password" in DATABASE_URL:
     raise ValueError("DATABASE_URL environment variable not set or is still a placeholder. Please update your .env file.")
