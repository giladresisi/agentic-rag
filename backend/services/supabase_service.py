from supabase import create_client, Client
from config import settings

# Supabase client
supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_ANON_KEY
)

# Service role client (for admin operations)
supabase_admin: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY
)


def get_supabase() -> Client:
    """Get Supabase client instance."""
    return supabase


def get_supabase_admin() -> Client:
    """Get Supabase admin client instance."""
    return supabase_admin
