import hashlib
import boto3
from botocore.exceptions import ClientError

from core.config import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_REGION,
    S3_BUCKET_NAME,
)

# Initialize boto3 clients
session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

polly_client = session.client("polly")
s3_client = session.client("s3")

def get_s3_url(file_name: str) -> str:
    """Constructs the public URL for a file in the S3 bucket."""
    return f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{file_name}"

def generate_audio_filename(text: str, voice_id: str) -> str:
    """Creates a unique, deterministic filename based on text and voice."""
    sha256 = hashlib.sha256((text + voice_id).encode("utf-8")).hexdigest()
    return f"{sha256}.mp3"

async def get_or_create_audio_url(text: str, voice_id: str) -> str:
    """
    Main function to get an audio URL.
    Checks S3 for an existing file; if not found, generates it with Polly and uploads.
    """
    if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME]):
        print("AWS service is not configured. Skipping audio generation.")
        return None

    filename = generate_audio_filename(text, voice_id)
    s3_url = get_s3_url(filename)

    try:
        # Check if the file already exists in S3
        s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=filename)
        print(f"Cache HIT: Found audio file {filename} in S3.")
        return s3_url
    except ClientError as e:
        # If the error is 404, the file doesn't exist, so we create it.
        if e.response['Error']['Code'] == '404':
            print(f"Cache MISS: File {filename} not in S3. Generating with Polly...")
            try:
                # Synthesize speech with Polly
                response = polly_client.synthesize_speech(
                    Text=text,
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
                return s3_url
            except Exception as polly_error:
                print(f"ERROR: Failed to generate or upload audio: {polly_error}")
                return None
        else:
            # Handle other S3 errors
            print(f"ERROR: An S3 error occurred: {e}")
            return None
