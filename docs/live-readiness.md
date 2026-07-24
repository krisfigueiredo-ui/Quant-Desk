# Restricted-live readiness

## Current status

**NOT READY.** PAPER is the default. Equity and crypto live flags and autonomous
execution are false. No broker was authenticated, capability discovery was not
completed, no paper/shadow observation period was supplied, strategies remain
research, and no live-readiness record was created.

## Required gates

All fields in `ReadinessChecklist` must be true:

- tests, strict typing, frontend syntax/build, secret scan, and migrations pass;
- official capability discovery and dedicated account verification pass;
- paper and shadow observation periods pass;
- no unresolved orders and all positions reconcile;
- risk configuration is versioned;
- kill switch and emergency stop are tested.

Additionally, the selected strategy must have independent train, validation,
untouched test, walk-forward, regime, cost/slippage, stability, and adequate
sample review. A readiness record never promotes a strategy by itself.

## Deliberate local procedure

Do not run this procedure until every manual gate is evidenced and reviewed.

1. Keep the application stopped. Pull and verify the approved commit.
2. Run all commands in the operations runbook and archive their outputs.
3. Authenticate the official adapter through its supported user-facing flow.
4. Run capability discovery without submitting an order.
5. Verify the dedicated account and reconcile cash, total equity, positions,
   open orders, and unknown orders.
6. Create a local JSON file containing every `ReadinessChecklist` field set to
   `true`; review and sign/version it outside the repository.
7. For equities only, run:

   ```bash
   python scripts/create_restricted_live_record.py \
     --asset-class equity --checklist /secure/path/equity-checklist.json
   ```

   Enter the dedicated account ID at the hidden prompt, then type exactly:

   ```text
   ENABLE RESTRICTED LIVE EQUITY TRADING
   ```

8. For crypto, repeat with `--asset-class crypto` and type exactly:

   ```text
   ENABLE RESTRICTED LIVE CRYPTO TRADING
   ```

9. Inspect permissions (`0600`) and hashes in the separate local record(s).
10. Set only the intended asset flag and `TRADING_MODE=RESTRICTED_LIVE`.
    `AUTONOMOUS_EXECUTION_ENABLED` should remain false for the first controlled
    observation.
11. Start one service, confirm the dashboard warning and dedicated account
    identity, and use a manually reviewed minimum-size test only after separate
    operator approval.

The general phrase `ENABLE RESTRICTED LIVE TRADING` is documented but does not
replace either asset-specific phrase. Ordinary prose is never interpreted as an
activation command. Standard live mode cannot be enabled by environment.
Restarting without the exact local records cannot expand authorization.

## Reset

Live authorization should be removed by stopping services and moving the local
asset-specific activation record into secured incident evidence. Hard-kill
reset is a different, offline incident procedure; never delete or rewrite a
kill record while workers are running.
