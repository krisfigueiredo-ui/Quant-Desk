# Security Policy

## Reporting

Do not open a public issue containing a credential, account identifier, order
payload, personal financial record, or exploitable detail. Use GitHub private
vulnerability reporting when enabled.

## Security boundaries

- Browser clients never receive brokerage credentials and never call a broker.
- Live equity and crypto activation are separate, offline, deliberate actions.
- The deterministic risk engine is the final order authority.
- Broker adapters reject undiscovered capabilities and mismatched accounts.
- Audit, database, queue, broker, market-data, or time uncertainty blocks new
  exposure.
- Secrets are environment/secret-manager inputs and are redacted from logs.
- The 37% hard kill persists and cannot reset online or automatically.

## Unsupported use

This repository is not approved for unattended live trading. PAPER is the
development default. A production security review, authenticated capability
discovery, observation period, and explicit local activation are required
before restricted live use.
