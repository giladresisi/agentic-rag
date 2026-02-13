"""
Targeted test for RAG tool calling with unique content that requires retrieval.
"""
import asyncio
from dotenv import load_dotenv
from services.openai_service import openai_service
from services.embedding_service import embedding_service
from services.supabase_service import get_supabase_admin

load_dotenv()

TEST_USER_EMAIL = "test@test.com"
TEST_USER_PASSWORD = "123456"
test_user_id = None


async def setup():
    global test_user_id
    supabase = get_supabase_admin()
    auth_response = supabase.auth.sign_in_with_password({
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    test_user_id = auth_response.user.id

    # Clean up
    supabase.table("documents").delete().eq("user_id", test_user_id).execute()
    print(f"[PASS] Setup complete, user: {test_user_id}")


async def create_document(content: str, filename: str):
    global test_user_id
    supabase = get_supabase_admin()

    # Create document
    doc_response = supabase.table("documents").insert({
        "user_id": test_user_id,
        "filename": filename,
        "content_type": "text/plain",
        "file_size_bytes": len(content),
        "storage_path": f"{test_user_id}/{filename}",
        "status": "completed",
        "chunk_count": 0
    }).execute()

    document_id = doc_response.data[0]["id"]

    # Chunk and embed
    chunks = embedding_service.chunk_text(content)
    embeddings = await embedding_service.generate_embeddings(chunks)

    # Save chunks
    chunk_records = []
    for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_records.append({
            "document_id": document_id,
            "user_id": test_user_id,
            "content": chunk_text,
            "embedding": embedding,
            "chunk_index": idx
        })

    supabase.table("chunks").insert(chunk_records).execute()
    supabase.table("documents").update({"chunk_count": len(chunks)}).eq("id", document_id).execute()

    print(f"[PASS] Created document: {filename} with {len(chunks)} chunks")
    return document_id


async def test_forced_retrieval():
    """Test with content that REQUIRES retrieval (fictional company)."""
    print("\n=== Test: Forced Retrieval with Unique Content ===")

    # Create document with unique, fictional information
    content = """
    AcmeTech Solutions Employee Handbook - Confidential

    Company Policy XR-789:
    All employees must complete their mandatory TechFlow training by March 15, 2024.
    The training code is ACME-TF-2024-Q1.

    Office Location:
    Our headquarters is located at 12345 Innovation Drive, Building C, Floor 7.

    IT Support Contact:
    For technical issues, contact our IT helpdesk at extension 4567.
    Email: itsupport@acmetech-internal.com
    """

    doc_id = await create_document(content, "acmetech_handbook.txt")
    await asyncio.sleep(1)  # Let embedding settle

    # Ask specific question that REQUIRES the document
    conversation_history = [
        {"role": "user", "content": "What is the training code for TechFlow training?"}
    ]

    print("\nStreaming response...")
    full_response = ""
    sources = None

    async for delta, chunk_sources in openai_service.stream_response(
        conversation_history=conversation_history,
        user_id=test_user_id,
        model="gpt-4o-mini"
    ):
        if delta:
            full_response += delta
        if chunk_sources:
            sources = chunk_sources

    print(f"Response: {full_response}\n")

    # Check for sources
    if sources and len(sources) > 0:
        print(f"[PASS] Tool called! Retrieved {len(sources)} sources:")
        for idx, source in enumerate(sources):
            print(f"  {idx+1}. {source['document_name']} (similarity: {source['similarity']:.3f})")
            print(f"     Preview: {source['chunk_content'][:80]}...")

        # Verify response contains the correct answer
        if "ACME-TF-2024-Q1" in full_response:
            print("\n[PASS] Response contains correct information from document!")
        else:
            print(f"\n[WARN] Response doesn't contain expected training code")
            print(f"Full response: {full_response}")

        return True
    else:
        print("[WARN] No sources returned")
        print(f"Response: {full_response}")
        print("\nPossible reasons:")
        print("1. LLM guessed the answer without using retrieval")
        print("2. Tool definition not compelling enough")
        print("3. Model chose not to use the tool")
        return False


async def test_with_system_prompt():
    """Test with explicit system prompt encouraging tool use."""
    print("\n=== Test: With System Prompt ===")

    conversation_history = [
        {
            "role": "system",
            "content": "You are a helpful assistant. When the user asks about specific information, ALWAYS use the retrieve_documents tool to search their uploaded documents before answering. Never guess or make up information."
        },
        {
            "role": "user",
            "content": "What is the IT support extension number?"
        }
    ]

    print("\nStreaming response...")
    full_response = ""
    sources = None

    async for delta, chunk_sources in openai_service.stream_response(
        conversation_history=conversation_history,
        user_id=test_user_id,
        model="gpt-4o-mini"
    ):
        if delta:
            full_response += delta
        if chunk_sources:
            sources = chunk_sources

    print(f"Response: {full_response}\n")

    if sources and len(sources) > 0:
        print(f"[PASS] Tool called! Retrieved {len(sources)} sources")

        if "4567" in full_response:
            print("[PASS] Correct extension number in response!")
        return True
    else:
        print("[WARN] No sources returned even with system prompt")
        return False


async def main():
    print("=" * 60)
    print("RAG TOOL CALLING VALIDATION TEST")
    print("=" * 60)

    await setup()

    result1 = await test_forced_retrieval()
    result2 = await test_with_system_prompt()

    # Clean up
    supabase = get_supabase_admin()
    supabase.table("documents").delete().eq("user_id", test_user_id).execute()

    print("\n" + "=" * 60)
    if result1 or result2:
        print("[PASS] Tool calling verified!")
        print("At least one test successfully triggered retrieval.")
    else:
        print("[WARN] Tool calling may need investigation")
        print("\nThis could indicate:")
        print("- LLM is choosing not to use the tool")
        print("- Tool definition needs improvement")
        print("- System prompt needed to encourage tool use")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
