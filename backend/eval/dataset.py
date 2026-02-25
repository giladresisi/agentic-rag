# Golden Q&A dataset for RAG evaluation.
# 15 hand-crafted questions derived from the 6 postmortem documents in postmortems/.
# Ground truths are used by RAGAS context_recall to verify retrieval completeness.
# Each question maps to a specific postmortem file via source_doc for traceability.
from dataclasses import dataclass, field
from typing import List


@dataclass
class EvalSample:
    question: str
    ground_truth: str
    source_doc: str  # postmortem filename for traceability
    # Domain keywords expected in the LLM's retrieval query arg.
    # Used by chat quality eval to deterministically check arg relevance.
    required_arg_keywords: List[str] = field(default_factory=list)


GOLDEN_DATASET: List[EvalSample] = [
    # ── INC-2024-003 auth-outage (3 questions: root cause, timeline, detection gap) ──
    EvalSample(
        question="What was the root cause of the INC-2024-003 auth service outage?",
        ground_truth=(
            "A Redis TTL misconfiguration caused by a code deployment at 14:32 UTC "
            "changed the session TTL from 3600 seconds to 360 seconds, causing mass "
            "token expiry and cache-poisoning of auth state."
        ),
        source_doc="INC-2024-003-auth-outage.md",
        required_arg_keywords=["INC-2024-003", "auth", "redis"],
    ),
    EvalSample(
        question="How long did the INC-2024-003 auth outage last?",
        ground_truth=(
            "The INC-2024-003 auth outage lasted 47 minutes, from 14:32 UTC to 15:19 UTC."
        ),
        source_doc="INC-2024-003-auth-outage.md",
        required_arg_keywords=["INC-2024-003", "auth"],
    ),
    EvalSample(
        question="What monitoring gap allowed the INC-2024-003 auth outage to go undetected for 6 minutes?",
        ground_truth=(
            "There was no alert on Redis hit-rate drop and token validation latency "
            "was not monitored, leaving only a generic 5xx spike alert that fired "
            "6 minutes after the incident began."
        ),
        source_doc="INC-2024-003-auth-outage.md",
        required_arg_keywords=["INC-2024-003", "monitoring"],
    ),
    # ── INC-2024-011 payment-db-corruption (2 questions: root cause, remediation) ──
    EvalSample(
        question="What caused the payment database corruption in INC-2024-011?",
        ground_truth=(
            "A schema migration script ran without a transaction wrapper. When the "
            "migration failed midway on adding a NOT NULL constraint, partial writes "
            "left 1,847 payment records with NULL payment_method fields."
        ),
        source_doc="INC-2024-011-payment-db-corruption.md",
        required_arg_keywords=["INC-2024-011", "payment"],
    ),
    EvalSample(
        question="How was the INC-2024-011 payment database corruption resolved?",
        ground_truth=(
            "The migration was rolled back, a data repair script backfilled the NULL "
            "payment_method fields from transaction logs for all 1,847 affected records, "
            "and the migration was re-run with a proper transaction wrapper."
        ),
        source_doc="INC-2024-011-payment-db-corruption.md",
        required_arg_keywords=["INC-2024-011", "payment"],
    ),
    # ── INC-2024-019 pipeline-memory-leak (2 questions: root cause, detection gap) ──
    EvalSample(
        question="What was the root cause of the INC-2024-019 data pipeline memory leak?",
        ground_truth=(
            "A background chunking worker accumulated file handles without releasing "
            "them because a Python context manager was missing from the PDF parser call "
            "added in v2.3.1, causing handles to leak until the pod was OOM killed."
        ),
        source_doc="INC-2024-019-pipeline-memory-leak.md",
        required_arg_keywords=["INC-2024-019", "memory", "pipeline"],
    ),
    EvalSample(
        question="Why was the INC-2024-019 memory leak not detected for over 6 hours?",
        ground_truth=(
            "There was no memory growth trend alert; only OOM kill alerting existed. "
            "The issue started overnight at 01:04 UTC and was not detected until the "
            "Kubernetes OOM kill alert fired at 07:15 UTC, a 6 hour 11 minute detection gap."
        ),
        source_doc="INC-2024-019-pipeline-memory-leak.md",
        required_arg_keywords=["INC-2024-019", "memory"],
    ),
    # ── INC-2024-027 gateway-timeout (3 questions: root cause, timeline, remediation) ──
    EvalSample(
        question="What caused the API gateway timeout cascade in INC-2024-027?",
        ground_truth=(
            "A downstream ML inference service began returning responses after 29.5 "
            "seconds, just under the 30-second gateway timeout. Under load, these "
            "near-timeout responses exhausted the connection pool of 50 connections, "
            "causing the gateway to queue and drop requests with 504 errors."
        ),
        source_doc="INC-2024-027-gateway-timeout.md",
        required_arg_keywords=["INC-2024-027", "gateway", "timeout"],
    ),
    EvalSample(
        question="How long did it take to identify the root cause of INC-2024-027?",
        ground_truth=(
            "The synthetic monitor detected elevated response times at 16:04 UTC, "
            "2 minutes after the incident started, but it took an additional 45 minutes "
            "to trace the root cause to the ML inference service near-timeout responses."
        ),
        source_doc="INC-2024-027-gateway-timeout.md",
        required_arg_keywords=["INC-2024-027", "gateway"],
    ),
    EvalSample(
        question="What remediation steps were taken for the INC-2024-027 gateway timeout cascade?",
        ground_truth=(
            "The ML inference service timeout was reduced from 30 seconds to 10 seconds, "
            "the connection pool was increased from 50 to 200, and a circuit breaker was "
            "added for the ML inference service."
        ),
        source_doc="INC-2024-027-gateway-timeout.md",
        required_arg_keywords=["INC-2024-027", "gateway"],
    ),
    # ── INC-2024-031 notif-queue-backup (2 questions: root cause, detection gap) ──
    EvalSample(
        question="What was the root cause of the INC-2024-031 notification queue backup?",
        ground_truth=(
            "A 10x surge in signup events from a viral social media post overwhelmed "
            "the notification worker which processed only 1 message per second. The queue "
            "grew to 2.1 million messages with no backpressure mechanism, and the email "
            "provider rate limit was 500 emails per minute."
        ),
        source_doc="INC-2024-031-notif-queue-backup.md",
        required_arg_keywords=["INC-2024-031", "notification", "queue"],
    ),
    EvalSample(
        question="How long did it take to detect the INC-2024-031 notification queue backup?",
        ground_truth=(
            "Detection took 2.5 hours. The incident began at 11:00 UTC but was not "
            "discovered until 13:30 UTC when users reported missing welcome emails, "
            "because no queue depth alert or email delivery lag tracking existed."
        ),
        source_doc="INC-2024-031-notif-queue-backup.md",
        required_arg_keywords=["INC-2024-031", "notification"],
    ),
    # ── INC-2024-038 deploy-rollback (2 questions: root cause, remediation) ──
    EvalSample(
        question="Why did the deployment rollback fail in INC-2024-038?",
        ground_truth=(
            "The v4.2.0 deployment included a DB migration that added a required column. "
            "When the team attempted rollback to v4.1.9, the older version did not know "
            "about the new column and crashed on startup, leaving the service down."
        ),
        source_doc="INC-2024-038-deploy-rollback.md",
        required_arg_keywords=["INC-2024-038", "rollback"],
    ),
    EvalSample(
        question="How was the INC-2024-038 failed deployment rollback resolved?",
        ground_truth=(
            "A forward-fix v4.2.1 was written that made the new column optional "
            "(nullable with a default value), deployed to staging for verification, "
            "and then deployed to production to restore the service."
        ),
        source_doc="INC-2024-038-deploy-rollback.md",
        required_arg_keywords=["INC-2024-038", "rollback"],
    ),
    # ── Cross-document question (1 question) ──
    EvalSample(
        question="Which incident had the longest resolution time and how long was it?",
        ground_truth=(
            "INC-2024-031 (notification queue backup) had the longest resolution time "
            "at 14 hours and 18 minutes, running from 11:00 UTC on Day 1 to 01:18 UTC "
            "on Day 2."
        ),
        source_doc="INC-2024-031-notif-queue-backup.md",
        required_arg_keywords=["resolution", "longest"],
    ),
]
