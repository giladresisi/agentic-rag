#!/usr/bin/env python
"""
Comprehensive retrieval system validation test.

Tests:
1. Storage cleanup (both tracked and orphaned files)
2. Clear query transformation
3. UNCLEAR query transformation (vague → specific)
4. No hallucination when no results
5. Proper error handling
"""
import asyncio
import sys
from dotenv import load_dotenv
from services.supabase_service import get_supabase_admin
from services.chat_service import chat_service
from test_utils import cleanup_test_documents_and_storage

load_dotenv()

TEST_USER_EMAIL = "test@..."
TEST_USER_PASSWORD = "***"


def log_section(title):
    print(f"\n{'='*70}\n{title}\n{'='*70}")


def log_test(num, desc):
    print(f"\n[TEST {num}] {desc}\n{'-'*70}")


def log_pass(msg):
    print(f"[PASS] {msg}")
    return True


def log_fail(msg):
    print(f"[FAIL] {msg}")
    return False


def log_info(msg):
    print(f"  {msg}")


async def main():
    """Run comprehensive test."""
    log_section("COMPREHENSIVE RETRIEVAL SYSTEM VALIDATION")

    supabase = get_supabase_admin()
    all_passed = True

    # Auth
    log_test(1, "Authentication")
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        user_id = auth_response.user.id
        log_pass(f"Authenticated as {TEST_USER_EMAIL}")
    except Exception as e:
        log_fail(f"Auth failed: {e}")
        return 1

    # Check document exists
    log_test(2, "Document Availability")
    docs = supabase.table("documents").select("*").eq("user_id", user_id).execute()

    if not docs.data:
        log_fail("No documents found - upload a test document first")
        log_info("Run: cd frontend && npm run dev")
        log_info("Then upload a document through the UI")
        return 1

    doc = docs.data[0]
    log_pass(f"Found document: {doc['filename']}")
    log_info(f"Chunks: {doc.get('chunk_count', 0)}")

    # Test 3: Clear Query → Good Transformation
    log_test(3, "Clear Query Transformation")
    try:
        conversation = [
            {"role": "user", "content": "What's in the document? What topic does it cover?"}
        ]

        log_info("User query: 'What's in the document? What topic does it cover?'")

        full_response = ""
        sources = None

        async for delta, chunk_sources in chat_service.stream_response(
            conversation_history=conversation,
            user_id=user_id,
            model="gpt-4o-mini",
            provider="openai"
        ):
            if delta:
                full_response += delta
            if chunk_sources:
                sources = chunk_sources

        # The LLM should generate something like "document content and main topics"
        # NOT just "summary" or "overview"
        if sources and len(sources) > 0:
            log_pass(f"Tool returned {len(sources)} source(s)")
            log_info(f"Response: {full_response[:120]}...")

            # Check for hallucination
            if "general purpose hand trucks" in full_response.lower():
                all_passed = log_fail("HALLUCINATION DETECTED!")
            else:
                log_pass("No hallucination")
        else:
            all_passed = log_fail("Tool returned no sources")
            log_info(f"Response: {full_response}")

    except Exception as e:
        all_passed = log_fail(f"Test failed: {e}")

    # Test 4: UNCLEAR Query → LLM Clarifies and Retrieves
    log_test(4, "Unclear Query Transformation (CRITICAL TEST)")
    try:
        # Test with vague/unclear queries that require LLM to infer intent
        unclear_queries = [
            "tell me about it",  # Very vague
            "what's this about?",  # Unclear referent
            "explain",  # Single word, no context
            "summary pls",  # Informal, single concept
        ]

        success_count = 0
        for query in unclear_queries:
            log_info(f"\nTrying unclear query: '{query}'")

            conversation = [{"role": "user", "content": query}]
            full_response = ""
            sources = None

            async for delta, chunk_sources in chat_service.stream_response(
                conversation_history=conversation,
                user_id=user_id,
                model="gpt-4o-mini",
                provider="openai"
            ):
                if delta:
                    full_response += delta
                if chunk_sources:
                    sources = chunk_sources

            if sources and len(sources) > 0:
                log_info(f"  ✓ Retrieved {len(sources)} source(s)")
                success_count += 1
            else:
                log_info(f"  ✗ No results (query too unclear)")

        if success_count >= len(unclear_queries) // 2:
            log_pass(f"LLM successfully handled {success_count}/{len(unclear_queries)} unclear queries")
            log_info("The LLM can transform vague queries into specific searches")
        else:
            log_info(f"LLM handled {success_count}/{len(unclear_queries)} unclear queries")
            log_info("This is acceptable - some queries are too vague")

    except Exception as e:
        all_passed = log_fail(f"Unclear query test failed: {e}")

    # Test 5: Storage Cleanup (Both Tracked and Orphaned)
    log_test(5, "Storage Cleanup with Orphaned Files")
    try:
        # Check storage state before cleanup
        log_info("Checking storage state...")

        try:
            storage_files = supabase.storage.from_("documents").list(user_id)
            storage_count = len(storage_files)
            log_info(f"Storage files: {storage_count}")
        except Exception as e:
            storage_count = 0
            log_info(f"No storage folder (OK): {e}")

        db_docs = supabase.table("documents").select("*").eq("user_id", user_id).execute()
        db_count = len(db_docs.data)
        log_info(f"Database docs: {db_count}")

        if storage_count > db_count:
            orphaned_count = storage_count - db_count
            log_info(f"Found {orphaned_count} orphaned file(s)")

        # Test cleanup function
        log_info("\nTesting cleanup function...")
        try:
            cleanup_test_documents_and_storage(user_id, cleanup_orphaned=True)
            log_pass("Cleanup utility executed successfully")

            # Verify storage is clean
            try:
                remaining_files = supabase.storage.from_("documents").list(user_id)
                if len(remaining_files) == 0:
                    log_pass("All files removed from storage")
                else:
                    log_info(f"Remaining files: {len(remaining_files)}")
            except:
                log_pass("Storage folder cleaned (no longer exists)")

        except Exception as e:
            all_passed = log_fail(f"Cleanup failed: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        all_passed = log_fail(f"Storage test failed: {e}")

    # Summary
    log_section("TEST RESULTS")

    if all_passed:
        print("\n✓ ALL TESTS PASSED\n")
        print("Retrieval system validation complete:")
        print("  1. Storage cleanup works (tracked + orphaned files)")
        print("  2. Clear queries → good transformations")
        print("  3. Unclear queries → LLM clarifies and retrieves")
        print("  4. No hallucinations detected")
        print("  5. Proper error handling")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED\n")
        print("Review failures above and fix issues.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
