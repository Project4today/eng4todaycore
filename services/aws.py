import hashlib
import boto3
from botocore.exceptions import ClientError

from core.config import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_REGION,
    S3_BUCKET_NAME,
)

# Initialize boto3 clients if credentials are provided
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )
    polly_client = session.client("polly")
    s3_client = session.client("s3")
else:
    polly_client = None
    s3_client = None

def generate_audio_filename(text: str, voice_id: str) -> str:
    """Creates a unique, deterministic filename based on text and voice."""
    clean_text = text.strip()
    sha256 = hashlib.sha256((clean_text + voice_id).encode("utf-8")).hexdigest()
    return f"{sha256}.mp3"

def get_presigned_url(file_name: str) -> str:
    """Generates a pre-signed URL to access a private S3 object."""
    if not s3_client:
        return None
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET_NAME, 'Key': file_name},
            ExpiresIn=3600  # URL expires in 1 hour
        )
        return url
    except ClientError as e:
        print(f"Error generating pre-signed URL: {e}")
        return None

async def get_or_create_audio_url(text: str, voice_id: str, text_type: str = 'text') -> str:
    """
    Handles the "write-through" cache.
    Checks S3 for an existing file; if not found, generates it with Polly and uploads.
    Returns a fresh pre-signed URL only if the object exists or was successfully created.
    """
    if not all([polly_client, s3_client, S3_BUCKET_NAME]):
        print("AWS service is not configured. Skipping audio generation.")
        return None

    clean_text = text.strip()
    if not clean_text:
        return None

    filename = generate_audio_filename(clean_text, voice_id)

    try:
        # Check if the file already exists in S3
        s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=filename)
        print(f"Cache HIT: Found audio file {filename} in S3.")
        # If it exists, we can proceed to generate the URL at the end.
    
    except ClientError as e:
        # If the error is 404, the file doesn't exist, so we create it.
        if e.response['Error']['Code'] == '404':
            print(f"Cache MISS: File {filename} not in S3. Generating with Polly...")
            try:
                # Synthesize speech with Polly
                response = polly_client.synthesize_speech(
                    Text=clean_text,
                    TextType=text_type,
                    OutputFormat="mp3",
                    VoiceId=voice_id,
                    Engine="neural"
                )
                
                # Upload the audio stream to S3
                s3_client.put_object(
                    Bucket=S3_BUCKET_NAME,
                    Key=filename,
                    Body=response["AudioStream"].read(),
                    ContentType="audio/mpeg"
                )
                print(f"SUCCESS: Uploaded {filename} to S3.")
                # Since creation was successful, we can now generate the URL.
            except Exception as polly_error:
                print(f"ERROR: Failed to generate or upload audio: {polly_error}")
                # CRITICAL: If creation fails, return None immediately.
                return None
        else:
            # Handle other S3 errors (like 403 Forbidden)
            print(f"ERROR: An S3 error occurred on head_object: {e}")
            # CRITICAL: If we can't check S3, we can't proceed.
            return None
            
    # This line is now only reached if the object is confirmed to exist on S3
    # (either because it was already there or because we just uploaded it).
    return get_presigned_url(filename)
