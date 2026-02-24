# backend/eval/pipeline.py
# RAG pipeline runner for evaluation.
# Calls retrieval + generation services directly as Python imports (not HTTP).
# Returns RAGAS-ready dicts: {question, answer, contexts}.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from services.retrieval_service import RetrievalService
from services.provider_service import provider_service
from services.langsmith_service import setup_langsmith
from config import settings
from pydantic import BaseModel

setup_langsmith()


class AnswerOutput(BaseModel):
    answer: str


EVAL_SYSTEM_PROMPT = (
    "You are a precise assistant. Answer the question using ONLY the information "
    "provided in the context below. If the context does not contain enough information "
    "to fully answer, say so explicitly. Do not add information from outside the context."
)


async def run_rag_pipeline(
    question: str,
    user_id: str = "00000000-0000-0000-0000-000000000000",
) -> dict:
    """Run retrieval + generation for one question.

    Uses admin client so RLS is bypassed — eval is not a user session.
    Returns RAGAS-ready dict with question, answer, and list of context strings.

    Args:
        question: The question to answer.
        user_id: The user_id used to filter chunks. Defaults to the eval placeholder UUID;
                 pass the real test user's UUID when running integration tests so the
                 retrieval filter matches the ingested documents.
    """
    chunks = await RetrievalService.retrieve_relevant_chunks(
        query=question,
        user_id=user_id,
    )
    # Use .get() to guard against malformed chunk dicts missing the "content" key
    contexts = [c.get("content", "") for c in chunks if c.get("content")]

    if not contexts:
        return {
            "question": question,
            "answer": "No relevant context found in the knowledge base.",
            "contexts": [],
        }

    context_block = "\n\n---\n\n".join(contexts)
    messages = [
        {"role": "system", "content": EVAL_SYSTEM_PROMPT},
        {"role": "user", "content": f"Context:\n{context_block}\n\nQuestion: {question}"},
    ]

    try:
        # Generate — use structured completion (not streaming) for deterministic eval output
        result = await provider_service.create_structured_completion(
            provider=settings.DEFAULT_PROVIDER,
            model=settings.DEFAULT_MODEL,
            messages=messages,
            response_schema=AnswerOutput,
            base_url=settings.DEFAULT_BASE_URL,
        )
        return {
            "question": question,
            "answer": result.answer,
            "contexts": contexts,
        }
    except Exception as exc:
        # Record failure per-sample instead of aborting the entire eval run
        return {
            "question": question,
            "answer": f"[EVAL ERROR: {exc}]",
            "contexts": contexts,
        }
