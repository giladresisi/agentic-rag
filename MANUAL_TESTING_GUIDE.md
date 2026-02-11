# Manual Testing Guide - Module 1 Validation

## Prerequisites
- ✅ Backend running: http://localhost:8000
- ✅ Frontend running: http://localhost:5174
- ✅ Database migration applied
- ✅ OPENAI_API_KEY configured in backend/.env

## Authentication Testing

### Test 1: Sign Up New User
1. Open http://localhost:5174
2. You should be redirected to `/login` (protected route enforcement ✅)
3. Click "Sign up" link at the bottom
4. Fill in:
   - Email: `testuser1@example.com`
   - Password: `TestPassword123!`
   - Confirm Password: `TestPassword123!`
5. Click "Sign Up"
6. **Expected:** Redirect to `/chat` with chat interface visible
7. **✅ Pass if:** You see the chat interface with message input

### Test 2: Log Out
1. While logged in from Test 1
2. Look for "Log out" or "Sign out" button
3. Click it
4. **Expected:** Redirect to `/login`
5. **✅ Pass if:** You're back at the login page

### Test 3: Log In
1. At the login page from Test 2
2. Fill in:
   - Email: `testuser1@example.com`
   - Password: `TestPassword123!`
3. Click "Login"
4. **Expected:** Redirect to `/chat`
5. **✅ Pass if:** You're back in the chat interface

### Test 4: JWT Persistence
1. While logged in, refresh the page (F5 or Ctrl+R)
2. **Expected:** You remain logged in, stay on `/chat`
3. **✅ Pass if:** No redirect to login, you stay authenticated

### Test 5: Row-Level Security (RLS)
1. Open a **second browser** (or incognito window)
2. Go to http://localhost:5174
3. Sign up as a different user:
   - Email: `testuser2@example.com`
   - Password: `TestPassword123!`
4. Create a thread and send a message in User 2's chat
5. Switch back to User 1's browser
6. **Expected:** User 1 cannot see User 2's threads/messages
7. **✅ Pass if:** Each user only sees their own data

---

## Chat Functionality Testing

### Test 6: Create Thread
1. While logged in, click "New Thread" or "+" button
2. **Expected:** New empty chat interface appears
3. **✅ Pass if:** Message input is empty and ready

### Test 7: Send Message & Streaming
1. Type a message: "Hello, what's 2+2?"
2. Send the message
3. **Expected:**
   - Your message appears immediately
   - Assistant response streams in (appears gradually)
4. **✅ Pass if:** You see streaming response from OpenAI

### Test 8: Conversation Continuity
1. In the same thread, send: "What was my previous question?"
2. **Expected:** Assistant remembers you asked about 2+2
3. **✅ Pass if:** Response references your previous message

### Test 9: Multiple Threads
1. Click "New Thread" to create a second thread
2. Send a different message in Thread 2
3. **Expected:** Thread list shows both threads in sidebar
4. Click on Thread 1
5. **Expected:** See original conversation
6. **✅ Pass if:** Can switch between threads, each shows correct messages

### Test 10: Message Persistence
1. Send a unique message: "Test persistence 12345"
2. Wait for assistant response
3. Refresh the page (F5)
4. **Expected:** Your message and response still visible
5. **✅ Pass if:** All messages persist after refresh

---

## Automated Tests Available

Run Playwright tests (where applicable):
```bash
cd frontend
npx playwright test auth.spec.ts::should enforce protected routes
```

**Note:** Full auth tests hit Supabase rate limits, so manual testing is required for signup/login flows.

---

## Troubleshooting

### Signup Fails
- Check backend logs for errors
- Verify SUPABASE_URL and SUPABASE_KEY in backend/.env
- Check browser console (F12) for network errors

### Chat Not Responding
- Check OPENAI_API_KEY is valid
- Verify using OpenAI Responses API (not deprecated Assistants API)
- Check backend logs for OpenAI API errors

### Messages Not Persisting
- Verify database migration was applied
- Check RLS policies are enabled
- Look for SQL errors in backend logs
