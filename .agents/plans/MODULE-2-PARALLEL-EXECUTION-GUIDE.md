# Module 2: Parallel Execution Guide

## Overview

Module 2 consists of 3 plans that can be partially parallelized to reduce implementation time.

## High-Level Execution Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                    PARALLEL EXECUTION                        │
├──────────────────────────┬──────────────────────────────────┤
│   Plan 4: Chat           │   Plan 5: Document               │
│   Completions Migration  │   Ingestion Pipeline             │
│   (⚠️ Medium complexity)  │   (🔴 Complex)                    │
│                          │                                  │
│   Team of 3 agents       │   Team of 4 agents               │
└──────────────────────────┴──────────────────────────────────┘
                           │
                           ▼
                  ┌────────────────────┐
                  │   Plan 6: Vector   │
                  │   Retrieval Tool   │
                  │   (✅ Simple)        │
                  │                    │
                  │   Team of 3 agents │
                  └────────────────────┘
```

## Phase 1: Parallel Track Execution

**Run these two plans simultaneously with separate teams:**

### Track A: Plan 4 (Chat Completions Migration)
**Team:** 3 agents
**Duration Estimate:** ~2-3 hours
**Deliverables:**
- Generic OpenAI-compatible client
- Provider selection UI
- Support for OpenAI, OpenRouter, Ollama, LM Studio

**Agent Assignments:**
1. **Backend-API Agent**: Provider service, config, chat router updates
2. **Backend-Core Agent**: OpenAI service refactor (Responses → Chat Completions)
3. **Frontend Agent**: Provider selector UI, integration

### Track B: Plan 5 (Document Ingestion)
**Team:** 4 agents
**Duration Estimate:** ~4-5 hours
**Deliverables:**
- Multi-format document parsing (PDF, DOCX, HTML, MD, TXT)
- Chunking and embedding pipeline
- pgvector storage
- Realtime ingestion status updates

**Agent Assignments:**
1. **Database Agent**: pgvector, migrations, storage bucket
2. **Backend-Processing Agent**: Embedding service (parsing, chunking, embedding)
3. **Backend-API Agent**: Ingestion router, models, endpoints
4. **Frontend Agent**: Upload UI, document list, realtime subscriptions

## Phase 2: Integration & Retrieval

**Run this plan after BOTH Plan 4 and Plan 5 complete:**

### Plan 6: Vector Retrieval Tool
**Team:** 3 agents
**Duration Estimate:** ~1-2 hours
**Prerequisites:**
- ✅ Plan 4 complete (need Chat Completions API for tool calling)
- ✅ Plan 5 complete (need chunks table with embeddings)

**Agent Assignments:**
1. **Database Agent**: Create match_chunks retrieval function
2. **Backend Agent**: Retrieval service, tool calling integration
3. **Frontend Agent**: Source display in message list

## Team Coordination

### Communication Protocol
- Each track should have a **lead coordinator** to manage agent handoffs
- Agents should report completion of their tasks to the coordinator
- Use task blocking/dependencies to enforce critical paths
- Regular sync points to verify integration readiness

### Checkpoints

**Checkpoint 1: Plan 4 Complete**
- ✅ Chat works with OpenAI API
- ✅ Provider selector UI functional
- ✅ Can switch between providers

**Checkpoint 2: Plan 5 Complete**
- ✅ Document upload works
- ✅ Documents are chunked and embedded
- ✅ Chunks stored in pgvector
- ✅ Realtime status updates working

**Checkpoint 3: Integration Ready**
- ✅ Both Plan 4 and Plan 5 validated
- ✅ No blocking issues
- ✅ Database schema compatible

**Checkpoint 4: Plan 6 Complete (Module 2 Complete)**
- ✅ RAG working end-to-end
- ✅ Documents retrieved correctly
- ✅ Sources displayed in UI
- ✅ Tool calling traces in LangSmith

## Time Savings

**Sequential Execution:**
- Plan 4: ~3 hours
- Plan 5: ~5 hours
- Plan 6: ~2 hours
- **Total: ~10 hours**

**Parallel Execution:**
- Phase 1: max(Plan 4, Plan 5) = ~5 hours
- Phase 2: Plan 6 = ~2 hours
- **Total: ~7 hours (30% faster)**

## Risk Management

### Potential Conflicts
1. **Database schema conflicts**: Ensure Agent 1 in both tracks coordinate on migration numbering
2. **OpenAI service conflicts**: Plan 4 refactors it, Plan 6 extends it - Plan 6 must wait
3. **Frontend routing conflicts**: Both plans add routes - coordinate naming

### Mitigation Strategies
1. Reserve migration numbers in advance (004-006 for these plans)
2. Enforce strict prerequisite checking before Plan 6 starts
3. Use feature branches if needed for true isolation
4. Test each plan independently before integration

## Success Criteria

**Module 2 Complete When:**
- ✅ All 3 plans validated independently
- ✅ End-to-end RAG flow working
- ✅ User can upload document and ask questions about it
- ✅ Retrieved sources displayed correctly
- ✅ Works with multiple providers (OpenAI, OpenRouter, local)
- ✅ RLS enforced on all new tables
- ✅ LangSmith traces show complete flow

## Next Steps

After Module 2:
- Module 3: Record Manager (deduplication)
- Module 4: Metadata Extraction
- Module 5: Multi-Format Support (already included in Plan 5)
- Module 6: Hybrid Search & Reranking
- Module 7: Additional Tools (text-to-SQL, web search)
- Module 8: Sub-Agents
