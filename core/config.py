import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Application Version ---
APP_VERSION = "0.2.0-beta" # Bump version for Polly integration

# --- Constants ---
MAX_CONVERSATION_TOKENS = 100000

# --- API Key and Model Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_VERSION = os.getenv("GEMINI_MODEL_VERSION", "gemini-1.5-pro")

# --- Database Configuration ---
DATABASE_URL = os.getenv("DATABASE_URL")

# --- AWS Configuration ---
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
DEFAULT_POLLY_VOICE_ID = os.getenv("DEFAULT_POLLY_VOICE_ID", "Joanna")


# --- Validation ---
if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
    raise ValueError("GEMINI_API_KEY environment variable not set or is still a placeholder.")
if not DATABASE_URL or "user:password" in DATABASE_URL:
     raise ValueError("DATABASE_URL environment variable not set or is still a placeholder.")
if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY or not S3_BUCKET_NAME:
    print("WARNING: AWS credentials or S3 bucket name are not fully configured. Polly integration will not work.")

