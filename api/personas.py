from typing import List
import asyncpg
from fastapi import APIRouter, HTTPException, status, Response, Depends

from db.session import get_db_pool
from models.persona import Persona

router = APIRouter()

@router.post("/", response_model=Persona, status_code=status.HTTP_201_CREATED)
async def create_persona(persona: Persona, db_pool=Depends(get_db_pool)):
    if not db_pool:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")
    async with db_pool.acquire() as connection:
        try:
            data = persona.dict(exclude={'prompt_id', 'created_at'})
            columns = ", ".join(data.keys())
            placeholders = ", ".join([f"${i+1}" for i in range(len(data))])
            
            query = f"INSERT INTO personas ({columns}) VALUES ({placeholders}) RETURNING *"
            
            record = await connection.fetchrow(query, *data.values())
            return dict(record)
        except asyncpg.exceptions.UniqueViolationError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Persona with role_name '{persona.role_name}' already exists.")
        except Exception as e:
            print(f"Error creating persona: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.get("/", response_model=List[Persona])
async def get_all_personas(db_pool=Depends(get_db_pool)):
    if not db_pool:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")
    async with db_pool.acquire() as connection:
        records = await connection.fetch("SELECT * FROM personas ORDER BY role_name")
        return [dict(record) for record in records]

@router.get("/{prompt_id}", response_model=Persona)
async def get_persona(prompt_id: int, db_pool=Depends(get_db_pool)):
    if not db_pool:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")
    async with db_pool.acquire() as connection:
        record = await connection.fetchrow("SELECT * FROM personas WHERE prompt_id = $1", prompt_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Persona with prompt_id {prompt_id} not found.")
        return dict(record)

@router.put("/{prompt_id}", response_model=Persona)
async def update_persona(prompt_id: int, persona: Persona, db_pool=Depends(get_db_pool)):
    if not db_pool:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")
    async with db_pool.acquire() as connection:
        data = persona.dict(exclude={'prompt_id', 'created_at'}, exclude_unset=True)
        set_clauses = ", ".join([f"{key} = ${i+2}" for i, key in enumerate(data.keys())])
        
        query = f"UPDATE personas SET {set_clauses} WHERE prompt_id = $1 RETURNING *"
        
        record = await connection.fetchrow(query, prompt_id, *data.values())
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Persona with prompt_id {prompt_id} not found.")
        return dict(record)

@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_persona(prompt_id: int, db_pool=Depends(get_db_pool)):
    if not db_pool:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")
    async with db_pool.acquire() as connection:
        result = await connection.execute("DELETE FROM personas WHERE prompt_id = $1", prompt_id)
        if result == "DELETE 0":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Persona with prompt_id {prompt_id} not found.")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
