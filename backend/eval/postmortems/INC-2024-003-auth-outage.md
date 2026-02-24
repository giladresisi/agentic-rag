# [INC-2024-003] — Auth Service JWT Validation Timeout Cascade

**Severity:** P1 | **Service:** auth-service | **Duration:** 47 min | **Status:** resolved
**Date:** 2024-01-15 | **Root Cause Category:** database

## Summary

A Redis TTL misconfiguration caused all JWT token cache entries to expire simultaneously, forcing every authentication request to hit PostgreSQL directly. The resulting connection pool exhaustion caused a cascading failure that brought the auth-service down for 47 minutes, affecting all users unable to log in or refresh tokens during the window.

## Timeline

- **02:14** — On-call alert fires: auth-service error rate exceeds 15% threshold
- **02:17** — Engineer acknowledges alert, begins investigation
- **02:22** — Redis hit rate observed at 0% in metrics dashboard; all cache misses
- **02:31** — PostgreSQL connection pool exhausted; pg_stat_activity shows 498/500 connections saturated
- **02:38** — Root cause identified: Redis TTL set to 86400 seconds had been reset to 0 during infrastructure maintenance, expiring all keys immediately
- **02:45** — Redis TTL corrected; connection pool limit raised temporarily from 500 to 750
- **02:51** — Cache warming initiated via warm-up script
- **03:01** — Auth-service error rate returns to normal; incident resolved

## Root Cause

During a routine Redis cluster maintenance window on 2024-01-14, an operator ran a `CONFIG RESETSTAT` command that inadvertently reset the `maxttl` configuration to 0. This caused all subsequently written cache entries to expire immediately on write. The effect was not observed until the following morning when traffic increased, at which point 100% of JWT validation requests fell through to PostgreSQL. The Postgres connection pool, sized for a 95% cache hit rate, was unable to absorb the full load and began rejecting new connections after 8 minutes, causing 502 errors application-wide.

## Contributing Factors

- Redis configuration changes were not version-controlled or audited post-maintenance
- No alerting existed on Redis cache hit rate dropping below 50%
- PostgreSQL connection pool was sized assuming cache as a dependency, with no burst headroom
- The on-call runbook did not include Redis TTL as a diagnostic step for auth failures

## Detection Gap

The Redis hit-rate metric existed in the dashboard but had no alert configured. The auth-service error rate alert (15% threshold) fired 8 minutes after the incident began, but the root cause took an additional 16 minutes to identify because engineers first investigated the PostgreSQL side. A Redis cache-miss alert at 40% would have reduced MTTR by an estimated 20 minutes.

## Follow-up Actions

1. **Auth team:** Add PagerDuty alert on Redis cache hit rate below 60% — threshold determined from P99 baseline analysis
2. **Platform team:** All Redis configuration changes must go through Terraform; direct `CONFIG` commands disallowed in production
3. **DBA team:** PostgreSQL connection pool to be resized with 30% burst headroom independent of cache assumptions
4. **On-call:** Add Redis TTL check and cache hit rate section to auth-service runbook
