# Notion requirements traceability

| Sprint | Requirement | Implementation | Test / learning |
|---|---|---|---|
| 1 | ingestion, dedup, funnel, experiment baseline | `main.py`, `models.Event`, `engine.funnel_metrics/assign_variant` | `test_event_validation...`, `test_ordered_funnel...`, lab 01–02 |
| 2 | Customer 360, per-product state, consent/identity schema | `Customer`, `Identity`, `Consent`, `build_customer_state` | `test_state_keeps...`, lab 03 |
| 3 | lifecycle decision, priorities, reason/evidence, no-action | `engine.decide`, `GrowthAction`, `DecisionAudit` | support/consent tests, lab 04 |
| 4 | candidate lifecycle and queue | `GrowthAction`, action listing, stable episode idempotency | repeated decision behavior, lab 04 |
| 5 | bounded structured draft and fallback | `OutreachDraft`, `fallback_draft`, draft endpoint | end-to-end test, lab 05 |
| 6 | consent/frequency/freshness, roles, approval, outbox, fake execution | `policy_verdict`, `approve`, execute endpoint | execution/auth tests, lab 06 |
| 7 | feedback dedup, holdout primitive, health/readiness, Docker/CI/demo | `Feedback`, `ExperimentAssignment`, webhook, Docker/CI | callback/assignment tests, lab 07 |

## Deliberate external blockers

Real LMS/CRM backfill, email/sequence provider, n8n callback signature, hosting, identity provider, live PII policy and LLM vendor/budget are not selected in Notion. The code therefore stays in explicit simulation/fake mode. Statistical inference beyond absolute rates needs a preregistered metric/window/sample design.
