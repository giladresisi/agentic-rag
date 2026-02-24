Code Review: PR #13
Repository: giladresisi/ir-copilot
Triggered By: giladresisi
Date: 2026-02-25

Stats
Files Modified: 31
Files Added: 8
Files Deleted: 0
Lines Added: 4,613
Lines Deleted: 263
Issues Found

🔴 CRITICAL Security Issue
File: supabase/migrations/016_production_incidents.sql:85
Issue: SQL injection vulnerability in SECURITY DEFINER function
Detail: The execute_incidents_query function concatenates user input directly into EXECUTE with SECURITY DEFINER privileges. While basic keyword filtering exists, it's bypassable and lacks proper defenses.
Specific Problems:
Missing SET search_path = public (PostgreSQL security requirement)
No semicolon blocking (allows statement chaining)
Incomplete blocklist (missing COPY, EXPLAIN, CALL, DO, SET, EXECUTE)
Function runs with owner privileges instead of dropping to sql_query_role
Fix Required:
CREATE OR REPLACE FUNCTION execute_incidents_query(query_text TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public  -- Add this line
AS $$
-- Add semicolon check and expanded blocklist
-- Add SET ROLE sql_query_role before EXECUTE
-- Add RESET ROLE after EXECUTE

🔴 CRITICAL Security Issue
File: supabase/migrations/016_production_incidents.sql:16
Issue: Missing Row-Level Security on production_incidents table
Detail: Table created without RLS violates project security rule "All tables need Row-Level Security". Even for read-only reference data, RLS should be enabled.
Fix Required:
ALTER TABLE production_incidents ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow authenticated read access" ON production_incidents FOR SELECT TO authenticated USING (true);

🟠 HIGH Security Issue
File: supabase/migrations/016_production_incidents.sql:89
Issue: Anonymous access granted to sensitive function
Detail: GRANT EXECUTE ON FUNCTION execute_incidents_query TO anon; allows unauthenticated users to query incident data.
Fix Required: Remove the anon grant, restrict to authenticated users only.

🟠 HIGH Logic Issue
File: backend/eval/pipeline.py:74
Issue: No error handling around LLM provider call
Detail: If provider_service.create_structured_completion fails (rate limit, parse error, timeout), the exception propagates and aborts the entire eval run instead of recording a failure for this sample.
Fix Required: Wrap in try/catch and return failure result to continue eval processing.

🟠 HIGH Logic Issue
File: backend/services/sql_service.py:80
Issue: Weak table validation can be bypassed
Detail: Current regex-based table validation doesn't handle quoted identifiers, schema-qualified names, or require FROM clauses. Queries like SELECT * FROM "other"."table" could bypass checks.
Fix Required: Strengthen regex patterns and require explicit FROM clause validation.

🟡 MEDIUM Issue
File: backend/eval/tool_selection_pipeline.py:159
Issue: Missing null guards on streaming tool calls
Detail: OpenAI streaming can emit tool_calls where tc_delta.function is None. Accessing .name or .arguments will raise AttributeError.
Fix Required: Add if tc_delta.function and tc_delta.function.name: guards in all three streaming loops.

🟡 MEDIUM Issue
File: backend/eval/tests/test_tool_selection.py:214
Issue: AsyncOpenAI constructor fails without API key in CI
Detail: AsyncOpenAI() constructor requires API key even though ascore() is mocked. Tests will fail in clean CI environments.
Fix Required: Pass api_key="test" or mock the constructor.

Additional Findings

Code Quality Issues (14 found)

Duplicate code: _get_eval_user_id() function duplicated between evaluate.py and evaluate_tool_selection.py
System prompt duplication: 90-line prompt copied between tool_selection_pipeline.py and chat_service.py
Unsafe list comprehension: backend/eval/pipeline.py:52 - c["content"] will KeyError on malformed chunks
Module-level side effects: backend/eval/pipeline.py:19 - setup_langsmith() at import time affects all test imports
Invalid f-strings: Multiple files have f-strings without placeholders (Ruff F541 violations)
Unsafe zip: backend/eval/evaluate.py:92 - zip without strict=True will silently truncate on length mismatch
Missing CLI flags: evaluate.py lacks --dry-run flag unlike evaluate_tool_selection.py
Silent exception swallowing: backend/eval/tests/conftest.py:62 - broad except with pass masks real setup problems
Tool streaming code triplication: Same streaming logic repeated 3x in tool_selection_pipeline.py
Dict mutation: evaluate_tool_selection.py:107 - r.pop() mutates caller's result dicts
Zero division risk: print_summary function doesn't guard against empty result lists
Missing .single() exception handling: Several places use .single() without try/catch per CLAUDE.md guidelines

Documentation Issues (5 found)

Plan filename: Missing sequence prefix - should be {sequence}.ragas-tool-call-accuracy.md
README examples outdated: Text-to-SQL examples still reference books instead of production_incidents
Missing language specifiers: Multiple fenced code blocks lack language identifiers
Stale migration note: PROGRESS.md says "uncommitted" but will be committed
Incomplete eval docs: SETUP.md documents RAGAS eval but not tool-selection eval

Test Issues (3 found)

Missing credential guards: Some test files don't validate TEST_EMAIL/TEST_PASSWORD before use
Unsafe response access: Thread creation response accessed without status code check
Invalid f-strings in tests: Multiple test files have unnecessary f-string prefixes

Summary

Found 17 issues total:

2 Critical (SQL injection, missing RLS)
3 High (anon access, error handling, validation bypass)
2 Medium (streaming guards, test setup)
10 Lower priority (code quality, docs, tests)

Must Fix Before Merge:

SQL injection in execute_incidents_query function - Add proper input validation and privilege dropping
Enable RLS on production_incidents table - Required by project security policy
Remove anonymous access to incident query function
Add error handling in eval pipeline to prevent run termination

Recommended Fixes:

Strengthen table validation in SQL service
Add null guards in streaming tool call processing
Extract duplicate code to shared modules
Add missing API key handling in tests

Code Quality: ⭐⭐⭐⭐☆ (4/5)

The implementation is well-structured with comprehensive eval pipelines and good test coverage. Security issues are localized to the SQL migration and can be addressed with targeted fixes.