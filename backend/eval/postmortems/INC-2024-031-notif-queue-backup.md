# [INC-2024-031] — RabbitMQ Queue Saturation Causing 4-Hour Notification Delay

**Severity:** P2 | **Service:** notification-service | **Duration:** 257 min | **Status:** resolved
**Date:** 2024-06-11 | **Root Cause Category:** configuration

## Summary

A planned maintenance window reduced the notification-service consumer group from 20 to 2 workers to free compute resources. When the maintenance window ended, the consumer count was not restored, leaving the RabbitMQ queue to accumulate messages for 4 hours before the backup was detected. Approximately 340,000 notification messages were delayed, including time-sensitive transactional emails and push notifications.

## Timeline

- **06:00** — Planned maintenance begins; consumer group scaled from 20 to 2 to reduce load
- **07:30** — Maintenance window ends; consumer group not restored (operator assumed auto-scaling would handle it)
- **07:30** — Queue depth begins growing at approximately 1,400 messages/minute net accumulation
- **10:30** — Queue depth alert fires at 500,000 messages (threshold set for batch processing overflow, not streaming)
- **10:35** — On-call engineer identifies consumer group at 2 workers; scales to 20
- **11:20** — Queue drain rate exceeds ingest rate; backlog starts reducing
- **14:47** — Queue depth returns to normal baseline; all delayed messages delivered
- **15:00** — Incident declared resolved; customer impact assessment begun

## Root Cause

The maintenance runbook specified scaling consumers down but did not include a step to scale back up at window end. The operator assumed the HPA (Horizontal Pod Autoscaler) would restore the consumer count based on queue depth, but the HPA was configured to scale on CPU utilisation, not queue depth. With only 2 consumers processing messages, CPU utilisation remained low enough that HPA never triggered a scale-up. The queue depth alert threshold of 500,000 messages was calibrated for a different workload scenario (batch export jobs) and was far too high to catch a streaming consumer saturation event promptly.

## Contributing Factors

- Maintenance runbook lacked a post-maintenance verification checklist
- HPA was CPU-based, not queue-depth-based, creating a false assumption about auto-recovery
- Queue depth alert threshold was copied from a batch workload and never reviewed for streaming appropriateness
- No automated post-maintenance validation job confirmed consumer count after window completion

## Detection Gap

The queue depth grew for 3 hours before the alert fired. A queue depth alert at 50,000 messages (representing approximately 35 minutes of backup at normal ingest rates) would have fired at 07:55 — just 25 minutes after the maintenance window ended. Additionally, a consumer count alert set to fire when active consumers drop below 10 would have caught the under-scaling immediately.

## Follow-up Actions

1. **Notifications team:** Configure KEDA (Kubernetes Event-Driven Autoscaling) to scale consumer pods based on RabbitMQ queue depth instead of CPU
2. **SRE team:** Lower queue depth alert threshold to 50,000 messages; add separate alert for consumer count below minimum threshold (10)
3. **Notifications team:** Update maintenance runbook with explicit post-window checklist including consumer count verification
4. **Platform team:** Add automated post-maintenance health check job that validates consumer counts and queue depth 15 minutes after window close
