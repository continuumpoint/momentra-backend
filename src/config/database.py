from supabase import create_client, Client
from src.config.settings import get_settings
from functools import lru_cache


@lru_cache()
def get_supabase_client() -> Client:
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
