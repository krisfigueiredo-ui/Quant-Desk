# Contributing

Quant Desk is safety-sensitive software. Changes that can create, authorize,
route, submit, cancel, or reconcile orders require:

1. A typed contract and explicit permission boundary.
2. Unit, contract, and failure-injection tests.
3. A fail-closed result for missing or uncertain state.
4. Documentation of operational and migration impact.
5. Confirmation that PAPER remains the default and all live flags remain false.

Run before opening a pull request:

```bash
python -m compileall -q bots scripts src apps
ruff check .
ruff format --check .
mypy src
pytest
python scripts/verify_live_disabled.py
```

Never commit credentials, account numbers, private financial records, raw
production databases, or unredacted logs. Live broker tests are prohibited in
CI.
