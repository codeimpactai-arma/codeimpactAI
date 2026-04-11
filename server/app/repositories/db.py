from datetime import datetime

from supabase import create_client, Client

# SUPABASE_URL = "https://hmouoztlgrsotauzohgm.supabase.co"
# SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imhtb3VvenRsZ3Jzb3RhdXpvaGdtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQzMjgwNjUsImV4cCI6MjA3OTkwNDA2NX0.7lICVEIkYaG_629xN_nVPUJspUgkhRswkKJKTF2TNBg"

SUPABASE_URL = "https://fctvakaarrquaegxlnxa.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZjdHZha2FhcnJxdWFlZ3hsbnhhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU4MjI1NTcsImV4cCI6MjA5MTM5ODU1N30.X3qLPaX0hzqi5rU8NBvsNOnAzhhdUVjdvQxCWRSmypw"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def now_str():
    return datetime.now().isoformat()
