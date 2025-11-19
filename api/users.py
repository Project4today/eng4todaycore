from typing import List
import uuid
from fastapi import APIRouter, HTTPException, status, Depends

from db.session import get_db_pool
from models.chat import UserSessionInfo

router = APIRouter()

@router.get("/{user_id}/sessions", response_model=List[UserSessionInfo], status_code=status.HTTP_200_OK)
async def get_user_sessions(user_id: int, db_pool=Depends(get_db_pool)):
    """
    Fetches a list of all non-empty chat sessions for a specific user.
    """
    if not db_pool:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")

    async with db_pool.acquire() as connection:
        try:
            query = """
            SELECT session_id, updated_at, session_name AS title
            FROM chat_sessions
            WHERE user_id = $1 AND session_name IS NOT NULL
            ORDER BY updated_at DESC;
            """
            records = await connection.fetch(query, user_id)
            return [UserSessionInfo(session_id=r['session_id'], updated_at=r['updated_at'], title=r['title']) for r in records]
        except Exception as e:
            print(f"Error retrieving user sessions: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")
