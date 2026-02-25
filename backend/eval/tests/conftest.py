"""Session fixture: clean + ingest postmortem docs for eval integration tests.

Run integration tests:
  EVAL_DOCS_INGESTED=true uv run python -m pytest eval/tests/ -v

Skip integration tests by setting EVAL_DOCS_INGESTED=false in backend/.env (the default).
"""
import asyncio
import os
import sys
import tempfile
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from dotenv import load_dotenv
load_dotenv()

POSTMORTEMS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "postmortems")
TEST_EMAIL = os.getenv("TEST_EMAIL")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")


def _get_test_user_id() -> str:
    """Sign in with TEST_EMAIL/TEST_PASSWORD and return the user's UUID.

    Uses Supabase admin client to sign in so we get the real user_id that
    satisfies the documents.user_id FK constraint.
    """
    from services.supabase_service import get_supabase_admin
    assert TEST_EMAIL and TEST_PASSWORD, (
        "TEST_EMAIL and TEST_PASSWORD must be set in backend/.env"
    )
    supabase = get_supabase_admin()
    auth_response = supabase.auth.sign_in_with_password({
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
    })
    return auth_response.user.id


async def _clean_eval_docs(user_id: str) -> None:
    """Delete all eval postmortem docs (and their chunks via CASCADE) for the given user."""
    from services.supabase_service import get_supabase_admin
    supabase = get_supabase_admin()

    existing = (
        supabase.table("documents")
        .select("id, storage_path, filename")
        .eq("user_id", user_id)
        .in_("filename", [f for f in os.listdir(POSTMORTEMS_DIR) if f.endswith(".md")])
        .execute()
    )
    storage_paths = [doc["storage_path"] for doc in existing.data or [] if doc.get("storage_path")]
    doc_ids = [doc["id"] for doc in existing.data or []]

    if storage_paths:
        try:
            supabase.storage.from_("documents").remove(storage_paths)
        except Exception as exc:
            # Non-fatal: storage file may already be gone. DB delete below is authoritative.
            print(f"  [eval-setup] Storage cleanup warning (non-fatal): {exc}")

    if doc_ids:
        supabase.table("documents").delete().in_("id", doc_ids).execute()


async def _ingest_postmortem_docs(user_id: str) -> None:
    """Upload each postmortem .md file to Storage and run the full ingestion pipeline.

    Calls process_document() directly (same code path as the HTTP upload endpoint
    but without auth middleware) so chunks are stored with the real test user_id,
    matching the eval pipeline's retrieval filter.

    extract_metadata=False skips LLM metadata extraction for speed.
    """
    from services.supabase_service import get_supabase_admin
    from routers.ingestion import process_document

    supabase = get_supabase_admin()

    md_files = sorted(f for f in os.listdir(POSTMORTEMS_DIR) if f.endswith(".md"))
    assert md_files, f"No .md files found in {POSTMORTEMS_DIR}"

    for md_file in md_files:
        file_path = os.path.join(POSTMORTEMS_DIR, md_file)
        with open(file_path, "rb") as fh:
            content = fh.read()

        # Upload raw bytes to Supabase Storage under the user's prefix
        storage_path = f"{user_id}/{uuid.uuid4()}.md"
        supabase.storage.from_("documents").upload(
            storage_path,
            content,
            file_options={"content-type": "text/markdown"},
        )

        # Create document record (status=processing)
        resp = supabase.table("documents").insert({
            "user_id": user_id,
            "filename": md_file,
            "content_type": "text/markdown",
            "file_size_bytes": len(content),
            "storage_path": storage_path,
            "status": "processing",
            "chunk_count": 0,
        }).execute()
        document_id = resp.data[0]["id"]

        # Write to temp file — process_document reads from disk
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".md")
        tmp.write(content)
        tmp.close()

        # Run parse → chunk → embed → save (awaited directly, no background task)
        await process_document(
            document_id=document_id,
            user_id=user_id,
            file_path=tmp.name,
            extract_metadata=False,
        )

        # Verify ingestion succeeded
        try:
            check = (
                supabase.table("documents")
                .select("status, error_message, chunk_count")
                .eq("id", document_id)
                .single()
                .execute()
            )
            status_row = check.data
        except Exception as e:
            raise AssertionError(f"Could not fetch document status for {md_file}: {e}")
        assert status_row["status"] == "completed", (
            f"Ingestion failed for {md_file}: {status_row.get('error_message')}"
        )
        print(f"  [eval-setup] {md_file} -> {status_row['chunk_count']} chunks")


async def _full_setup(user_id: str) -> None:
    print(f"\n[eval-setup] Cleaning eval postmortem docs for user {user_id[:8]}...")
    await _clean_eval_docs(user_id)
    print("[eval-setup] Ingesting postmortem documents...")
    await _ingest_postmortem_docs(user_id)
    print("[eval-setup] Ingestion complete.\n")


@pytest.fixture(scope="session")
def eval_ingestion_setup():
    """Clean + ingest postmortem docs; yield the test user_id for retrieval.

    Skipped when EVAL_DOCS_INGESTED=false (the .env.example default).
    Set EVAL_DOCS_INGESTED=true in backend/.env to enable integration tests.

    Yields:
        str: The real test user UUID used for ingestion (pass to run_rag_pipeline).

    Docs are left in place after tests so developers can run evaluate.py immediately.
    """
    if os.getenv("EVAL_DOCS_INGESTED", "false").lower() in ("0", "false", "no", ""):
        pytest.skip("Set EVAL_DOCS_INGESTED=true in backend/.env to run integration tests")

    user_id = _get_test_user_id()
    asyncio.run(_full_setup(user_id))
    os.environ["EVAL_DOCS_INGESTED"] = "true"
    yield user_id
    # Docs intentionally left in place for manual evaluate.py run.
