# CI Integration Testing Plan

## Context

Add a GitHub Actions workflow that runs backend integration tests on every PR targeting `main`, using the production Docker image against a dedicated CI Supabase project (fully isolated from production). Tests run *inside* the running container via `docker exec` — this avoids installing the heavy backend deps (torch, docling, ~2GB) on the runner, since the container already has everything.

## Why this approach

- `test_utils.py` imports `from services.supabase_service import get_supabase_admin` → tests need backend Python deps → running on the raw runner requires full `uv sync` (slow, ~10-15 min)
- Tests excluded from Docker image (`.dockerignore` has `tests/`) → can't bake them in at build time
- Solution: `docker cp` test files into the running container → `docker exec` pytest → all deps already present, no extra install step
- Docker layer cache (type=gha) ensures the 500MB Docling model layer is only downloaded on the first CI run, then cached

## Files to create

| File | Description |
|------|-------------|
| `.github/workflows/integration-tests.yml` | New CI workflow (~65 lines) |

No other files need to change.

## One-time manual setup (before first CI run)

1. **Create CI Supabase project** at supabase.com (free tier, name it e.g. `agentic-rag-ci`)
2. **Link locally and apply migrations:**
   ```bash
   supabase link --project-ref <ci-project-ref>
   # Patch SQL_QUERY_ROLE_PASSWORD placeholder in 013_sql_tool.sql with a CI-specific password
   supabase db push
   # Restore *** placeholder after push
   ```
3. **Create test user** in CI project Auth dashboard (same email/password as your test account, or a new CI-specific one)
4. **Add GitHub repository secrets** (Settings → Secrets → Actions):
   - `CI_SUPABASE_URL` — `https://<ci-project-ref>.supabase.co`
   - `CI_SUPABASE_ANON_KEY`
   - `CI_SUPABASE_SERVICE_ROLE_KEY`
   - `CI_OPENAI_API_KEY` — can reuse existing key or create a dedicated one
   - `CI_TEST_EMAIL`
   - `CI_TEST_PASSWORD`
5. **Enable branch protection** on `main` → add "Integration Tests / backend-integration" as a required status check

## Workflow: `.github/workflows/integration-tests.yml`

```yaml
name: Integration Tests

on:
  pull_request:
    branches: [main]
    paths:
      - 'backend/**'

jobs:
  backend-integration:
    name: Backend integration tests
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      # Buildx enables layer-level caching via GitHub Actions cache
      - uses: docker/setup-buildx-action@v3

      # Build the production image locally (load: true).
      # cache-from/to reuses cached layers across runs — critical for
      # the 500MB Docling model layer (only downloaded on first cold run).
      - name: Build backend image
        uses: docker/build-push-action@v6
        with:
          context: ./backend
          load: true
          tags: backend:ci
          cache-from: type=gha
          cache-to: type=gha,mode=max

      # Run backend container with CI Supabase credentials.
      # PORT=8000 (internal) so test HTTP calls to localhost:8000 work
      # from inside the container via docker exec.
      - name: Start backend
        run: |
          docker run -d \
            --name backend-ci \
            -p 8000:8000 \
            -e PORT=8000 \
            -e SUPABASE_URL=${{ secrets.CI_SUPABASE_URL }} \
            -e SUPABASE_ANON_KEY=${{ secrets.CI_SUPABASE_ANON_KEY }} \
            -e SUPABASE_SERVICE_ROLE_KEY=${{ secrets.CI_SUPABASE_SERVICE_ROLE_KEY }} \
            -e OPENAI_API_KEY=${{ secrets.CI_OPENAI_API_KEY }} \
            -e TEST_EMAIL=${{ secrets.CI_TEST_EMAIL }} \
            -e TEST_PASSWORD=${{ secrets.CI_TEST_PASSWORD }} \
            -e LANGSMITH_TRACING=false \
            backend:ci

      # Wait up to 60s for the server to be ready
      - name: Wait for backend
        run: |
          for i in $(seq 1 30); do
            curl -sf http://localhost:8000/health && echo " ready" && break
            echo "Waiting... ($i/30)"
            sleep 2
          done

      # Tests are excluded from the Docker image (.dockerignore has tests/).
      # Copy them in at runtime so pytest can find + import them inside the container.
      - name: Copy tests into container
        run: docker cp ./backend/tests backend-ci:/app/tests

      # Run pytest inside the container.
      # All backend deps (torch, docling, supabase, etc.) are already installed.
      # Env vars (SUPABASE_URL, TEST_EMAIL, etc.) are inherited from docker run.
      - name: Run integration tests
        run: |
          docker exec backend-ci \
            uv run pytest tests/auto/ -v --tb=short
```

## Behavior

- **Trigger:** any PR to `main` that touches `backend/**`
- **First run:** ~15-20 min (downloads + caches Docling models and all Docker layers)
- **Subsequent runs:** ~5-8 min (Docker cache warm, only changed layers rebuilt)
- **Test output:** streams directly to GitHub Actions logs
- **On failure:** PR check fails, merge blocked (once branch protection is enabled)

## Verification

1. Open a test PR that modifies any file in `backend/`
2. Go to Actions tab → "Integration Tests" → "backend-integration" job
3. Watch logs — pytest output should appear under "Run integration tests"
4. Confirm all tests pass (or investigate failures)
5. Merge the PR after confirming CI is green

## Notes

- Frontend-only PRs skip this workflow entirely (paths filter)
- The CI Supabase project accumulates test data over time; the tests' targeted cleanup (`doc_ids=[...]`) handles per-run cleanup, but an occasional manual sweep of the CI project may be needed
- To also run on push to `main` (not just PRs), add `push: branches: [main]` to the trigger
- `LANGSMITH_TRACING=false` prevents CI test runs from polluting your LangSmith traces
