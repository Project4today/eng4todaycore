import json
from typing import Optional
import asyncpg
from contextlib import asynccontextmanager
from fastapi import FastAPI

from core.config import DATABASE_URL, GEMINI_MODEL_VERSION

db_pool: Optional[asyncpg.Pool] = None

async def _init_connection(connection):
    """Initialize each new database connection by setting the JSONB codec."""
    await connection.set_type_codec(
        'jsonb',
        encoder=lambda v: json.dumps(v, ensure_ascii=False),
        decoder=json.loads,
        schema='pg_catalog'
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the application.
    Connects to the database on startup and closes the connection on shutdown.
    """
    global db_pool
    print("Application startup: connecting to database...")
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, init=_init_connection)
        print(f"Successfully connected to the database and configured to use '{GEMINI_MODEL_VERSION}'.")
    except Exception as e:
        print(f"FATAL: Failed to connect to the database: {e}")
        db_pool = None
    
    yield
    
    if db_pool:
        print("Application shutdown: closing database connection pool...")
        await db_pool.close()
        print("Database connection pool closed.")

def get_db_pool():
    """Dependency to get the database pool."""
    return db_pool
