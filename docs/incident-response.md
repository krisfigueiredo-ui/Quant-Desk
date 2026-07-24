# Incident response

## Priorities

Protect account state, prevent duplicate or new exposure, preserve evidence,
reconcile through official interfaces, and communicate verified facts. Do not
assume an order filled, blindly liquidate after infrastructure failure, or
reset safeguards to make the dashboard green.

## Immediate actions

1. Use `PAUSE NEW TRADES` for a contained issue or `EMERGENCY STOP` for unsafe
   execution. The latter is deterministic and persistent.
2. Stop worker processes. Keep the API read-only if it helps observation.
3. Record incident ID, UTC time, operator, mode, last known account snapshot,
   trace IDs, broker IDs, configuration checksums, and service health.
4. At the official broker, independently inspect account, positions, open
   orders, partial fills, rejections, and cancellations.
5. Cancel only verified unfilled opening orders when the official adapter
   supports it. Do not cancel protective exits blindly.
6. Preserve database, append-only audit, redacted logs, kill record, and
   readiness records. Never copy secrets into the incident report.

## Trigger-specific guidance

- Unknown order: block resubmission; reconcile by client and broker order IDs.
- Partial fill: preserve filled quantity, lot ownership, remaining quantity,
  and fees; do not submit the original quantity again.
- Stale market/account data: block entries until a fresh authoritative snapshot.
- Database/queue/audit failure: block entries; repair durability before resume.
- Broker disconnect: keep monitoring independent data, but do not infer official
  order state.
- 10% drawdown: formal incident report and strategy-expectancy review.
- 15%+: risk-reducing only and formal review.
- 20%+: live suspension and shadow/paper signal generation.
- 37%: permanent hard kill and full forensic review.

## Recovery and reset

Recovery requires root-cause evidence, complete account reconciliation, zero
unknown orders, restored dependency health, regression tests, configuration
review, and operator approval. A hard-kill reset is offline:

1. stop all services and preserve the kill file as evidence;
2. verify the incident is closed and accounts reconcile;
3. create a reviewed reset record referencing the incident;
4. move the active kill file to an immutable evidence location;
5. restart in PAPER, test emergency stop, then observe SHADOW;
6. repeat the entire restricted-live readiness procedure if live use is still
   justified.

No agent or scheduled task may perform these steps.
