"""
Eval document setup: ensure all postmortem docs are ingested for the test user.

Checks which postmortem files are already present and completed, then ingests
only the missing ones. Skips entirely if all docs are already uploaded.

Run standalone before any eval pipeline:
    cd backend && uv run python eval/eval_setup.py

Or call _full_setup() programmatically (e.g. from conftest.py).

Prerequisites:
    TEST_EMAIL / TEST_PASSWORD set in backend/.env
    Eval deps installed: uv pip install -r eval/requirements-eval.txt
"""
import asyncio
import os
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

POSTMORTEMS_DIR = os.path.join(os.path.dirname(__file__), "postmortems")


def _all_postmortem_filenames() -> list[str]:
    return sorted(f for f in os.listdir(POSTMORTEMS_DIR) if f.endswith(".md"))


def _get_missing_filenames(user_id: str, all_filenames: list[str]) -> list[str]:
    """Return filenames from all_filenames that are not yet completed in the DB."""
    from services.supabase_service import get_supabase_admin
    supabase = get_supabase_admin()

    existing = (
        supabase.table("documents")
        .select("filename, status")
        .eq("user_id", user_id)
        .in_("filename", all_filenames)
        .execute()
    )
    completed = {doc["filename"] for doc in existing.data or [] if doc["status"] == "completed"}
    return [f for f in all_filenames if f not in completed]


async def _ingest_postmortem_docs(user_id: str, filenames: list[str]) -> None:
    """Upload and ingest the specified postmortem .md files."""
    from services.supabase_service import get_supabase_admin
    from routers.ingestion import process_document

    supabase = get_supabase_admin()

    for md_file in filenames:
        file_path = os.path.join(POSTMORTEMS_DIR, md_file)
        with open(file_path, "rb") as fh:
            content = fh.read()

        storage_path = f"{user_id}/{uuid.uuid4()}.md"
        supabase.storage.from_("documents").upload(
            storage_path,
            content,
            file_options={"content-type": "text/markdown"},
        )

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

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".md")
        tmp.write(content)
        tmp.close()

        await process_document(
            document_id=document_id,
            user_id=user_id,
            file_path=tmp.name,
            extract_metadata=False,
        )

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


async def _clean_eval_docs(user_id: str) -> None:
    """Delete all eval postmortem docs (and their chunks via CASCADE) for the given user.

    Used by conftest.py for a forced clean + re-ingest before integration tests.
    Not called by _full_setup — normal runs only upload what is missing.
    """
    from services.supabase_service import get_supabase_admin
    supabase = get_supabase_admin()

    existing = (
        supabase.table("documents")
        .select("id, storage_path, filename")
        .eq("user_id", user_id)
        .in_("filename", _all_postmortem_filenames())
        .execute()
    )
    storage_paths = [doc["storage_path"] for doc in existing.data or [] if doc.get("storage_path")]
    doc_ids = [doc["id"] for doc in existing.data or []]

    if storage_paths:
        try:
            supabase.storage.from_("documents").remove(storage_paths)
        except Exception as exc:
            print(f"  [eval-setup] Storage cleanup warning (non-fatal): {exc}")

    if doc_ids:
        supabase.table("documents").delete().in_("id", doc_ids).execute()


async def _full_setup(user_id: str) -> None:
    """Ingest only the postmortem docs that are missing or not yet completed.

    Skips entirely if all docs are already present. This makes the setup
    idempotent and fast when re-running evals after a previous successful run.
    """
    all_filenames = _all_postmortem_filenames()
    assert all_filenames, f"No .md files found in {POSTMORTEMS_DIR}"

    missing = _get_missing_filenames(user_id, all_filenames)

    if not missing:
        print(f"[eval-setup] All {len(all_filenames)} postmortem docs already uploaded — skipping.\n")
        return

    print(f"[eval-setup] {len(missing)}/{len(all_filenames)} doc(s) missing, ingesting:")
    for f in missing:
        print(f"  - {f}")
    await _ingest_postmortem_docs(user_id, missing)
    print("[eval-setup] Ingestion complete.\n")


async def main() -> None:
    from eval.eval_utils import get_eval_user_id
    user_id = get_eval_user_id()
    await _full_setup(user_id)


if __name__ == "__main__":
    asyncio.run(main())
