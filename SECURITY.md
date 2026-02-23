# Security Policy

## Project Scope and Disclaimer

**This repository is a reference implementation and learning template — not a production-ready application.**

It demonstrates how to wire together a RAG pipeline (FastAPI + Supabase + LLMs) for educational purposes. Before deploying this with real users or sensitive data, you are expected to conduct your own security review, harden the configuration, and apply changes appropriate for your threat model.

Specifically, this template:

- Has **not** undergone a professional security audit
- May contain **known limitations** that are acceptable for a demo but not for production (see below)
- Uses **API keys and secrets via environment variables** — proper secret management (e.g. GCP Secret Manager, AWS Secrets Manager) is left to the deployer
- Deploys a **public Cloud Run endpoint** with no rate limiting, IP allowlisting, or WAF
- Relies on **Supabase Row-Level Security** for data isolation — verify policies are correctly applied for your schema before going live

## Known Limitations

The following are intentional simplifications acceptable for a template but should be addressed before real-user deployment:

| Area | Limitation | Recommended Action |
|---|---|---|
| Rate limiting | No per-user or global rate limits on API endpoints | Add a reverse proxy (e.g. Nginx, Cloudflare) or middleware |
| File upload | No antivirus/malware scanning on uploaded documents | Integrate a scanning service before processing |
| Authentication | Relies entirely on Supabase Auth JWTs — no MFA enforced | Enable MFA in Supabase Auth settings |
| Secrets | Secrets passed as env vars, stored in Cloud Run config | Migrate to a secrets manager |
| CORS | `CORS_ORIGINS` is configurable but defaults to permissive dev values | Restrict to your exact frontend origin in production |
| Dependency pinning | Requirements are version-pinned but not audited continuously | Set up Dependabot or `pip-audit` in CI |
| Logging | Structured logs only; no audit trail for user actions | Add an audit log for sensitive operations |

## Supported Versions

This project does not follow a release versioning scheme. The `main` branch reflects the latest state. There are no older supported versions.

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not open a public GitHub issue**. Instead, use one of:

- **GitHub private vulnerability reporting** — via the [Security tab](../../security/advisories/new) of this repository (preferred)
- **Email** — contact the repository owner directly via their GitHub profile

Please include:
- A description of the vulnerability and its potential impact
- Steps to reproduce or a proof-of-concept (if safe to share)
- Any suggested mitigations

You can expect an acknowledgement within **72 hours**. Since this is an open-source template maintained by a single developer, response timelines for fixes will vary based on severity.

Vulnerabilities in **third-party dependencies** (FastAPI, Supabase client, docling, etc.) should be reported upstream to the respective projects.
