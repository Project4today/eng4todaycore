import os
from dotenv import load_dotenv
from .secrets_manager import get_secret

# --- Application Version ---
APP_VERSION = "0.3.0-beta" # Bump version for new config system

# --- Load Base Environment ---
# This loads the .env file for local development and gets OS environment variables for cloud.
load_dotenv()

# --- Hybrid Configuration Loading ---
# This is the core of the new system.

# Check if we are in a cloud environment by looking for the secret ARN.
APP_ENV_SECRET_ARN = os.getenv("arn:aws:secretsmanager:us-east-1:155290703087:secret:eng4today/dev/app-env-68508fbb-8upc9h")

if APP_ENV_SECRET_ARN:
    print("Cloud environment detected. Fetching secrets from AWS Secrets Manager...")
    # We are in the cloud, fetch the JSON secret from AWS.
    secrets = get_secret(APP_ENV_SECRET_ARN)
    
    # --- Database Configuration (from AWS Secrets) ---
    DB_HOST = secrets.get("DB_HOST")
    DB_PORT = secrets.get("DB_PORT")
    DB_USER = secrets.get("DB_USER")
    DB_PASSWORD = secrets.get("DB_PASSWORD")
    DB_NAME = secrets.get("DB_NAME")
    
    # --- AWS Service Configuration (from AWS Secrets) ---
    S3_BUCKET_NAME = secrets.get("S3_BUCKET_NAME")
    DEFAULT_POLLY_VOICE_ID = secrets.get("DEFAULT_POLLY_VOICE_ID", "Joanna")
    # In a cloud environment (like ECS), boto3 can get credentials from the task role automatically.
    # So, we don't need to set them explicitly here.
    AWS_ACCESS_KEY_ID = None
    AWS_SECRET_ACCESS_KEY = None
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

else:
    print("Local development environment detected. Loading from .env file...")
    # We are running locally, load all variables from the .env file.

    # --- Database Configuration (from .env) ---
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_NAME = os.getenv("DB_NAME")

    # --- AWS Service Configuration (from .env) ---
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
    DEFAULT_POLLY_VOICE_ID = os.getenv("DEFAULT_POLLY_VOICE_ID", "Joanna")

# --- Construct Database URL ---
# This is now built dynamically from the loaded components.
if all([DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME]):
    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    DATABASE_URL = None
    print("WARNING: Database connection details are not fully configured.")

# --- Other Configurations ---
MAX_CONVERSATION_TOKENS = 20000
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_VERSION = os.getenv("GEMINI_MODEL_VERSION", "gemini-1.5-pro")

# --- Validation ---
if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
    raise ValueError("GEMINI_API_KEY environment variable not set or is still a placeholder.")
if not DATABASE_URL:
     raise ValueError("DATABASE_URL could not be constructed. Please check your environment variables or secrets.")

print(f"Successfully loaded configuration for version {APP_VERSION}.")
