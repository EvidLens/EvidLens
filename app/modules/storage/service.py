import os
from supabase import create_client, Client

def get_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("APP_SUPABASE_KEY")
    print("DEBUG URL:", url)
    print("DEBUG KEY:", key[:10] if key else "NONE")
    return create_client(url, key)

BUCKET = "evidlens-files"
supabase: Client = get_supabase_client()  # <-- this line calls the function above

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
