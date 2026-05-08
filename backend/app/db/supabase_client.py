"""
Bower Ag CowCare Tool — Supabase Client
Singleton connection to Supabase for database operations.
Uses service_role key for backend (bypasses RLS for admin operations).
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


def get_supabase_client() -> Client:
    """
    Returns a Supabase client using the service role key.
    Used for backend operations that need full DB access.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env. "
            "See .env.example for required variables."
        )

    return create_client(url, key)


def get_supabase_anon_client() -> Client:
    """
    Returns a Supabase client using the anon key.
    Used for operations that should respect RLS (Row Level Security).
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env. "
            "See .env.example for required variables."
        )

    return create_client(url, key)
