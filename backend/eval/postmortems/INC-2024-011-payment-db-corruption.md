# [INC-2024-011] — Payment DB B-tree Index Corruption After Unclean Shutdown

**Severity:** P1 | **Service:** payment-api | **Duration:** 132 min | **Status:** resolved
**Date:** 2024-02-08 | **Root Cause Category:** database

## Summary

A PostgreSQL 14.1 bug involving partial page writes caused B-tree index corruption on the payment transactions table after an unclean replica shutdown. Write operations to the payments table began failing with index corruption errors, causing payment processing to be unavailable for 2 hours and 12 minutes until the index was rebuilt and the replica promoted cleanly.

## Timeline

- **09:22** — Spike in payment-api error rate detected; 5xx responses on `/payments/charge`
- **09:25** — Database error logs show: `ERROR: index "payments_transaction_id_idx" contains unexpected zero page`
- **09:29** — On-call DBA engaged; standby replica confirmed as healthy; failover initiated
- **09:41** — Failover to replica completes; writes still failing — corruption present on replica as well
- **09:52** — Decision made to rebuild affected indexes on both primary and replica
- **10:08** — `REINDEX CONCURRENTLY` started on primary; read traffic rerouted to replica
- **10:47** — Primary index rebuild complete; write traffic restored to primary
- **11:22** — Replica index rebuild complete; replication lag cleared; full capacity restored
- **11:34** — Incident declared resolved after 30 minutes of clean metrics

## Root Cause

PostgreSQL 14.1 contains a known bug (PG Bug #17761) where B-tree indexes can become corrupt if a crash occurs during a page split operation without `full_page_writes` enabled. The replica had `full_page_writes = off` in its configuration to reduce WAL volume — a performance optimization applied 6 months prior. When the replica was shut down uncleanly during a network partition event, two in-flight B-tree page splits left the index in an inconsistent state. The corruption was replicated to the primary before detection.

## Contributing Factors

- `full_page_writes = off` was set on the replica as an undocumented performance optimisation
- PostgreSQL was running 14.1 despite 14.4 being available, which includes the fsync fix
- No index corruption checks were part of the daily database health monitoring job
- The failover runbook assumed replica integrity and did not include pre-failover index validation

## Detection Gap

Index corruption is not surfaced by standard Postgres monitoring exporters. The issue was only detected when application-level writes began failing. An `amcheck` extension job running nightly would have caught the corruption before it propagated to the primary and reduced blast radius significantly.

## Follow-up Actions

1. **DBA team:** Enable `full_page_writes = on` on all PostgreSQL instances; document performance trade-off in runbook
2. **Platform team:** Upgrade all PostgreSQL 14.x instances to 14.7+ within 30 days
3. **DBA team:** Add nightly `amcheck` job to database health monitoring for all B-tree indexes on critical tables
4. **SRE team:** Update failover runbook to include index integrity check as a pre-promotion step
