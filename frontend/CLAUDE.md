# Frontend CLAUDE.md

React + Vite + TypeScript + Tailwind + shadcn/ui frontend for RAG application.

## React Patterns

### Stale Closure Prevention with useCallback + setTimeout

**Problem:** When `useCallback` depends on state values, the callback is recreated on state changes. If the callback uses `setTimeout` or other async operations, the closures can capture stale state values.

**Symptom:** Async operations read old state values even though state has updated.

**Example Bug:**
```typescript
const [index, setIndex] = useState(0);

const doSomething = useCallback(async () => {
  await someAsyncOp();
  // This setTimeout captures current doSomething
  setTimeout(() => {
    // But this index might be stale!
    console.log(index); // Reads old value
  }, 100);
}, [index]); // Recreated when index changes!
```

**Solution:** Use refs for values read in async callbacks:
```typescript
const [index, setIndex] = useState(0);
const indexRef = useRef(index);

useEffect(() => {
  indexRef.current = index; // Always current
}, [index]);

const doSomething = useCallback(async () => {
  await someAsyncOp();
  setTimeout(() => {
    console.log(indexRef.current); // Always reads latest!
  }, 100);
}, []); // Stable - never recreated
```

**When to use:**
- setTimeout/setInterval callbacks reading state
- Promise chains reading state
- Event handlers with delayed execution
- Any async operation where timing matters

**Related:** React Strict Mode double-invocation can compound this issue.

### AbortController for Request Deduplication

**Problem:** React Strict Mode (development) or race conditions can cause duplicate HTTP requests.

**Solution:** Track pending requests with AbortController and cancel duplicates:

```typescript
const pendingRef = useRef<AbortController | null>(null);

const makeRequest = async () => {
  // Cancel previous request
  if (pendingRef.current) {
    pendingRef.current.abort();
  }

  const controller = new AbortController();
  pendingRef.current = controller;

  try {
    await fetch(url, { signal: controller.signal });
  } catch (err) {
    if (err.name === 'AbortError') return; // Expected
    throw err;
  } finally {
    pendingRef.current = null;
  }
};
```

**Benefits:**
- Prevents duplicate API calls
- Handles React Strict Mode double-invocation gracefully
- Network-level cancellation (doesn't just ignore response)

## Debugging Patterns

### React Async Timing Issues

When debugging duplicate calls, race conditions, or timing-related bugs in React:

**1. Add unique call IDs to track execution sequences:**
```typescript
const callId = Math.random().toString(36).substr(2, 9);
console.log(`[COMPONENT-${callId}] Function called`, {
  timestamp: new Date().toISOString(),
  stackTrace: new Error().stack
});
```

**2. Log state vs ref values to detect stale closures:**
```typescript
console.log({
  stateValue: myState,
  refValue: myRef.current,
  match: myState === myRef.current
});
```

**3. Check React Strict Mode:**
- Look for `<React.StrictMode>` in entry file (main.tsx/index.tsx)
- Strict Mode double-invokes callbacks in development
- Test in production build to isolate: `npm run build && npm run preview`

**4. Use AbortController for request deduplication** (see pattern above)

## Bug Investigation Process

### Systematic Debugging

**1. Form Hypothesis:**
- What behavior do you observe?
- What could cause this behavior?
- What's the most likely cause?

**2. Test Hypothesis:**
- Add minimal code to test hypothesis
- Document result (worked/failed)
- If failed, what does that rule out?

**3. Gather Evidence:**
- After 2-3 failed hypotheses, switch to evidence-gathering
- Add comprehensive logging (call IDs, timestamps, stack traces)
- Analyze patterns in the evidence

**4. Form New Hypothesis:**
- Based on evidence, what's actually happening?
- Test new hypothesis

**5. Validate Solution:**
- Does it fix the issue?
- Are there related issues to address?
- Is this defensive enough?

**Example: Duplicate Request Bug**
- Hypothesis 1: Double-click → Add guard → Failed
- Hypothesis 2: Race condition → Add locks → Failed
- Evidence: Console logs show 2.5s delay, stale state
- Hypothesis 3: Stale closure → Fix with refs → Success

## Case Study: Duplicate Upload Bug

**Issue:** Single file uploads sent TWO identical HTTP requests, causing "file already exists" error on second request.

**Root Cause:** Stale closure in `useCallback` with `setTimeout`. The `uploadNext` callback had `currentUploadIndex` as a dependency, causing recreation on every state change. When `setTimeout` fired, it called a newly-created function that read stale state.

**Solution Applied:**
1. **Primary Fix:** Use refs for state values read in async callbacks
   - `currentUploadIndexRef` tracks index with always-current value
   - `uploadNext` reads from ref instead of state
   - Remove state from `useCallback` dependencies
2. **Defense-in-Depth:** AbortController for request deduplication

**Result:** Bug resolved. Single and multi-file uploads work correctly without duplicates.

**Key Learnings:**
- Stale closures are subtle - systematic debugging with evidence-gathering is essential
- Unique call IDs track async execution sequences effectively
- Multi-layered solutions (fix root cause + add defensive layer) are more robust
- React Strict Mode can mask or compound timing issues

**Full Investigation:** See `.agents/execution-reports/duplicate-upload-bug-fix.md`
