"""
MANUAL TEST - Requires a live server.
  Run: cd backend && uvicorn main:app --reload
  Then: python tests/manual/test_stream.py

Test SSE streaming endpoint manually
"""
import sys
from pathlib import Path
# Make backend and test utilities importable when run directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # backend/
sys.path.insert(0, str(Path(__file__).parent.parent))         # backend/tests/

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
TEST_EMAIL = os.getenv("TEST_EMAIL")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")


def main():
    # Get auth token first
    login_response = requests.post('http://localhost:8000/auth/login', json={
        'email': TEST_EMAIL,
        'password': TEST_PASSWORD
    })
    token = login_response.json()['access_token']
    print(f"+ Logged in, token: {token[:20]}...")

    # Get or create a thread
    threads_response = requests.get(
        'http://localhost:8000/chat/threads',
        headers={'Authorization': f'Bearer {token}'}
    )
    threads = threads_response.json()
    if threads:
        thread_id = threads[0]['id']
        print(f"+ Using existing thread: {thread_id}")
    else:
        create_response = requests.post(
            'http://localhost:8000/chat/threads',
            headers={'Authorization': f'Bearer {token}'},
            json={'title': 'Test Thread'}
        )
        thread_id = create_response.json()['id']
        print(f"+ Created new thread: {thread_id}")

    # Send a message and stream the response
    print("\n+ Sending message and streaming response...\n")
    response = requests.post(
        f'http://localhost:8000/chat/threads/{thread_id}/messages',
        headers={
            'Authorization': f'Bearer {token}',
            'Accept': 'text/event-stream',
        },
        json={'content': 'Say hello in 3 words'},
        stream=True
    )

    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data = line_str[6:]
                if data == '[DONE]':
                    print("\n+ Stream completed!")
                    break
                try:
                    parsed = json.loads(data)
                    if parsed.get('type') == 'content_delta':
                        print(parsed['delta'], end='', flush=True)
                except json.JSONDecodeError:
                    pass


if __name__ == "__main__":
    main()
