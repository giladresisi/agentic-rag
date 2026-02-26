Code Review: PR #13
Repository: giladresisi/ir-copilot
Triggered By: giladresisi
Date: 2026-02-25

Stats
Files Modified: 31
Files Added: 10
Files Deleted: 0
Lines Added: 4,318
Lines Deleted: 202

Issues Found

🔴 CRITICAL Security Issues

1. SQL Injection Vulnerability in RPC Function
File: supabase/migrations/016_production_incidents.sql:131
Issue: String concatenation in SECURITY DEFINER function creates SQL injection risk
Detail: The execute_incidents_query function directly concatenates query_text into an EXECUTE statement with elevated privileges. While basic keyword filtering exists, it's insufficient against advanced injection techniques.
Critical Problems:
Missing SET search_path = public (PostgreSQL security requirement for SECURITY DEFINER)
No semicolon blocking allows statement chaining
Incomplete dangerous keyword blocklist (missing COPY, EXPLAIN, CALL, DO, SET, EXECUTE)
Function runs with owner privileges instead of dropping to sql_query_role

2. Missing Row-Level Security
File: supabase/migrations/016_production_incidents.sql:8-21
Issue: Table created without RLS violates project security policy
Detail: Per CLAUDE.md: "All tables need Row-Level Security - users only see their own data". Even for reference data, RLS should be enabled with appropriate policies.

🟠 HIGH Priority Issues

3. Anonymous Access to Sensitive Data
File: supabase/migrations/016_production_incidents.sql:140
Issue: GRANT EXECUTE ON FUNCTION execute_incidents_query TO anon allows unauthenticated access
Detail: Unauthenticated users can query production incident data through this RPC

4. Inadequate Error Handling in Evaluation Pipeline
File: backend/eval/evaluate.py:174 and backend/eval/evaluate_tool_selection.py:97
Issue: Unguarded API calls can terminate entire evaluation runs
Detail: Single LLM API failures abort processing of all remaining samples instead of recording individual failures

5. Weak Table Validation Logic
File: backend/services/sql_service.py:74-85
Issue: Regex patterns don't handle schema-qualified or quoted identifiers
Detail: Queries like FROM public."production_incidents" could bypass validation

🟡 MEDIUM Issues

6. Production Logging Violations
Files: backend/eval/evaluate.py, backend/eval/evaluate_tool_selection.py, backend/eval/eval_utils.py
Issue: print() statements used in non-test production code
Detail: Violates CLAUDE.md logging standards - should use logging framework or database error capture

7. Unsafe Supabase .single() Usage
File: backend/eval/tests/conftest.py:130
Issue: Missing try/except for .single() calls that can raise exceptions when no rows found
Detail: Per CLAUDE.md guidelines, .single() must be wrapped in exception handling

8. Missing Null Guards in Streaming
File: backend/eval/tool_selection_pipeline.py:42-50
Issue: OpenAI streaming can emit tool_calls where tc_delta.function is None
Detail: Accessing .name or .arguments will raise AttributeError

🟢 POSITIVE Security Findings

I want to note several excellent security practices implemented:
✅ Comprehensive input validation in sql_service.py with keyword blocking and table restrictions
✅ Defense-in-depth architecture with app-level + RPC-level validation
✅ Proper privilege restrictions - sql_query_role has minimal grants
✅ No secrets exposure - all credentials properly externalized
✅ Comprehensive test coverage with proper mocking to prevent live API calls in tests

Code Quality Assessment

Strengths:

Well-structured evaluation framework with clear separation of concerns
Comprehensive test suite (23 tests) with proper mocking
Good documentation and inline comments
Follows established patterns from existing codebase
Clean migration from books to production_incidents domain

Areas for Improvement:

Code Duplication: Helper functions like get_eval_user_id() duplicated across files
Error Resilience: Several unguarded API calls that could crash evaluation runs
Type Safety: Some unsafe dictionary access patterns without .get() protection
Resource Management: Import-time side effects that could affect test isolation

Recommendations

Must Fix Before Merge:

Secure the SQL RPC function - Add search_path protection, semicolon blocking, and privilege dropping
Enable RLS on production_incidents table with appropriate policies
Remove anonymous access to incident query function
Add error handling in evaluation pipelines to prevent single failures from aborting runs

Recommended Improvements:

Replace print statements with proper logging framework usage
Add proper exception handling for Supabase .single() calls
Strengthen table validation regex patterns
Extract duplicate code to shared utilities
Add null guards for streaming API responses

Summary

Overall Assessment: This is a well-implemented evaluation framework with good architectural decisions and comprehensive functionality. The core evaluation logic is sound and the test coverage is excellent.

Security Status: NEEDS ATTENTION - The SQL injection vulnerability in the RPC function and missing RLS are serious concerns that must be addressed, but they're localized and fixable.

Code Quality: GOOD - Clean, readable code following established patterns. The issues found are primarily around error handling robustness and security hardening rather than fundamental design problems.

Recommendation: ⚠️ APPROVE WITH REQUIRED FIXES - Address the critical security issues, then this is ready for merge. The evaluation pipeline design is solid and will provide valuable insights into RAG system performance.