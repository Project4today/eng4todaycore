import boto3
import json
from botocore.exceptions import ClientError

def get_secret(secret_arn: str) -> dict:
    """
    Fetches a secret from AWS Secrets Manager and parses the JSON string.
    """
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager')

    try:
        print(f"Attempting to fetch secret from AWS Secrets Manager: {secret_arn}")
        get_secret_value_response = client.get_secret_value(SecretId=secret_arn)
        print("Successfully fetched secret.")
    except ClientError as e:
        print(f"ERROR: Could not fetch secret from AWS Secrets Manager: {e}")
        raise e

    # The secret is returned as a JSON string, so we need to parse it.
    secret = get_secret_value_response['SecretString']
    return json.loads(secret)
