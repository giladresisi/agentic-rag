# Feature: Module 6 - Hybrid Search & Reranking

**⚠️ CRITICAL - DO NOT COMMIT CHANGES:**
- Implement ALL changes, delete debug logs added during execution, leave unstaged
- User reviews with `git diff` before committing

Validate codebase patterns before implementing. Follow existing naming conventions.

## Feature Description

Enhance retrieval by combining vector similarity search with PostgreSQL full-text search, merged using Reciprocal Rank Fusion (RRF). Add optional reranking with Cohere API and local cross-encoder models. Replaces current vector-only retrieval with always-on hybrid search.

**User Value:** Better search quality combining semantic understanding (vectors) with exact keyword matching.

## User Story

As a RAG application user
I want retrieval using both semantic similarity and keyword matching
So that I get relevant results for both conceptual searches and specific terms

## Problem Statement

Vector-only retrieval limitations:
- Misses exact keyword matches when vector similarity is low
- Poor recall for proper nouns, acronyms, technical terms, dates
- Cannot leverage term frequency signals
- Example: Query "Paris Agreement 2015" may miss documents mentioning exact term

## Solution Statement

**Layer 1: Hybrid Search**
- PostgreSQL Full-Text Search (tsvector/tsquery) + Vector search
- Reciprocal Rank Fusion (RRF) to merge results
- Single RPC function `hybrid_search_chunks()`

**Layer 2: Reranking**
- Cohere Rerank API (cloud)
- Local cross-encoder models (sentence-transformers) for privacy
- Configurable via provider pattern

**Layer 3: Always-On Integration**
- Replace `match_chunks_v2` with hybrid search
- Same return schema (backward compatible)

## Feature Metadata

**Feature Type**: Enhancement
**Complexity**: High
**Primary Systems Affected**: Retrieval pipeline, database, provider service
**Dependencies**: PostgreSQL FTS (built-in), Cohere API (optional), sentence-transformers (optional)
**Breaking Changes**: No

---

## CONTEXT REFERENCES

### Relevant Codebase Files - MUST READ

- `backend/services/retrieval_service.py` (lines 11-98) - Vector-only retrieval to upgrade
- `supabase/migrations/010_variable_dimensions_no_ivfflat.sql` (lines 66-115) - Current match_chunks_v2 RPC
- `backend/services/provider_service.py` (lines 50-216) - Provider pattern for reranking
- `backend/services/chat_service.py` (lines 29-46, 167-217) - Tool definition and execution
- `backend/test_rag_retrieval.py` - Retrieval test patterns

### New Files to Create

- `supabase/migrations/013_hybrid_search.sql`
- `backend/services/reranking_service.py`
- `backend/models/reranking.py`
- `backend/test_hybrid_search.py`

### External API Research

**Cohere Rerank API v2**
- Docs: https://docs.cohere.com/reference/rerank
- Setup: Sign up at https://dashboard.cohere.com/, get API key
- Pricing: ~$1 per 1000 rerank requests
- Models: rerank-english-v3.0 (recommended)

**Local Reranking (sentence-transformers)**
- Model: `cross-encoder/ms-marco-MiniLM-L-6-v2` (80MB, fast)
- No API calls, runs locally
- One-time download from HuggingFace

### Patterns to Follow

**RRF Algorithm:**
```python
def rrf(rankings, k=60):
    scores = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0) + 1/(k + rank + 1)
    return sorted(scores, key=scores.get, reverse=True)
```

**PostgreSQL FTS:**
```sql
ALTER TABLE chunks ADD COLUMN content_tsv tsvector;
UPDATE chunks SET content_tsv = to_tsvector('english', content);
CREATE INDEX idx_chunks_content_tsv ON chunks USING gin(content_tsv);
```

---

## PARALLEL EXECUTION STRATEGY

### Dependency Graph

```
WAVE 1: External Setup (Parallel)
├─ Task 1.1: Cohere Setup (optional)
└─ Task 1.2: Local Model Setup (required)
         ↓
WAVE 2: Foundation (Parallel)
├─ Task 2.1: Database Migration
└─ Task 2.2: Pydantic Models
         ↓
WAVE 3: Services (Parallel)
├─ Task 3.1: Reranking Service
└─ Task 3.2: Config Updates
         ↓
WAVE 4: Integration (Sequential)
└─ Task 4.1: Update Retrieval Service
         ↓
WAVE 5: Testing (Parallel)
├─ Task 5.1: Unit Tests
└─ Task 5.2: E2E Tests
```

**Parallelization:** 2.5x speedup with 2 agents (5 waves vs 9 sequential)

---

## IMPLEMENTATION PLAN

### Phase 1: External Service Verification

#### Task 1.1: Cohere API Setup (Optional)

**Setup:**
1. Sign up at https://dashboard.cohere.com/
2. Create API key
3. Add to `.env`: `COHERE_API_KEY=...` and `COHERE_RERANK_MODEL=rerank-english-v3.0`
4. Install: `pip install cohere>=5.0.0`

**Verification:**
```bash
cd backend
venv/Scripts/python -c "
import cohere, os
from dotenv import load_dotenv
load_dotenv()
client = cohere.Client(api_key=os.getenv('COHERE_API_KEY'))
results = client.rerank(query='test', documents=['doc1', 'doc2'], model='rerank-english-v3.0', top_n=2)
print(f'SUCCESS: Cohere rerank returned {len(results.results)} results')
"
```

**If Fails:** Skip Cohere, use local-only mode

---

#### Task 1.2: Local Reranking Model Setup (REQUIRED)

**Setup:**
1. Install: `pip install sentence-transformers>=2.2.0`
2. Download model: `CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')`

**Verification:**
```bash
cd backend
venv/Scripts/python -c "
from sentence_transformers import CrossEncoder
model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
scores = model.predict([('query', 'doc1'), ('query', 'doc2')])
print(f'SUCCESS: Local model loaded, scores: {scores}')
"
```

**If Fails:** BLOCKER - cannot proceed

---

### Phase 2: Core Implementation

#### Task 2.1: CREATE Database Migration

**File:** `supabase/migrations/013_hybrid_search.sql`

**Components:**
1. Add `content_tsv` tsvector column to chunks
2. Create GIN index: `idx_chunks_content_tsv`
3. Create auto-update trigger for tsvector
4. Create `keyword_search_chunks()` RPC
5. Create `hybrid_search_chunks()` RPC with RRF

**Key RPC Signature:**
```sql
hybrid_search_chunks(
    query_text TEXT,
    query_embedding VECTOR,
    user_id_filter UUID,
    match_count INT DEFAULT 10,
    vector_weight REAL DEFAULT 0.5,
    keyword_weight REAL DEFAULT 0.5,
    dimension_filter INT,
    similarity_threshold REAL
) RETURNS TABLE (id, document_id, content, similarity, keyword_rank, hybrid_score)
```

**RRF Implementation:** Use CTE to combine vector and keyword results with RRF scoring: `score = vector_weight/(k+vector_rank) + keyword_weight/(k+keyword_rank)` where k=60

**Validation:** Apply migration, test with real embedding

---

#### Task 2.2: CREATE Reranking Models

**File:** `backend/models/reranking.py`

**Models:**
- `RerankDocument(id: str, text: str)`
- `RerankRequest(query: str, documents: List[RerankDocument], top_n: int, model: Optional[str])`
- `RerankResult(id: str, relevance_score: float, index: int)`
- `RerankResponse(results: List[RerankResult], model: str, provider: str)`

---

#### Task 2.3: UPDATE Config

**File:** `backend/config.py`

**Add Settings:**
```python
HYBRID_SEARCH_ENABLED: bool = True
HYBRID_VECTOR_WEIGHT: float = 0.5
HYBRID_KEYWORD_WEIGHT: float = 0.5
RERANKING_ENABLED: bool = True
RERANKING_PROVIDER: str = "local"  # Options: cohere, local
RERANKING_TOP_N: int = 5
COHERE_API_KEY: str = ""
COHERE_RERANK_MODEL: str = "rerank-english-v3.0"
LOCAL_RERANK_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
```

Update `.env.example` with all new settings

---

### Phase 3: Service Layer

#### Task 3.1: CREATE Reranking Service

**File:** `backend/services/reranking_service.py`

**Pattern:** Mirror `provider_service.py` structure

**Key Methods:**
- `get_providers()` → Dict of available providers
- `rerank_cohere(query, documents, top_n, model)` → RerankResponse
- `rerank_local(query, documents, top_n, model)` → RerankResponse
- `rerank(request: RerankRequest, provider)` → RerankResponse (main entry point)

**Implementation Notes:**
- Lazy load local model (first call only)
- Log provider/model used: `print(f"[RERANKING] Provider: {provider} | Documents: {len(docs)}")`
- Handle Cohere import error gracefully
- Validate API key for Cohere

**Validation:** Test both providers with sample data

---

#### Task 3.2: UPDATE Retrieval Service

**File:** `backend/services/retrieval_service.py`

**Changes:**
Replace `retrieve_relevant_chunks()` implementation:

1. **Hybrid Search Call:**
   - If `HYBRID_SEARCH_ENABLED`, call `hybrid_search_chunks` RPC
   - Else fallback to `match_chunks_v2` (backward compat)
   - Retrieve more results if reranking enabled (limit * 3)

2. **Reranking:**
   - If `enable_reranking` and chunks exist, call `reranking_service.rerank()`
   - Reorder chunks by rerank scores
   - Add `rerank_score` field to results

3. **Enrichment:**
   - Same as before: fetch document names, enrich chunks
   - Add hybrid scores (similarity, keyword_rank, hybrid_score) if available
   - Maintain backward compatible return schema

**Signature:** Keep same as before, add optional `enable_reranking` param

---

### Phase 4: Testing

#### Task 4.1: CREATE Test Suite

**File:** `backend/test_hybrid_search.py`

**Test Cases:**
1. `test_keyword_search_rpc()` - Keyword RPC works
2. `test_hybrid_search_rpc()` - Hybrid RPC with RRF works
3. `test_local_reranking()` - Local cross-encoder inference
4. `test_cohere_reranking()` - Cohere API (if key set)
5. `test_hybrid_retrieval_with_reranking()` - E2E pipeline
6. `test_vector_only_fallback()` - Backward compat
7. Edge cases: empty query, no matches, special chars, long queries

**Automation:** ✅ 95% automated (pytest), 1 manual UI test

**Manual Test:** Chat UI verification
1. Upload document
2. Chat: "What does the document say about [topic]?"
3. Verify sources display, improved quality

---

## TESTING STRATEGY

### Automated Tests (95%)

**Tool:** pytest
**Location:** `backend/test_hybrid_search.py`
**Execution:** `python test_hybrid_search.py`

**Coverage:**
- Unit: Keyword RPC, Hybrid RPC, Reranking (local/Cohere)
- Integration: E2E retrieval pipeline, RLS enforcement
- Edge Cases: Empty queries, no matches, special chars, failures

### Manual Tests (5%)

**Test:** Chat UI with hybrid search
**Why Manual:** Visual verification of UI, LLM tool calling
**Time:** ~10 minutes
**Steps:** Upload doc → Chat → Verify sources and quality

---

## VALIDATION COMMANDS

### Level 0: External Services (MUST PASS FIRST)

```bash
# Local model (REQUIRED)
cd backend
venv/Scripts/python -c "
from sentence_transformers import CrossEncoder
model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
scores = model.predict([('q', 'd')])
print(f'SUCCESS: Local model works, score: {scores[0]:.4f}')
"

# Cohere (OPTIONAL)
venv/Scripts/python -c "
import cohere, os
from dotenv import load_dotenv
load_dotenv()
if not os.getenv('COHERE_API_KEY'):
    print('SKIP: Cohere not configured')
    exit(0)
client = cohere.Client(api_key=os.getenv('COHERE_API_KEY'))
r = client.rerank(query='test', documents=['d1','d2'], model='rerank-english-v3.0', top_n=2)
print(f'SUCCESS: Cohere works, {len(r.results)} results')
"
```

**DO NOT PROCEED if local model fails**

---

### Level 1: Unit Tests

```bash
cd backend
venv/Scripts/python test_hybrid_search.py
venv/Scripts/python test_rag_retrieval.py  # Backward compat
```

---

### Level 2: Database Validation

```sql
-- Verify tsvector exists
SELECT content_tsv FROM chunks LIMIT 1;

-- Test keyword search
SELECT * FROM keyword_search_chunks('test', '{user_id}', 5);

-- Test hybrid search (use real embedding)
SELECT * FROM hybrid_search_chunks('test', ARRAY[...]::VECTOR, '{user_id}', 5, 0.5, 0.5, 1536, 0.0);
```

---

### Level 3: Manual UI Test

1. Start backend: `uvicorn main:app --reload`
2. Start frontend: `npm run dev`
3. Upload document → Chat → Verify sources and quality

---

## ACCEPTANCE CRITERIA

- [ ] External Services: Local model works (Cohere optional)
- [ ] Database: Migration 013 applied, tsvector populated, GIN index created
- [ ] Services: reranking_service and updated retrieval_service working
- [ ] Retrieval Quality: Hybrid search combines vector + keyword with RRF
- [ ] Reranking: Improves result ordering
- [ ] Backward Compatibility: Vector-only mode still works
- [ ] Testing: 95%+ automated coverage, all tests pass
- [ ] Performance: Hybrid search <2s, reranking <1s overhead
- [ ] No regressions in existing tests

---

## COMPLETION CHECKLIST

- [ ] Phase 1: External services verified (local REQUIRED, Cohere optional)
- [ ] All tasks completed in wave order
- [ ] Migration 013 created and applied
- [ ] Services created: reranking_service, updated retrieval_service
- [ ] Config settings added
- [ ] All automated tests passing (95%+ coverage)
- [ ] Manual UI test completed
- [ ] All validation commands executed
- [ ] All acceptance criteria met
- [ ] **⚠️ Debug logs removed (keep pre-existing only)**
- [ ] **⚠️ Changes UNSTAGED for user review**

---

## NOTES

### Design Decisions

**PostgreSQL FTS over pg_bm25:** Built-in, no extension, good performance
**RRF over other fusion:** Simple, parameter-free, research-proven (k=60)
**Both Cohere and Local:** Quality vs privacy/cost trade-off
**Always-On Hybrid:** Simpler codebase, better defaults

### Performance

- Full-text search: <100ms (GIN index)
- Hybrid search: ~2x vector-only (still <2s)
- Reranking: 100-200ms local, 200-500ms Cohere

### Future Enhancements (Out of Scope)

- Metadata filtering (requires Module 4)
- Semantic caching
- Query expansion
- Custom RRF tuning
- GPU acceleration for local reranking
