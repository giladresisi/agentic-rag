# 1-Click Setup Script Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create `setup.sh` that takes a new clone from zero to fully configured app in one command.

**Architecture:** Single bash script at repo root. Pre-flight gate lists prerequisites + manual steps, waits for "done", then runs 6 automated steps. Uses Python (available after `uv sync`) for safe env-file patching. Trap ensures 013_sql_tool.sql placeholder is always restored.

**Tech Stack:** bash, uv, npm, npx playwright, Python, supabase CLI

---

### Task 1: Create `setup.sh`

**Files:**
- Create: `setup.sh`

Spec from PROGRESS.md §"Feature: 1-Click Setup Script":

**Pre-flight gate** — list prerequisites + manual steps, wait for user to type "done".

**Automated steps:**
1. `cd backend && uv sync`
2. `cd frontend && npm install`
3. `cd frontend && npx playwright install`
4. Pre-download Docling models (Python one-liner from SETUP.md §2)
5. Read `SUPABASE_PROJECT_REF` from `backend/.env`, run `supabase link --project-ref <ref>`
6. Patch `013_sql_tool.sql`, run `supabase db push`, restore placeholder (trap for safety)

**Key implementation notes:**
- `#!/usr/bin/env bash` + `set -euo pipefail`
- Read env vars from `.env` files with `grep`/`sed` (strip carriage returns, comments, quotes)
- Derive `VITE_SUPABASE_URL=https://<ref>.supabase.co` and write to `frontend/.env` if absent
- Windows: detect `$APPDATA/npm/supabase.exe` as fallback CLI location
- Use `MIGRATION_PATCHED` flag + `trap cleanup_migration EXIT` to guarantee restore
- Use Python (via `uv run`) for migration patch/restore to avoid sed escaping issues with passwords
- Post-script: print instructions to create test user + set TEST_EMAIL/TEST_PASSWORD in both .env files

**Validation:** Run `bash -n setup.sh` (syntax check)

---

### Task 2: Update top of `SETUP.md`

**Files:**
- Modify: `SETUP.md:1-5`

Add a "Quick Setup" section immediately after the opening paragraph pointing to `setup.sh`.

---

### Task 3: Update README.md "Getting Started" section

**Files:**
- Modify: `README.md:75-88`

Add Option 1 (1-click: `bash setup.sh`) and Option 2 (manual: follow SETUP.md).
