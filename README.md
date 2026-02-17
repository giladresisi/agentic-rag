# Agentic RAG Application - Full Masterclass Implementation

A complete agentic RAG system implementing all 8 modules of the [![Claude Code RAG Masterclass](./video-thumbnail.png)](https://www.youtube.com/watch?v=xgPWCuqLoek).

This repository demonstrates the full capabilities of building complex AI applications through collaboration with Claude Code.

## What This Is

A fully implemented agentic RAG application built by collaborating with Claude Code, showcasing all 8 modules from the RAG Masterclass. This is not a tutorial in progress—it's a complete reference implementation demonstrating document ingestion, hybrid search, tool calling, subagent delegation, and observability in a production-grade architecture (though a POC-level implementation, see 'Known Limitations' section below).

## What It Includes

- **Chat interface** with threaded conversations, streaming, tool calls, and subagent reasoning
- **Document ingestion** with drag-and-drop upload and processing status
- **Full RAG pipeline**: chunking, embedding, hybrid search, reranking
- **Agentic patterns**: text-to-SQL, web search, subagents with isolated context

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | React, TypeScript, Tailwind, shadcn/ui, Vite |
| Backend | Python, FastAPI |
| Database | Supabase (Postgres + pgvector + Auth + Storage) |
| Doc Processing | Docling |
| AI Models | Local (LM Studio) or Cloud (OpenAI, OpenRouter) |
| Observability | LangSmith |

## The 8 Modules

1. **App Shell** — Auth, chat UI, managed RAG with OpenAI Responses API
2. **BYO Retrieval + Memory** — Ingestion, pgvector, switch to generic completions API
3. **Record Manager** — Content hashing, deduplication
4. **Metadata Extraction** — LLM-extracted metadata, filtered retrieval
5. **Multi-Format Support** — PDF, DOCX, HTML, Markdown via Docling
6. **Hybrid Search & Reranking** — Keyword + vector search, RRF, reranking
7. **Additional Tools** — Text-to-SQL, web search fallback
8. **Subagents** — Isolated context, document analysis delegation

## Getting Started

For complete setup instructions including environment configuration, database migrations, and running the application, see [SETUP.md](./SETUP.md).

## Docs

- [PRD.md](./PRD.md) — What I've built (the 8 modules in detail)
- [CLAUDE.md](./CLAUDE.md) — Context for Claude Code (updated by me)
- [PROGRESS.md](./PROGRESS.md) — Track record of the build progress
- [SETUP.md](./SETUP.md) — Installation and setup instructions
- [.agents/plans/](./.agents/plans/) — Detailed implementation plans for each module
- [.agents/execution-reports/](./.agents/execution-reports/) — Post-execution summaries and metrics
- [.agents/claude-pr-reviews/](./.agents/claude-pr-reviews/) — Code review feedback from Claude
- [.agents/system-reviews/](./.agents/system-reviews/) — Process improvement analysis

## GitHub Workflows

Automated code review and fix workflows for AI-assisted development (located in [`.github/workflows/`](./.github/workflows/)):

- `claude-review.yml` / `claude-fix.yml` — Claude Code integration for PR reviews and fixes
- `codex-review.yml` / `codex-fix.yml` — OpenAI Codex integration
- `cursor-review.yml` / `cursor-fix.yml` — Cursor IDE integration
- `release-notes.yml` — Automated release notes generation

Customize workflow prompts via [`.github/workflows/prompts/`](./.github/workflows/prompts/) to tailor the review and fix processes to your project's needs.

## Future Enhancements

Beyond the current implementation, several advanced RAG techniques could further improve retrieval quality and answer accuracy:

### 1. Graph RAG

Graph-based retrieval augmentation creates knowledge graphs from documents to capture relationships and enable multi-hop reasoning. Instead of treating chunks as isolated text snippets, Graph RAG builds entity relationships and semantic connections that improve contextual understanding. Tools like **Microsoft's GraphRAG**, **LlamaIndex's Knowledge Graph Index**, and **Neo4j with LangChain** provide out-of-the-box implementations. This approach excels at answering questions requiring multi-document synthesis or relationship traversal (e.g., "How are these three research papers connected?").

### 2. Extra LLM Passes

Multiple LLM passes can enhance both retrieval precision and answer quality. Examples include:
- **Question generation per chunk**: Store questions each chunk answers well, enabling question-to-question matching during retrieval
- **Answer validation with retries**: Verify the LLM's response against retrieved context, retry with expanded context if confidence is low
- **Web search fallback validation**: Cross-reference answers with real-time web search to detect outdated or contradictory information
- **Multi-agent verification**: Use separate LLM instances to critique and refine answers before presenting to users

These techniques trade latency for accuracy, making them suitable for high-stakes use cases where correctness outweighs speed.

### 3. Advanced Chunking

Current fixed-size chunking (1000 chars with 200 char overlap) is simple but ignores document structure and semantic boundaries. Advanced approaches include:
- **Semantic chunking** (LangChain): Split documents at natural semantic boundaries using embedding similarity to detect topic shifts
- **Hybrid chunking** (Docling): Combine structural parsing (headings, sections) with content-aware splitting to preserve document hierarchy
- **Agentic chunking**: Use LLMs to dynamically determine optimal chunk boundaries based on content density and question patterns
- **Context-preserving chunking**: Prepend section headers or document metadata to each chunk for better standalone comprehension

These methods improve retrieval relevance by ensuring chunks represent coherent, self-contained units of meaning.

## Known Limitations

While all 8 modules have been implemented and core functionality is working, several areas need attention before production deployment:

1. **Incomplete Items from PROGRESS.md** — See [PROGRESS.md](./PROGRESS.md) for specific items marked as incomplete or requiring manual validation across modules.

2. **Agentic Flow Refinement** — The LLM's multi-step retrieval flow (triggering document retrieval → subagent analysis) needs further testing and system prompt refinement. Both tools work when invoked separately, but the orchestration pattern requires validation and prompt optimization.

3. **Frontend Enhancements** — Several UX improvements would upgrade the look & feel:
   - Display tool calls in conversation history (collapsible boxes)
   - Persist tool calls as messages in the database
   - Show LLM "thinking" responses in the UI
   - Improve visual feedback for multi-step agentic workflows

4. **Production Hardening** — Additional validation and security updates needed:
   - Comprehensive input validation and sanitization
   - Rate limiting and abuse prevention
   - Error handling and recovery patterns
   - Security audit of RLS policies
   - Performance optimization and caching strategies
   - Monitoring and alerting infrastructure
   - Load testing and scalability validation

This is a POC-level implementation demonstrating the full RAG Masterclass architecture. Use it as a learning resource and reference implementation, but apply production-grade engineering practices before deploying to real users.
