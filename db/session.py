import json
from typing import Optional
import asyncpg
from fastapi import FastAPI
from contextlib import asynccontextmanager

from core.config import DATABASE_URL

_db_pool: Optional[asyncpg.Pool] = None

async def _init_connection(connection):
    """
    A hook to set up the JSONB codec for the database connection.
    """
    await connection.set_type_codec('jsonb', encoder=json.dumps, decoder=json.loads, schema='pg_catalog')

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    The lifespan manager for the FastAPI application.
    It connects to the database on startup and closes the connection on shutdown.
    """
    global _db_pool
    print("Application startup: connecting to database...", flush=True)
    try:
        if DATABASE_URL:
            _db_pool = await asyncpg.create_pool(DATABASE_URL, init=_init_connection)
            print("Successfully connected to the database.", flush=True)
        else:
            print("WARNING: DATABASE_URL not set. Database pool will not be initialized.", flush=True)
            _db_pool = None
    except Exception as e:
        # Add flush=True to ensure this critical error is logged immediately
        print(f"FATAL: Failed to connect to the database: {e}", flush=True)
        _db_pool = None
    
    yield
    
    if _db_pool:
        print("Application shutdown: closing database connection pool...", flush=True)
        await _db_pool.close()
        print("Database connection pool closed.", flush=True)

def get_db_pool():
    """
    A dependency to get the database pool.
    This is used by the API endpoints to interact with the database.
    """
    return _db_pool
