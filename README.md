# IR-Copilot — Incident Response AI Assistant

![Static Badge](https://img.shields.io/badge/automated%20tests-135-blue)

A complete agentic RAG system with multi-tenant chat interface, document ingestion pipeline, hybrid search, metadata filtering, LLM-based tool calling, reranking, and subagent delegation capabilities — with out-of-the-box **LLM observability** via [LangSmith](https://smith.langchain.com) and **evaluation** via [RAGAS](https://docs.ragas.io/).

See it in action:

[![IR-Copilot App](./video-thumbnail.png)](https://youtu.be/iybjMFp-JdQ?si=BjiJO3fdn7ontHe7)

---

## Why? What is it for?

This is a complete foundation for building agentic RAG-based chat applications that retrieve precise information from unstructured data sources without hallucinations.
It's designed for real-world use cases where organizations need intelligent document retrieval and Q&A systems:

- **Internal knowledge bases** - Corporate documentation, policies, procedures, onboarding materials
- **Customer support systems** - Product documentation, troubleshooting guides, FAQs
- **Research and analysis** - Academic papers, market research, technical reports
- **Legal and compliance** - Contracts, regulations, case law, compliance documents

<details>
<summary><strong>When to use RAG (vector search):</strong></summary>

<br>

- Your data is unstructured (documents, PDFs, manuals, reports)
- Information is scattered across many files
- Questions require semantic understanding, not exact keyword matches
- Content changes frequently (new documents added regularly)

</details>

<details>
<summary><strong>When NOT to use RAG:</strong></summary>

<br>

For structured data sources (codebases, API documentation with organized folders), consider **agentic search** instead. Modern LLMs can efficiently navigate folder structures and table-of-contents files without the overhead of chunking, embedding, and vector search. This approach has less infrastructure complexity and works better when data is already well-organized.

</details>

---

## Architecture

![System Architecture](docs/architecture.svg)

---

## Features

- **Multi-tenant chat interface** - User auth, threaded streamed chats, model selection (OpenAI, OpenRouter, local via LM Studio)
- **Document ingestion pipeline** - Multi-format document support, processing status tracking, content hashing + deduplication
- **Advanced RAG pipeline** - Intelligent chunking, embeddings, pgvector storage, metadata filtering, hybrid search, reranking
- **Agentic capabilities** - LLM tool selection (text-to-SQL, web search, retrieval), subagent delegation for complex analysis
- **Built-in observability** - Every LLM call, tool invocation, and subagent trace automatically captured in [LangSmith](https://smith.langchain.com) with zero extra instrumentation
- **RAG evaluation** - Reproducible quality benchmarking via [RAGAS](https://docs.ragas.io): scores retrieval and answer quality across faithfulness, relevancy, precision, and recall; results pushed to LangSmith as named experiments

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| Backend | Python, FastAPI |
| Database | Supabase (Postgres + pgvector + Auth + Storage + Realtime) |
| Document Processing | Docling |
| AI Models | OpenAI, OpenRouter, LM Studio (local) |
| Observability | LangSmith |
| Evaluation | RAGAS |

---

## Getting Started

**Prerequisites:** Python 3.10+, [uv](https://docs.astral.sh/uv/), Node.js 18+, Supabase account, OpenAI API key. Optional: LangSmith (observability), Cohere (reranking), Tavily (web search), OpenRouter/LM Studio.

### Option 1: 1-Click Setup (Recommended)

After cloning, fill in `backend/.env` and `frontend/.env` (copy from the `.env.example` files), then run:

```bash
bash setup.sh
```

The script installs all dependencies, pre-downloads Docling parsing models, links your Supabase project, and applies all database migrations — following a guided checklist. The whole process takes ~5 minutes plus model download time on first run.

### Option 2: Manual Setup

Follow **[SETUP.md](./SETUP.md)** step by step for full control, detailed explanations, and troubleshooting guidance.

---

## Usage

### Example Queries

The system automatically selects the appropriate tool based on your question:

**Document Retrieval Tool** - Searches your uploaded documents using hybrid search (vector + keyword):
```
"What is the training code for TechFlow training?"
"What is the qubit stability rate in the Zenith project?"
"What is the IT support extension number?"
```

**Text-to-SQL Tool** - Queries the structured incidents database:
```
"Show all P1 incidents from the last 30 days"
"Which service had the most outages this year?"
"Average resolution time for database-related incidents"
```

**Web Search Tool** - Falls back to real-time web search when documents don't have the answer:
```
"What is the current weather in London right now today?"
"What are the latest technology news headlines today?"
"What happened in the tech industry this week?"
```

**Subagent Delegation** - Spawns an isolated subagent with its own context for deep document analysis:
```
"Please analyze the document zetacorp_annual_report.txt and extract the quarterly revenue breakdown with growth rates."
"Analyze project_alpha.txt and extract all the project details."
"Summarize the key findings from research_paper.pdf."
```

The LLM intelligently routes your question to the right tool(s) and can combine multiple tools in a single conversation.

---

## More Details

<br>

<details>
<summary><strong>📚 Documentation</strong></summary>

<br>

- **[PRD.md](./PRD.md)** - Product requirements and detailed module breakdown
- **[CLAUDE.md](./CLAUDE.md)** - Project context for Claude Code (development guidelines)
- **[PROGRESS.md](./PROGRESS.md)** - Build progress tracking, completion status, challenges and solutions
- **[SETUP.md](./SETUP.md)** - Installation and setup instructions
- **[.agents/plans/](./.agents/plans/)** - Detailed implementation plans for each module
- **[.agents/execution-reports/](./.agents/execution-reports/)** - Post-execution summaries and metrics
- **[.agents/claude-pr-reviews/](./.agents/claude-pr-reviews/)** - Code review feedback from Claude
- **[.agents/system-reviews/](./.agents/system-reviews/)** - Process improvement analysis

</details>

<details>
<summary><strong>⚙️ Dev Skills &amp; Workflows</strong></summary>

<br>

This project was developed mostly using the skills in the [al-dev-env](https://github.com/giladresisi/ai-dev-env) Claude Code plugin.

---

Automated code review and fix workflows for AI-assisted development (located in [`.github/workflows/`](./.github/workflows/)):

- `claude-review.yml` / `claude-fix.yml` - Claude Code integration for PR reviews and fixes
- `codex-review.yml` / `codex-fix.yml` - OpenAI Codex integration
- `cursor-review.yml` / `cursor-fix.yml` - Cursor IDE integration
- `release-notes.yml` - Automated release notes generation

Customize workflow prompts via [`.github/workflows/prompts/`](./.github/workflows/prompts/) to tailor the review and fix processes to your project's needs.

</details>

<details>
<summary><strong>🚀 Future Enhancements</strong></summary>

<br>

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

### 4. Fully Containerized Setup

The current setup requires manual environment configuration across multiple services. A fully containerized approach would include:
- **Local Docker Compose stack**: Bundle backend, frontend, and a local Supabase instance (Postgres + pgvector + Storage + Auth) into a single `docker compose up` with no external accounts required
- **CI testing environment**: GitHub Actions workflow running the full backend and E2E test suites against the containerized stack — requires test doubles or stubs for external APIs (OpenAI, LangSmith, Tavily, Cohere) and a structured logging policy (structured JSON logs, no stdout noise) so CI can parse and assert on output
- **Automated 1-click setup**: Extend `setup.sh` to detect a Docker environment, skip manual Supabase steps, and wire credentials automatically — reducing new-user setup from ~15 manual steps to a single command

### 5. Hallucination Resistance Scoring

The current RAGAS golden dataset only covers in-distribution questions. Adding out-of-distribution queries (with ground truth "This information is not available") would give RAGAS a quantified hallucination resistance score alongside the existing retrieval quality metrics.

</details>

<details>
<summary><strong>⚠️ Known Limitations</strong></summary>

<br>

While all 8 modules have been implemented and core functionality is working, several areas need attention before production deployment:

1. **Metadata-Enhanced Retrieval Not Implemented** - Module 4 extracts and stores document metadata (summary, document_type, key_topics) but the retrieval pipeline does not yet use this metadata for filtering or boosting. Documents are retrieved purely by vector/hybrid search score. Metadata-filtered retrieval (e.g. "search only within PDFs" or "find chunks from documents about finance") is a genuine unimplemented gap.

2. **Provider Settings Not Persisted Across Sessions** - The model provider configuration (chat model, embeddings model) is stored in React in-memory state only (`useModelConfig` hook, `useState`). Settings reset to backend defaults every time the browser is refreshed or a new session starts. There is no backend persistence or localStorage for user provider preferences.

3. **Agentic Flow Refinement** - The LLM's multi-step retrieval flow (triggering document retrieval → subagent analysis) needs further testing and system prompt refinement. Both tools work when invoked separately, but the orchestration pattern requires validation and prompt optimization.

4. **Frontend Enhancements** - Several UX improvements would upgrade the look & feel:
   - Display tool calls in conversation history (collapsible boxes)
   - Persist tool calls as messages in the database
   - Show LLM "thinking" responses in the UI
   - Improve visual feedback for multi-step agentic workflows

5. **Production Hardening** - Additional validation and security updates needed:
   - Comprehensive input validation and sanitization
   - Rate limiting and abuse prevention
   - Error handling and recovery patterns
   - Security audit of RLS policies
   - Performance optimization and caching strategies
   - Monitoring and alerting infrastructure
   - Load testing and scalability validation

</details>

<details>
<summary><strong>🏆 Main Challenges Overcome</strong></summary>

<br>

- **LangSmith traces not closing** — Caught independently via dashboard inspection, diagnosed as an async generator cleanup bug, then converted the one-time finding into automated Playwright tests that poll the LangSmith API to verify trace closure on every run.

- **API lock-in spotted before it compounded** — Recognized mid-build that the OpenAI Responses API would block multi-provider support in the next module; drove the migration to stateless completions before the constraint became structural debt.

- **Bugs only real files could expose** — Synthetic PDFs passed; real-world uploads (including Hebrew filenames and complex multi-column layouts) surfaced 9 separate bugs across two sessions, all caught through hands-on validation.

- **9-issue Cloud Run gauntlet** — Identified memory constraints on Render, drove migration to Cloud Run, and resolved 9 production issues — including a blocking event loop from synchronous ML inference inside `async def` that only appeared under concurrent load.

- **Clean-slate QA pass** — After all modules shipped, set up the project from scratch as a first-time user, found 40 silently skipped tests and multiple broken selectors, and drove fixes to 86/86 backend and 39/39 E2E tests before closing.

</details>

<details>
<summary><strong>💡 Learnings & Conclusions</strong></summary>

<br>

- AI-driven dev works great with clear and meaningful context and requirements, without them it goes astray and doesn't fully cover what you wanted
- The setup for AI-driven dev must always be improved, I've built and improved my [ai-dev-env](https://github.com/giladresisi/ai-dev-env) plugin while building this project
- Take the time when validating AI-driven dev, it's up to you to check if the AI fully covered all relevant scenarios and to help it complete the coverage if it didn't
- Split the work you give AI to features / phases / fixes so it has a better chance of completing them well and you have stable versions to deploy & revert to

</details>

<details>
<summary><strong>🌟 Inspiration</strong></summary>

<br>

This project was inspired by the **[Claude Code RAG Masterclass](https://www.youtube.com/watch?v=xgPWCuqLoek)**. The original masterclass covered 8 modules of a RAG architecture, as detailed in [PRD.md](./PRD.md). On top of that foundation, many extras were added that weren't part of the original course — including RAG evaluation (RAGAS), a 1-click setup script, Cloud Run deployment, automated frontend (Playwright) and backend (pytest) tests, AI-assisted code review workflows, and observability via LangSmith.

</details>

---

## Evaluation

The RAG pipeline ships with a built-in [RAGAS](https://docs.ragas.io) evaluation suite — 15 golden Q&A pairs scored on faithfulness, answer relevancy, context precision, and context recall, with results pushed to LangSmith.

👉 **[See backend/eval/README.md for full details and run instructions](./backend/eval/README.md)**

---

## About This Project

This is a POC-level implementation demonstrating the full agentic RAG architecture, built through collaboration with Claude Code. The repository demonstrates the full capabilities of building complex AI applications with AI coding tools.
Use it as a learning resource and reference implementation, but apply production-grade engineering practices before deploying to real users, see 'Known Limitations' above for more info.

---

## License

MIT License
