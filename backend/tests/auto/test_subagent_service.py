"""
Tests for sub-agent service: execution, recursion limit, and error handling.
"""
import asyncio
from dotenv import load_dotenv
from test_utils import TEST_EMAIL, TEST_PASSWORD
from services.supabase_service import get_supabase_admin
from services.embedding_service import embedding_service
from models.subagent import SubAgentRequest
from services.subagent_service import execute_subagent

load_dotenv()

test_user_id = None
test_document_id = None


def setup_module(module):
    """Pytest module setup: authenticate, create test document before tests."""
    import asyncio
    asyncio.run(setup())


async def setup():
    """Authenticate test user and create a test document with chunks."""
    global test_user_id, test_document_id
    supabase = get_supabase_admin()

    auth_response = supabase.auth.sign_in_with_password({
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
    })
    test_user_id = auth_response.user.id
    print(f"[PASS] Setup - authenticated user: {test_user_id}")

    # Clean up any previous test data
    supabase.table("documents").delete().eq("user_id", test_user_id).execute()

    # Create a test document with known content
    content = """Project Phoenix Status Report - Q4 2024

Executive Summary:
Project Phoenix is a cloud migration initiative targeting legacy infrastructure.
The project budget is $2.4 million with a completion target of March 2025.

Key Milestones:
- Phase 1 (Database Migration): Completed November 2024
- Phase 2 (Application Layer): In Progress, 65% complete
- Phase 3 (Load Testing): Scheduled January 2025

Risk Assessment:
Primary risk is vendor lock-in with CloudCorp services.
Mitigation strategy includes multi-cloud abstraction layer.

Team Lead: Dr. Sarah Chen
Project Code: PHX-2024-Q4
"""

    doc_response = supabase.table("documents").insert({
        "user_id": test_user_id,
        "filename": "phoenix_report.txt",
        "content_type": "text/plain",
        "file_size_bytes": len(content),
        "storage_path": f"{test_user_id}/phoenix_report_subagent_test.txt",
        "status": "completed",
        "chunk_count": 0,
    }).execute()

    test_document_id = doc_response.data[0]["id"]

    # Upload file to storage for read_full_document
    try:
        supabase.storage.from_("documents").upload(
            f"{test_user_id}/phoenix_report_subagent_test.txt",
            content.encode("utf-8"),
            {"content-type": "text/plain"},
        )
    except Exception as e:
        if "Duplicate" not in str(e):
            raise

    # Create chunks with embeddings
    chunks = embedding_service.chunk_text(content)
    embeddings = await embedding_service.generate_embeddings(chunks)

    chunk_records = []
    for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_records.append({
            "document_id": test_document_id,
            "user_id": test_user_id,
            "content": chunk_text,
            "embedding": embedding,
            "chunk_index": idx,
        })

    supabase.table("chunks").insert(chunk_records).execute()
    supabase.table("documents").update({"chunk_count": len(chunks)}).eq("id", test_document_id).execute()

    print(f"[PASS] Setup - created document: {test_document_id} with {len(chunks)} chunks")


async def test_basic_execution():
    """Test basic sub-agent execution with a real document."""
    print("\n=== Test: Basic Sub-Agent Execution ===")

    request = SubAgentRequest(
        task_description="What is the project budget and completion target date?",
        document_id=test_document_id,
        parent_depth=0,
        user_id=test_user_id,
    )

    result = await execute_subagent(request, test_user_id)

    assert result.status == "completed", f"Expected completed, got {result.status}: {result.error}"
    assert result.result is not None, "Result should not be None"
    assert len(result.result) > 0, "Result should not be empty"
    assert result.document_name == "phoenix_report.txt", f"Expected phoenix_report.txt, got {result.document_name}"
    assert len(result.reasoning_steps) > 0, "Should have reasoning steps"

    # Check that the response references actual document content
    response_lower = result.result.lower()
    has_budget = "2.4" in response_lower or "million" in response_lower
    has_date = "march" in response_lower or "2025" in response_lower

    if has_budget and has_date:
        print(f"[PASS] Response contains correct budget and date info")
    else:
        print(f"[WARN] Response may not contain expected info: {result.result[:200]}")

    print(f"[PASS] Basic execution - status={result.status}, steps={len(result.reasoning_steps)}, doc={result.document_name}")
    print(f"       Response preview: {result.result[:150]}...")
    return True


async def test_recursion_limit():
    """Test that recursion limit is enforced."""
    print("\n=== Test: Recursion Limit ===")

    request = SubAgentRequest(
        task_description="Summarize this document",
        document_id=test_document_id,
        parent_depth=2,  # At limit
        user_id=test_user_id,
    )

    result = await execute_subagent(request, test_user_id)

    assert result.status == "failed", f"Expected failed, got {result.status}"
    assert result.error == "Recursion limit exceeded", f"Expected recursion error, got: {result.error}"

    print(f"[PASS] Recursion limit - status={result.status}, error={result.error}")
    return True


async def test_document_not_found():
    """Test handling of non-existent document."""
    print("\n=== Test: Document Not Found ===")

    request = SubAgentRequest(
        task_description="Analyze this document",
        document_id="00000000-0000-0000-0000-000000000000",
        parent_depth=0,
        user_id=test_user_id,
    )

    result = await execute_subagent(request, test_user_id)

    assert result.status == "failed", f"Expected failed, got {result.status}"
    assert "not found" in result.error.lower(), f"Expected 'not found' in error, got: {result.error}"

    print(f"[PASS] Document not found - status={result.status}, error={result.error}")
    return True


async def cleanup():
    """Clean up test data."""
    supabase = get_supabase_admin()
    supabase.table("documents").delete().eq("user_id", test_user_id).execute()
    try:
        supabase.storage.from_("documents").remove(
            [f"{test_user_id}/phoenix_report_subagent_test.txt"]
        )
    except Exception:
        pass
    print("\n[CLEANUP] Test data removed")


async def main():
    print("=" * 60)
    print("SUB-AGENT SERVICE TESTS")
    print("=" * 60)

    await setup()

    results = []
    try:
        results.append(("Basic Execution", await test_basic_execution()))
        results.append(("Recursion Limit", await test_recursion_limit()))
        results.append(("Document Not Found", await test_document_not_found()))
    finally:
        await cleanup()

    print("\n" + "=" * 60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")
    print("=" * 60)

    if passed < total:
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
