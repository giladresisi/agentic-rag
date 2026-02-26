# backend/eval/eval_utils.py
# Shared utilities for eval entry points (evaluate.py, evaluate_tool_selection.py).
import os


def get_eval_user_id() -> str:
    """Resolve the user UUID for eval retrieval.

    Signs in with TEST_EMAIL/TEST_PASSWORD (from backend/.env) to get the real
    Supabase user UUID — the same user whose postmortem docs were ingested.
    Falls back to the placeholder UUID if credentials are not configured (retrieval
    will return no chunks and scores will be meaningless).
    """
    test_email = os.getenv("TEST_EMAIL")
    test_password = os.getenv("TEST_PASSWORD")
    if not test_email or not test_password:
        print("  [warn] TEST_EMAIL/TEST_PASSWORD not set — using placeholder UUID (no docs retrieved)")
        return "00000000-0000-0000-0000-000000000000"
    from services.supabase_service import get_supabase_admin
    supabase = get_supabase_admin()
    auth = supabase.auth.sign_in_with_password({"email": test_email, "password": test_password})
    user_id = auth.user.id
    print(f"  Signed in as {test_email} (user_id: {user_id[:8]}...)")
    return user_id
