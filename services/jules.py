import httpx
from fastapi import HTTPException, status
from core.config import JULES_API_KEY, JULES_API_URL

async def get_jules_sources():
    """
    Fetches the list of available sources from the Jules API.
    """
    if not JULES_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Jules API Key is not configured."
        )

    # Corrected URL and headers based on your feedback
    url = f"{JULES_API_URL}/v1alpha/sources"
    headers = {
        "X-Goog-Api-Key": JULES_API_KEY,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status() # Raise exception for 4xx/5xx errors
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Jules API Error: {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Jules API Error: {e.response.text}"
            )
        except httpx.RequestError as e:
            print(f"Jules Connection Error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to connect to Jules API."
            )
