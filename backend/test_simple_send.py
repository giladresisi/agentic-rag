"""Simple test for sending a message."""
import asyncio
from test_utils import TEST_EMAIL, TEST_PASSWORD
import httpx

async def test():
    # Login
    login_resp = await httpx.AsyncClient().post(
        'http://localhost:8000/auth/login',
        json={'email': 'test@test.com', 'password': '123456'},
        timeout=10.0
    )
    token = login_resp.json()['access_token']
    print(f"Logged in: {token[:30]}...")

    # Create thread
    thread_resp = await httpx.AsyncClient().post(
        'http://localhost:8000/chat/threads',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        json={'title': 'Test Thread'},
        timeout=10.0
    )
    thread_id = thread_resp.json()['id']
    print(f"Created thread: {thread_id}")

    # Send message and stream response
    print("\nSending message and streaming response...")
    chunk_count = 0
    full_response = ""

    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream(
            'POST',
            f'http://localhost:8000/chat/threads/{thread_id}/messages',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json={'content': 'Say hello in 2 words'}
        ) as resp:
            print(f"Response status: {resp.status_code}")
            if resp.status_code != 200:
                print(f"Error: {await resp.aread()}")
                return

            async for line in resp.aiter_lines():
                if line.startswith('event: '):
                    print(f"Event: {line}")
                elif line.startswith('data: '):
                    data = line[6:]
                    if data == "[DONE]":
                        print("Received [DONE]")
                        break

                    import json
                    try:
                        event_data = json.loads(data)
                        if event_data.get('type') == 'content_delta':
                            delta = event_data.get('delta', '')
                            full_response += delta
                            chunk_count += 1
                            print(f"Chunk {chunk_count}: {repr(delta)}")
                    except:
                        print(f"Data: {data}")

    print(f"\nFull response: {full_response}")
    print(f"Total chunks: {chunk_count}")
    print("\n[OK] Test completed successfully!")

asyncio.run(test())
