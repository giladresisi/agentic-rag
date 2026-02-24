# [INC-2024-038] — Nil Pointer Panic in Payment-API Deployment Causing 503s

**Severity:** P3 | **Service:** payment-api | **Duration:** 22 min | **Status:** resolved
**Date:** 2024-07-02 | **Root Cause Category:** deployment

## Summary

A nil pointer panic in payment-api v2.14.1 caused all payment endpoints to return 503 Service Unavailable for 22 minutes following a full production deployment. The panic originated from a missing nil check on an optional configuration field introduced in the new release. A canary deployment strategy was available but had not been enabled for this service, so the bad build reached 100% of traffic immediately upon rollout.

## Timeline

- **11:18** — payment-api v2.14.1 deployment initiated via CI/CD pipeline
- **11:19** — Deployment completes; all pods running v2.14.1
- **11:19** — Error rate immediately spikes to 98% on all payment endpoints; PagerDuty alert fires
- **11:21** — Engineer confirms panic in logs: `nil pointer dereference in config.GetWebhookConfig().Endpoint`
- **11:24** — Decision made to rollback to v2.14.0
- **11:28** — Rollback deployment initiated
- **11:34** — v2.14.0 fully deployed; error rate returns to 0%
- **11:40** — Incident declared resolved; 22 minutes total impact

## Root Cause

Payment-api v2.14.1 introduced an optional webhook configuration block (`WebhookConfig`) for a new payment provider integration. The developer who implemented the feature assumed `WebhookConfig` would always be populated because it was present in the development environment's config file. However, the production configuration did not include the new block, causing `GetWebhookConfig()` to return `nil`. The code accessed `.Endpoint` on the nil pointer without a nil check, triggering a runtime panic that crashed every request handler goroutine. The service had no canary or blue-green deployment configured, so 100% of traffic immediately hit the broken version.

## Contributing Factors

- No nil check on the return value of an optional configuration accessor
- Canary deployment was not enabled for payment-api despite it being available in the deployment platform
- The new config block was not documented in the deployment runbook or config template
- Production config was not validated against the new struct shape during CI

## Detection Gap

The CI pipeline ran unit tests against a test config that included the new `WebhookConfig` block, so the nil pointer was never exercised in testing. A config schema validation step in the deployment pipeline — comparing the deployed config against the expected struct fields — would have caught the missing key before traffic was routed to the new version.

## Follow-up Actions

1. **Payments team:** Add nil checks to all optional config accessors; add linter rule to flag unguarded field access on pointer-typed config structs
2. **Platform team:** Enable canary deployment for payment-api with 5% initial traffic weight and automatic rollback on error rate above 2%
3. **Payments team:** Add config schema validation to CI pipeline using `go-validator` to enforce required vs optional field presence against production config
4. **DevOps team:** Add production config diff check to deployment runbook; any new optional config fields must be documented and added to config template before release
