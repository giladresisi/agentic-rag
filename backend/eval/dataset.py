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
            "During a Redis cluster maintenance window, an operator ran a CONFIG RESETSTAT "
            "command that inadvertently reset the maxttl configuration to 0, causing all "
            "JWT cache entries to expire immediately on write. This forced every authentication "
            "request to hit PostgreSQL directly, exhausting the connection pool and causing "
            "502 errors application-wide."
        ),
        source_doc="INC-2024-003-auth-outage.md",
        required_arg_keywords=["INC-2024-003", "auth", "redis"],
    ),
    EvalSample(
        question="How long did the INC-2024-003 auth outage last?",
        ground_truth=(
            "The INC-2024-003 auth outage lasted 47 minutes, from approximately 02:14 UTC "
            "when the alert fired to 03:01 UTC when the error rate returned to normal."
        ),
        source_doc="INC-2024-003-auth-outage.md",
        required_arg_keywords=["INC-2024-003", "auth"],
    ),
    EvalSample(
        question="What monitoring gap existed in the INC-2024-003 auth service outage?",
        ground_truth=(
            "The Redis hit-rate metric existed in the dashboard but had no alert configured. "
            "The auth-service error rate alert (15% threshold) fired 8 minutes after the "
            "incident began, and the root cause took an additional 16 minutes to identify "
            "because engineers investigated the PostgreSQL side first rather than Redis."
        ),
        source_doc="INC-2024-003-auth-outage.md",
        required_arg_keywords=["INC-2024-003", "monitoring"],
    ),
    # ── INC-2024-011 payment-db-corruption (2 questions: root cause, remediation) ──
    EvalSample(
        question="What caused the payment database corruption in INC-2024-011?",
        ground_truth=(
            "A PostgreSQL 14.1 bug (PG Bug #17761) caused B-tree index corruption when "
            "the replica was shut down uncleanly during a network partition event. The "
            "replica had full_page_writes = off as a performance optimisation, which "
            "allowed in-flight B-tree page splits to leave the index in an inconsistent "
            "state that then replicated to the primary."
        ),
        source_doc="INC-2024-011-payment-db-corruption.md",
        required_arg_keywords=["INC-2024-011", "payment"],
    ),
    EvalSample(
        question="How was the INC-2024-011 payment database corruption resolved?",
        ground_truth=(
            "REINDEX CONCURRENTLY was run on both the primary and replica to rebuild the "
            "corrupted B-tree indexes. Read traffic was rerouted to the replica during the "
            "primary rebuild, and write traffic was restored to the primary once its index "
            "rebuild completed at 10:47."
        ),
        source_doc="INC-2024-011-payment-db-corruption.md",
        required_arg_keywords=["INC-2024-011", "payment"],
    ),
    # ── INC-2024-019 pipeline-memory-leak (2 questions: root cause, detection gap) ──
    EvalSample(
        question="What was the root cause of the INC-2024-019 data pipeline memory leak?",
        ground_truth=(
            "The pipeline worker maintained a module-level pending_tasks list to track "
            "in-flight asyncio tasks, but completed tasks were never removed from it. "
            "Over a nightly run processing 2.1 million records, the list accumulated "
            "847,000 Task objects that kept large intermediate data structures alive, "
            "eventually causing all worker pods to be OOMKilled."
        ),
        source_doc="INC-2024-019-pipeline-memory-leak.md",
        required_arg_keywords=["INC-2024-019", "memory", "pipeline"],
    ),
    EvalSample(
        question="Why was the INC-2024-019 memory leak not caught before the pods were OOMKilled?",
        ground_truth=(
            "Memory growth was gradual and only became critical after 28 minutes of "
            "processing. No memory growth rate alert existed; the only alert was on SLA "
            "breach (batch not completed by 01:00), which fired at 01:00 — 50 minutes "
            "after the job started, not on any infrastructure health signal."
        ),
        source_doc="INC-2024-019-pipeline-memory-leak.md",
        required_arg_keywords=["INC-2024-019", "memory"],
    ),
    # ── INC-2024-027 gateway-timeout (3 questions: root cause, timeline, remediation) ──
    EvalSample(
        question="What caused the API gateway timeout cascade in INC-2024-027?",
        ground_truth=(
            "An expired intermediate TLS certificate on the load balancer caused upstream "
            "TLS handshake failures between the API gateway and its backend services, "
            "resulting in 504 Gateway Timeout errors on all API routes. The automated "
            "cert-rotation job covered only leaf certificates and did not renew the "
            "intermediate certificate in the chain."
        ),
        source_doc="INC-2024-027-gateway-timeout.md",
        required_arg_keywords=["INC-2024-027", "gateway", "timeout"],
    ),
    EvalSample(
        question="How long did it take to identify the root cause of INC-2024-027?",
        ground_truth=(
            "The on-call alert fired at 14:05 when error rate spiked to 100%. TLS "
            "handshake errors were observed in gateway logs at 14:13, and intermediate "
            "certificate expiry was confirmed via openssl s_client at 14:18 — 13 minutes "
            "after the incident began."
        ),
        source_doc="INC-2024-027-gateway-timeout.md",
        required_arg_keywords=["INC-2024-027", "gateway"],
    ),
    EvalSample(
        question="What remediation steps were taken for the INC-2024-027 gateway timeout cascade?",
        ground_truth=(
            "A new intermediate certificate was issued from the internal PKI at 14:22 "
            "and deployed to the load balancer by 14:31, at which point TLS handshakes "
            "began succeeding and all routes returned 200 by 14:38."
        ),
        source_doc="INC-2024-027-gateway-timeout.md",
        required_arg_keywords=["INC-2024-027", "gateway"],
    ),
    # ── INC-2024-031 notif-queue-backup (2 questions: root cause, detection gap) ──
    EvalSample(
        question="What was the root cause of the INC-2024-031 notification queue backup?",
        ground_truth=(
            "A planned maintenance window scaled the notification-service consumer group "
            "from 20 to 2 workers, but the maintenance runbook had no step to restore the "
            "count when the window ended. The HPA was configured on CPU utilisation rather "
            "than queue depth, so it never triggered a scale-up, leaving 2 consumers to "
            "fall behind an accumulating queue of approximately 340,000 messages."
        ),
        source_doc="INC-2024-031-notif-queue-backup.md",
        required_arg_keywords=["INC-2024-031", "notification", "queue"],
    ),
    EvalSample(
        question="How long did it take to detect the INC-2024-031 notification queue backup?",
        ground_truth=(
            "The queue depth grew for 3 hours before detection. The maintenance window "
            "ended at 07:30 and the queue began accumulating, but the queue depth alert "
            "did not fire until 10:30 when the depth reached 500,000 messages — a "
            "threshold calibrated for batch processing, not streaming consumer saturation."
        ),
        source_doc="INC-2024-031-notif-queue-backup.md",
        required_arg_keywords=["INC-2024-031", "notification"],
    ),
    # ── INC-2024-038 deploy-rollback (2 questions: root cause, remediation) ──
    EvalSample(
        question="What caused the INC-2024-038 payment-api deployment to fail and require rollback?",
        ground_truth=(
            "The deployment rollback did not fail — it succeeded. Payment-api v2.14.1 "
            "caused a nil pointer panic because it accessed GetWebhookConfig().Endpoint "
            "without a nil check, and the production config did not include the new "
            "WebhookConfig block. Rollback to v2.14.0 was completed successfully within "
            "10 minutes, restoring the error rate to 0%."
        ),
        source_doc="INC-2024-038-deploy-rollback.md",
        required_arg_keywords=["INC-2024-038", "rollback"],
    ),
    EvalSample(
        question="How was the INC-2024-038 payment-api deployment failure resolved?",
        ground_truth=(
            "The incident was resolved by rolling back payment-api from v2.14.1 to "
            "v2.14.0. The rollback was initiated at 11:24, the v2.14.0 deployment "
            "completed at 11:34, and the error rate returned to 0%, resolving the "
            "incident after 22 minutes total impact."
        ),
        source_doc="INC-2024-038-deploy-rollback.md",
        required_arg_keywords=["INC-2024-038", "rollback"],
    ),
    # ── Cross-document question (1 question) ──
    EvalSample(
        question="Which incident had the longest resolution time and how long was it?",
        ground_truth=(
            "INC-2024-019 (data pipeline OOM crash loop) had the longest resolution time "
            "at 378 minutes (6 hours 18 minutes), from the batch job start at 00:10 to "
            "completion at 06:28. The next longest was INC-2024-031 at 257 minutes."
        ),
        source_doc="INC-2024-019-pipeline-memory-leak.md",
        required_arg_keywords=["resolution", "longest"],
    ),
]
