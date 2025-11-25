from typing import List
from fastapi import APIRouter, HTTPException, status, Depends

from services.aws import polly_client
from models.voice import VoiceResponse

router = APIRouter()

@router.get("/", response_model=List[VoiceResponse])
async def get_available_voices():
    """
    Fetches a list of available English neural voices from Amazon Polly.
    """
    if not polly_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AWS Polly client is not configured. Cannot fetch voices."
        )

    try:
        # Call Polly to get all neural voices
        response = polly_client.describe_voices(Engine='neural')
        
        voices = response.get('Voices', [])
        
        # Filter for English voices and format the response
        english_voices = []
        for voice in voices:
            lang_code = voice.get('LanguageCode')
            if lang_code and lang_code.startswith('en-'):
                english_voices.append(
                    VoiceResponse(
                        id=voice.get('Id'),
                        name=voice.get('Name'),
                        gender=voice.get('Gender'),
                        language_code=lang_code,
                        language_name=voice.get('LanguageName')
                    )
                )
        
        # Sort by language name and then by voice name for a clean list
        english_voices.sort(key=lambda v: (v.language_name, v.name))
        
        return english_voices

    except Exception as e:
        print(f"ERROR: Failed to fetch voices from Polly: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve voice list from the provider."
        )
