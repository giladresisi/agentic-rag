#!/usr/bin/env bash
# setup.sh — IR-Copilot 1-click setup
# Works on Linux, macOS, and Windows (Git Bash / MINGW64)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_TOOL_MIGRATION="$SCRIPT_DIR/supabase/migrations/013_sql_tool.sql"

# ─── Helpers ─────────────────────────────────────────────────────────────────

# Read a value from a .env file.
# Strips inline comments, surrounding whitespace, carriage returns, and quotes.
read_env_var() {
    local file="$1" key="$2"
    grep -E "^${key}=" "$file" 2>/dev/null | head -1 \
        | sed "s/^${key}=//; s/\r$//; s/[[:space:]]*#.*\$//; s/^[[:space:]]*//; s/[[:space:]]*\$//; s/^[\"']//; s/[\"']\$//"
}

# ─── Pre-flight ───────────────────────────────────────────────────────────────

echo ""
echo "=== IR-Copilot Setup Script ==="
echo ""
echo "Before proceeding, make sure you have completed the following:"
echo ""
echo "REQUIRED tools (must already be installed):"
echo "  - Python 3.10+   (python --version or python3 --version)"
echo "  - uv             (uv --version)  https://docs.astral.sh/uv/"
echo "  - Node.js 18+    (node --version)"
echo "  - Supabase CLI   (supabase --version)  see SETUP.md for install instructions"
echo "  - Git            (git --version)"
echo ""
echo "OPTIONAL services (leave blank in .env to disable):"
echo "  - LangSmith account + API key  (observability)"
echo "  - Cohere API key               (reranking)"
echo "  - Tavily API key               (web search)"
echo ""
echo "MANUAL PRE-FLIGHT STEPS -- complete all of these before typing 'done':"
echo ""
echo "  1. Create a Supabase account + project at https://supabase.com"
echo "     Wait for provisioning (~2-3 min). From the project dashboard, copy:"
echo "       Project ID  : Settings -> General -> Project ID"
echo "       Anon key    : Settings -> API -> Legacy keys tab -> anon"
echo "       Service key : Settings -> API -> Legacy keys tab -> service_role"
echo ""
echo "  2. Copy and fill in backend/.env:"
echo "       cp backend/.env.example backend/.env"
echo "     Required values:"
echo "       SUPABASE_PROJECT_REF      (your Project ID from above)"
echo "       SUPABASE_ANON_KEY         (anon key)"
echo "       SUPABASE_SERVICE_ROLE_KEY (service_role key)"
echo "       OPENAI_API_KEY            (from https://platform.openai.com)"
echo "       SQL_QUERY_ROLE_PASSWORD   (choose any secure password)"
echo "     Optional: LANGSMITH_API_KEY, COHERE_API_KEY, TAVILY_API_KEY"
echo ""
echo "  3. Copy and fill in frontend/.env:"
echo "       cp frontend/.env.example frontend/.env"
echo "     Required values:"
echo "       SUPABASE_PROJECT_REF     (same Project ID as above)"
echo "       VITE_SUPABASE_ANON_KEY   (same anon key as above)"
echo "     Optional: VITE_BACKEND_API_URL (default: http://localhost:8000)"
echo ""
echo "  4. Log in to Supabase CLI (opens a browser window):"
echo "       supabase login"
echo ""
echo "When ALL of the above steps are complete, type 'done' and press Enter:"
read -r confirmation
if [[ "$confirmation" != "done" ]]; then
    echo "Setup cancelled."
    exit 1
fi

# ─── Validate env files ───────────────────────────────────────────────────────

echo ""
echo "Validating environment files..."

if [[ ! -f "$SCRIPT_DIR/backend/.env" ]]; then
    echo "Error: backend/.env not found."
    echo "       Run: cp backend/.env.example backend/.env  then fill in the required values."
    exit 1
fi

if [[ ! -f "$SCRIPT_DIR/frontend/.env" ]]; then
    echo "Error: frontend/.env not found."
    echo "       Run: cp frontend/.env.example frontend/.env  then fill in the required values."
    exit 1
fi

SUPABASE_PROJECT_REF=$(read_env_var "$SCRIPT_DIR/backend/.env" "SUPABASE_PROJECT_REF")
SQL_QUERY_ROLE_PASSWORD=$(read_env_var "$SCRIPT_DIR/backend/.env" "SQL_QUERY_ROLE_PASSWORD")

if [[ -z "$SUPABASE_PROJECT_REF" || "$SUPABASE_PROJECT_REF" == "xxxxxxxxxxxxx" ]]; then
    echo "Error: SUPABASE_PROJECT_REF not set in backend/.env"
    exit 1
fi

if [[ -z "$SQL_QUERY_ROLE_PASSWORD" || "$SQL_QUERY_ROLE_PASSWORD" == "secure_password_here" ]]; then
    echo "Error: SQL_QUERY_ROLE_PASSWORD not set in backend/.env"
    exit 1
fi

echo "  OK"

# ─── Derive VITE_SUPABASE_URL in frontend/.env ────────────────────────────────

VITE_SUPABASE_URL="https://${SUPABASE_PROJECT_REF}.supabase.co"
existing_url=$(read_env_var "$SCRIPT_DIR/frontend/.env" "VITE_SUPABASE_URL")
if [[ -z "$existing_url" ]]; then
    printf '\nVITE_SUPABASE_URL=%s\n' "$VITE_SUPABASE_URL" >> "$SCRIPT_DIR/frontend/.env"
    echo "  Wrote VITE_SUPABASE_URL=$VITE_SUPABASE_URL to frontend/.env"
else
    echo "  VITE_SUPABASE_URL already set in frontend/.env, skipping"
fi

# ─── Find Supabase CLI ────────────────────────────────────────────────────────

SUPABASE_CMD=""
if command -v supabase &>/dev/null 2>&1; then
    SUPABASE_CMD="supabase"
elif [[ -n "${APPDATA:-}" && -f "$APPDATA/npm/supabase.exe" ]]; then
    SUPABASE_CMD="$APPDATA/npm/supabase.exe"
fi

if [[ -z "$SUPABASE_CMD" ]]; then
    echo "Error: Supabase CLI not found."
    echo "       See SETUP.md -> Supabase Setup -> Install the CLI for platform-specific instructions."
    exit 1
fi

# ─── Migration patch/restore helpers ─────────────────────────────────────────
# Uses Python (available after uv sync in step 1) to avoid sed escaping issues.

MIGRATION_PATCHED=false

cleanup_migration() {
    if [[ "$MIGRATION_PATCHED" == "true" ]]; then
        (cd "$SCRIPT_DIR/backend" && uv run python -c "
import sys
path, pw = sys.argv[1], sys.argv[2]
with open(path) as f: c = f.read()
c = c.replace(f\"WITH LOGIN PASSWORD '{pw}'\", \"WITH LOGIN PASSWORD '***'\")
with open(path, 'w') as f: f.write(c)
" "$SQL_TOOL_MIGRATION" "$SQL_QUERY_ROLE_PASSWORD") || true
        MIGRATION_PATCHED=false
    fi
}

trap cleanup_migration EXIT

patch_migration() {
    (cd "$SCRIPT_DIR/backend" && uv run python -c "
import sys
path, pw = sys.argv[1], sys.argv[2]
with open(path) as f: c = f.read()
c = c.replace(\"WITH LOGIN PASSWORD '***'\", f\"WITH LOGIN PASSWORD '{pw}'\")
with open(path, 'w') as f: f.write(c)
" "$SQL_TOOL_MIGRATION" "$SQL_QUERY_ROLE_PASSWORD")
    MIGRATION_PATCHED=true
}

# ─── Step 1: Backend dependencies ─────────────────────────────────────────────

echo ""
echo "[1/6] Installing backend Python dependencies..."
(cd "$SCRIPT_DIR/backend" && uv sync)
echo "  Done"

# ─── Step 2: Frontend dependencies ────────────────────────────────────────────

echo ""
echo "[2/6] Installing frontend Node.js dependencies..."
(cd "$SCRIPT_DIR/frontend" && npm install)
echo "  Done"

# ─── Step 3: Playwright browser binaries ──────────────────────────────────────

echo ""
echo "[3/6] Downloading Playwright browser binaries (Chromium, for E2E tests)..."
(cd "$SCRIPT_DIR/frontend" && npx playwright install)
echo "  Done"

# ─── Step 4: Pre-download Docling models ──────────────────────────────────────

echo ""
echo "[4/6] Pre-downloading document parsing models (~500 MB, may take several minutes)..."
(cd "$SCRIPT_DIR/backend" && uv run python -W ignore::UserWarning -c "
import tempfile, os
from docling.document_converter import DocumentConverter
pdf = b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF'
with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
    f.write(pdf); tmp = f.name
try:
    converter = DocumentConverter(); converter.convert(tmp); print('Models ready')
finally:
    os.unlink(tmp)
")
echo "  Done"

# ─── Step 5: Link Supabase project ────────────────────────────────────────────

echo ""
echo "[5/6] Linking Supabase project ($SUPABASE_PROJECT_REF)..."
"$SUPABASE_CMD" link --project-ref "$SUPABASE_PROJECT_REF"
echo "  Done"

# ─── Step 6: Apply database migrations ────────────────────────────────────────

echo ""
echo "[6/6] Applying database migrations..."
patch_migration
"$SUPABASE_CMD" db push
cleanup_migration
trap - EXIT
echo "  Done"

# ─── Post-script instructions ──────────────────────────────────────────────────

echo ""
echo "============================================"
echo "Setup complete! Two manual steps remain:"
echo "============================================"
echo ""
echo "  1. Create a test user in Supabase dashboard:"
echo "     Authentication -> Users -> Add user"
echo "     Choose an email and password (used only for automated tests)."
echo ""
echo "  2. Add test credentials to BOTH .env files:"
echo "     backend/.env  : TEST_EMAIL=<your-email>  TEST_PASSWORD=<your-password>"
echo "     frontend/.env : TEST_EMAIL=<your-email>  TEST_PASSWORD=<your-password>"
echo ""
echo "Once done, you're ready to go:"
echo ""
echo "  Start the app:"
echo "    Terminal 1:  cd backend && uv run uvicorn main:app --reload --port 8000"
echo "    Terminal 2:  cd frontend && npm run dev"
echo "    Open:        http://localhost:5173"
echo ""
echo "  Run tests:"
echo "    Backend:     bash backend/tests/run_tests.sh"
echo "    Frontend:    bash frontend/tests/run_tests.sh"
echo ""
