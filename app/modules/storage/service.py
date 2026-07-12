import boto3, os
R2 = boto3.client("s3", endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com", aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"), aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"))
BUCKET = os.getenv("R2_BUCKET_NAME")

async def upload_report_pdf(file_bytes, filename):
    R2.put_object(Bucket=BUCKET, Key=filename, Body=file_bytes)
    return f"https://{BUCKET}.{os.getenv('R2_ACCOUNT_ID')}.r2.dev/{filename}"
