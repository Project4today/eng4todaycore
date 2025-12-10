import os
import json
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

APP_ENV = os.getenv("APP_ENV")
if APP_ENV:
    try:
        app_env_json = json.loads(APP_ENV)
        db_user = app_env_json.get("DB_USER")
        db_password = app_env_json.get("DB_PASSWORD")
        db_host = app_env_json.get("DB_HOST")
        db_port = app_env_json.get("DB_PORT")
        db_name = app_env_json.get("DB_NAME")

        if all([db_user, db_password, db_host, db_port, db_name]):
            DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            print(f"INFO: Configured DATABASE_URL from APP_ENV for host: {db_host}")
        else:
             print("WARNING: APP_ENV present but missing one or more DB fields (DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME).")
    except json.JSONDecodeError:
        print("WARNING: APP_ENV is not a valid JSON string.")
    except Exception as e:
        print(f"WARNING: Failed to parse APP_ENV: {e}")

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

