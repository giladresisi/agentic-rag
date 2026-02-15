#!/usr/bin/env python
"""Quick test to upload a document and check metadata extraction."""
import os
import sys
import time

# Add backend to path and change to backend directory
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)
os.chdir(backend_path)

from dotenv import load_dotenv
load_dotenv('../.env')

from fastapi.testclient import TestClient
from main import app
from test_utils import TEST_EMAIL, TEST_PASSWORD
from io import BytesIO

client = TestClient(app)

# Login
print("Logging in...")
response = client.post('/auth/login', json={'email': TEST_EMAIL, 'password': TEST_PASSWORD})
if response.status_code != 200:
    print(f"Login failed: {response.status_code} - {response.text}")
    sys.exit(1)

token = response.json()['access_token']
print("Login successful!")

# Upload test document with metadata extraction enabled
test_content = b"""# Introduction to Artificial Intelligence

Artificial Intelligence (AI) is revolutionizing how we interact with technology and solve complex problems. This comprehensive guide explores the fundamental concepts, applications, and future directions of AI systems.

## Machine Learning Fundamentals

Machine learning enables computers to learn from data without explicit programming. Key approaches include supervised learning, unsupervised learning, and reinforcement learning. These techniques power modern applications from recommendation systems to autonomous vehicles.

## Neural Networks and Deep Learning

Deep neural networks have transformed AI capabilities, enabling breakthroughs in computer vision, natural language processing, and speech recognition. Convolutional neural networks excel at image processing, while recurrent networks handle sequential data effectively.

## Real-World Applications

AI technologies are deployed across diverse sectors including healthcare diagnostics, financial fraud detection, personalized education, and smart manufacturing. These applications demonstrate AI's potential to augment human capabilities and drive innovation.
"""

print("\nUploading document with metadata extraction enabled...")
files = {'file': ('test_ai_guide.md', BytesIO(test_content), 'text/markdown')}
data = {
    'extract_metadata': 'true',
    'provider': 'openai',
    'model': 'text-embedding-3-small',
    'dimensions': '1536'
}

response = client.post(
    '/ingestion/upload',
    files=files,
    data=data,
    headers={'Authorization': f'Bearer {token}'}
)

if response.status_code != 200:
    print(f"Upload failed: {response.status_code} - {response.text}")
    sys.exit(1)

doc_data = response.json()
doc_id = doc_data['id']
print(f"✓ Document uploaded successfully: {doc_id}")
print(f"  Status: {doc_data['status']}")
print(f"  Metadata status: {doc_data.get('metadata_status', 'N/A')}")

# Wait for background processing
print("\nWaiting 10 seconds for background processing...")
time.sleep(10)

# Check document status
print("\nChecking document status...")
response = client.get(
    f'/ingestion/documents/{doc_id}',
    headers={'Authorization': f'Bearer {token}'}
)

if response.status_code == 200:
    doc = response.json()
    print(f"  Document status: {doc['status']}")
    print(f"  Metadata status: {doc.get('metadata_status', 'N/A')}")
    print(f"  Summary: {doc.get('summary', 'N/A')[:100] if doc.get('summary') else 'N/A'}")
    print(f"  Document type: {doc.get('document_type', 'N/A')}")
    print(f"  Key topics: {doc.get('key_topics', 'N/A')}")
    print(f"  Extracted at: {doc.get('extracted_at', 'N/A')}")

    if doc.get('metadata_status') == 'completed':
        print("\n✓ SUCCESS: Metadata extraction completed!")
    elif doc.get('metadata_status') == 'pending':
        print("\n✗ ISSUE: Metadata status still 'pending' - background task may not have run")
    elif doc.get('metadata_status') == 'failed':
        print("\n✗ ISSUE: Metadata extraction failed")
        print(f"  Error: {doc.get('error_message', 'No error message')}")
    else:
        print(f"\n? Unknown metadata status: {doc.get('metadata_status')}")
else:
    print(f"Failed to get document: {response.status_code} - {response.text}")

print("\nCheck ../debug_metadata.log for detailed logging")
