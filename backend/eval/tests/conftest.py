"""Session fixture: ensure postmortem docs are ingested for eval integration tests.

Run integration tests:
  EVAL_DOCS_INGESTED=true uv run python -m pytest eval/tests/ -v

Skip integration tests by setting EVAL_DOCS_INGESTED=false in backend/.env (the default).
"""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from dotenv import load_dotenv
load_dotenv()

from eval.eval_setup import _full_setup
from eval.eval_utils import get_eval_user_id


@pytest.fixture(scope="session")
def eval_ingestion_setup():
    """Ensure postmortem docs are present; yield the test user_id for retrieval.

    Skipped when EVAL_DOCS_INGESTED=false (the .env.example default).
    Set EVAL_DOCS_INGESTED=true in backend/.env to enable integration tests.

    Yields:
        str: The real test user UUID used for ingestion (pass to run_rag_pipeline).

    Docs are left in place after tests so developers can run evaluate.py immediately.
    """
    if os.getenv("EVAL_DOCS_INGESTED", "false").lower() in ("0", "false", "no", ""):
        pytest.skip("Set EVAL_DOCS_INGESTED=true in backend/.env to run integration tests")

    user_id = get_eval_user_id()
    asyncio.run(_full_setup(user_id))
    os.environ["EVAL_DOCS_INGESTED"] = "true"
    yield user_id
    # Docs intentionally left in place for manual evaluate.py run.
