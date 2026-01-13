import os
import sys
from urllib.parse import quote_plus
from dotenv import load_dotenv

# --- Application Version ---
APP_VERSION = "0.3.3-beta"

# Load .env cho môi trường local (nếu có)
load_dotenv()

# --- 1. SAFE DEBUGGING: CHECK VARIABLES ---
# In log để verify trên CloudWatch xem ECS đã inject secret thành công chưa
print("\n--- [START] CHECKING ENVIRONMENT VARIABLES ---", flush=True)

required_vars = ["DB_HOST", "DB_USER", "DB_PASSWORD", "DB_PORT", "DB_NAME", "JULES_API_KEY"]
missing_vars = []

for var_name in required_vars:
    value = os.getenv(var_name)
    if value:
        # Chỉ in độ dài để debug, KHÔNG in giá trị thật
        print(f"✅ {var_name:<15}: FOUND | Length: {len(str(value))} chars", flush=True)
    else:
        print(f"❌ {var_name:<15}: MISSING", flush=True)
        missing_vars.append(var_name)

print("--- [END] CHECKING ENVIRONMENT VARIABLES ---\n", flush=True)

# --- 2. DATABASE CONFIGURATION ---
DATABASE_URL = f"postgresql://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}/{os.getenv("DB_NAME")}"
safe_url = f"postgresql://*******:******@{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}/{os.getenv("DB_NAME")}"
print(f"INFO: Constructed DATABASE_URL: {safe_url}")

# Nếu chưa có DATABASE_URL nhưng đủ các biến thành phần thì tự construct
if not DATABASE_URL and not missing_vars:
    try:
        db_host = os.getenv("DB_HOST")
        db_user = os.getenv("DB_USER")
        db_pass = os.getenv("DB_PASSWORD")
        db_port = os.getenv("DB_PORT")
        db_name = os.getenv("DB_NAME")
        jules_key = os.getenv("JULES_API_KEY")

        # Encode user/pass để xử lý ký tự đặc biệt (quan trọng)
        encoded_user = quote_plus(db_user)
        encoded_pass = quote_plus(db_pass)

        # FIX: Sử dụng 'postgresql://' thay vì 'postgresql+asyncpg://'
        # asyncpg trực tiếp không hỗ trợ scheme '+asyncpg'
        DATABASE_URL = f"postgresql://{encoded_user}:{encoded_pass}@{db_host}:{db_port}/{db_name}"
        
        # Log URL an toàn (che password)
        safe_url = f"postgresql://{encoded_user}:******@{db_host}:{db_port}/{db_name}"
        print(f"INFO: Constructed DATABASE_URL: {safe_url}", flush=True)
        
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to construct DATABASE_URL. Error: {str(e)}", flush=True)

# --- 3. VALIDATION ---
if not DATABASE_URL:
    print("CRITICAL ERROR: DATABASE_URL could not be set. Exiting...", flush=True)
    raise ValueError("DATABASE_URL could not be constructed. Check environment variables.")

# --- 4. OTHER CONFIGURATIONS ---
MAX_CONVERSATION_TOKENS = 20000

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_VERSION = os.getenv("GEMINI_MODEL_VERSION", "gemini-1.5-pro")

if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
    print("WARNING: GEMINI_API_KEY is missing or invalid.", flush=True)

# AWS Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
DEFAULT_POLLY_VOICE_ID = os.getenv("DEFAULT_POLLY_VOICE_ID", "Joanna")

# Jules API Configuration
JULES_API_KEY = os.getenv("JULES_API_KEY")
# Updated default URL based on your feedback
JULES_API_URL = os.getenv("JULES_API_URL", "https://jules.googleapis.com") 

print(f"Successfully loaded configuration for version {APP_VERSION}.", flush=True)
