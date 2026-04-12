from datetime import datetime

from supabase import create_client, Client

SUPABASE_URL = "https://fctvakaarrquaegxlnxa.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZjdHZha2FhcnJxdWFlZ3hsbnhhIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTgyMjU1NywiZXhwIjoyMDkxMzk4NTU3fQ.QH2KzaNibRMwymHVO3qH0jQ2WYOahJyWazEf_kcy5Ng"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def now_str():
    return datetime.now().isoformat()
