from typing import Any
from fastapi import APIRouter, Depends
from services.jules import get_jules_sources

router = APIRouter()

@router.get("/sources", response_model=Any)
async def get_sources():
    """
    Retrieves a list of available sources from the Jules API.
    """
    # The `get_jules_sources` function handles all logic and error handling.
    # We use `response_model=Any` because we don't have a Pydantic model for the Jules response yet.
    # This can be refined later if the response structure is known.
    sources = await get_jules_sources()
    return sources
