# [INC-2024-019] — Data Pipeline OOM Crash Loop Causing 6-Hour Batch Delay

**Severity:** P2 | **Service:** data-pipeline | **Duration:** 378 min | **Status:** resolved
**Date:** 2024-03-22 | **Root Cause Category:** deployment

## Summary

A memory leak in the data pipeline worker process caused all worker pods to crash-loop in out-of-memory (OOM) conditions, delaying the nightly batch processing job by 6 hours. The root cause was asyncio Task objects accumulated in an unbounded list that was never garbage collected. The fix required identifying the leak source, patching the worker code, and redeploying with a weakref-based task registry.

## Timeline

- **00:10** — Nightly batch job starts on schedule; 4 worker pods initialised
- **00:38** — Memory usage on all workers reaches 90% of pod limit (1.5 GB)
- **00:42** — First worker OOMKilled by Kubernetes; pod restarts
- **00:45** — Remaining workers all OOMKilled within 3 minutes; all pods in CrashLoopBackOff
- **01:00** — On-call alert fires: data-pipeline job SLA breach (batch not completed by 01:00)
- **01:15** — Engineer begins investigation; heap dump captured from restarted pod
- **02:30** — Heap analysis identifies `pending_tasks` list holding 847,000 asyncio.Task references
- **03:45** — Fix implemented: replaced list with `weakref.WeakSet` to allow GC of completed tasks
- **04:10** — Patched image deployed to staging; memory profile confirmed stable over 30-minute run
- **05:30** — Patched image deployed to production; workers start processing backlog
- **06:28** — Batch job completes; 6 hours 18 minutes late; downstream reports delayed

## Root Cause

The pipeline worker maintained a module-level `pending_tasks = []` list to track in-flight asyncio tasks and prevent premature garbage collection. Over the course of a nightly run processing 2.1 million records, this list accumulated 847,000 Task objects that were never removed after completion. Completed tasks hold references to their coroutine frames, keeping large intermediate data structures alive. The correct fix is to use a `weakref.WeakSet`, which allows the GC to collect completed Task objects automatically while still preventing premature collection of running tasks.

## Contributing Factors

- The `pending_tasks` list was introduced 4 months prior without a corresponding cleanup path
- No memory profiling was part of the CI pipeline or pre-deployment checklist
- Pod memory limits were set at 1.5 GB with no alert until OOMKill; a warning alert at 70% was missing
- The pipeline had no circuit breaker to pause ingestion when memory thresholds were approached

## Detection Gap

Memory growth was gradual and only became critical at the end of the run after 28 minutes of processing. A Prometheus alert on memory growth rate (e.g., >50 MB/min sustained for 5 minutes) would have fired at 00:25 and allowed intervention before OOMKill. The existing alert only triggered on SLA breach, not on infrastructure health signals.

## Follow-up Actions

1. **Data engineering team:** Replace all unbounded task tracking lists with `weakref.WeakSet` across pipeline codebase; add lint rule to flag list.append in asyncio contexts
2. **Platform team:** Add Kubernetes memory warning alert at 70% of pod limit for all stateful workloads
3. **Data engineering team:** Add memory profiling step to CI pipeline using `memray` on representative workload
4. **SRE team:** Implement circuit breaker to pause batch ingestion if memory exceeds 80% for more than 2 minutes
