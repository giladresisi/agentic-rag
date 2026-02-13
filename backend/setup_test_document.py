"""Create a test document for validation."""
import asyncio
from dotenv import load_dotenv
from test_utils import TEST_EMAIL, TEST_PASSWORD
from services.supabase_service import get_supabase_admin
from services.embedding_service import embedding_service

load_dotenv()

async def create_test_doc():
    supabase = get_supabase_admin()

    # Auth
    auth = supabase.auth.sign_in_with_password({
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    user_id = auth.user.id

    # Create document content
    content = """# Cloud Computing Guide

## Introduction
Cloud computing is a technology that delivers computing services over the internet. It provides on-demand access to computing resources like servers, storage, databases, and applications.

## Key Benefits
- Scalability: Easily scale resources up or down
- Cost-effective: Pay only for what you use
- Accessibility: Access from anywhere
- Reliability: Built-in redundancy and backup

## Common Use Cases
1. Web hosting and application deployment
2. Data storage and backup
3. Big data analytics
4. Machine learning and AI workloads

## Cloud Service Models
- Infrastructure as a Service (IaaS)
- Platform as a Service (PaaS)
- Software as a Service (SaaS)
"""

    # Create document record
    doc_response = supabase.table("documents").insert({
        "user_id": user_id,
        "filename": "cloud_computing_guide.md",
        "content_type": "text/markdown",
        "file_size_bytes": len(content),
        "storage_path": f"{user_id}/cloud_computing_guide.md",
        "status": "completed",
        "chunk_count": 0
    }).execute()

    doc_id = doc_response.data[0]["id"]

    # Chunk and embed
    chunks = embedding_service.chunk_text(content)
    embeddings = await embedding_service.generate_embeddings(chunks)

    # Save chunks
    chunk_records = []
    for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_records.append({
            "document_id": doc_id,
            "user_id": user_id,
            "content": chunk_text,
            "embedding": embedding,
            "chunk_index": idx,
            "embedding_dimensions": len(embedding)
        })

    supabase.table("chunks").insert(chunk_records).execute()

    # Update document
    supabase.table("documents").update({
        "chunk_count": len(chunks),
        "embedding_dimensions": len(embeddings[0])
    }).eq("id", doc_id).execute()

    print(f"\n[SUCCESS] Created test document with {len(chunks)} chunks")
    print(f"Document: cloud_computing_guide.md")
    print(f"User: {user_id}")

if __name__ == "__main__":
    asyncio.run(create_test_doc())
