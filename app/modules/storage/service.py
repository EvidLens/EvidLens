import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
BUCKET = "evidlens-files"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def upload_report_pdf(file_bytes, filename):
    # Upload to Supabase Storage
    res = supabase.storage.from_(BUCKET).upload(
        path=filename,
        file=file_bytes,
        file_options={"content-type": "application/pdf", "upsert": "true"}
    )
    
    # Get public URL
    url_data = supabase.storage.from_(BUCKET).get_public_url(filename)
    return url_data
