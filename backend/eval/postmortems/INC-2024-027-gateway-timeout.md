# [INC-2024-027] — API Gateway TLS Handshake Failures Causing 504 Cascade

**Severity:** P1 | **Service:** api-gateway | **Duration:** 38 min | **Status:** resolved
**Date:** 2024-05-03 | **Root Cause Category:** network

## Summary

An expired intermediate TLS certificate on the load balancer caused upstream TLS handshake failures between the API gateway and its backend services, resulting in 504 Gateway Timeout errors on all API routes for 38 minutes. The certificate had expired silently because the automated certificate rotation job was scoped only to leaf certificates and did not cover intermediate certificates in the chain.

## Timeline

- **14:05** — Sudden spike to 100% error rate on all API gateway routes; on-call alert fires immediately
- **14:07** — Customer support reports flood of "Service Unavailable" tickets
- **14:09** — Engineer confirms 504s on all routes; checks upstream service health — all services healthy
- **14:13** — TLS handshake errors observed in gateway logs: `SSL_ERROR_RX_CERTIFICATE_EXPIRED`
- **14:18** — Intermediate certificate expiry confirmed via `openssl s_client`; expired at 14:00 UTC
- **14:22** — New intermediate certificate issued from internal PKI
- **14:31** — Certificate deployed to load balancer; TLS handshakes begin succeeding
- **14:38** — All routes returning 200; gateway error rate at 0%; incident resolved
- **14:43** — Post-incident monitoring confirms stability

## Root Cause

The load balancer's TLS certificate chain included a 90-day intermediate certificate issued by the internal PKI authority. The automated cert-rotation job (running on a cron schedule) was configured to renew only leaf certificates using ACME. Intermediate certificates required a separate manual renewal process that was documented only in a wiki page last updated 14 months prior. No monitoring or alerting existed on intermediate certificate expiry, and the certificate expired at 14:00 UTC on a Friday — outside business hours for the team responsible for PKI management.

## Contributing Factors

- Cert rotation automation covered leaf certs only; intermediate certs were a documented manual exception that was forgotten
- No Prometheus or Datadog check monitored certificate chain expiry, only the leaf cert expiry
- The PKI wiki page had not been reviewed or linked to the on-call runbook
- Intermediate cert validity (90 days) was shorter than the quarterly review cadence

## Detection Gap

The leaf certificate expiry alert had 30-day and 7-day warning thresholds. No equivalent alert existed for intermediate certificates in the chain. A `cert-manager` check against the full chain using `openssl verify` would have detected the impending expiry 30 days prior and created a ticket automatically.

## Follow-up Actions

1. **Security team:** Extend certificate monitoring to cover all certificates in the TLS chain, not just leaf certs; configure 30-day and 7-day alerts
2. **Platform team:** Add intermediate certificate renewal to Terraform-managed cert rotation pipeline; remove manual process
3. **SRE team:** Add TLS chain validation to the synthetic monitoring probe that runs every 5 minutes against all API gateway routes
4. **Platform team:** Increase intermediate certificate validity to 365 days to reduce renewal frequency and risk
