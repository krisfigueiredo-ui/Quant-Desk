# Crypto execution boundary

## Status

**Official v2 adapter implemented; disabled and unauthenticated.** It has not
called an account, market-data, or order endpoint and has not submitted a trade.
Availability depends on account and jurisdiction.

The adapter follows the official
[Robinhood Crypto Trading API documentation](https://docs.robinhood.com/crypto/trading/).
Requests use Ed25519 signatures over:

```text
api_key + timestamp + path_with_query + uppercase_method + exact_body
```

and send `x-api-key`, `x-timestamp`, and `x-signature`. The exact compact,
sorted JSON string signed is the body transmitted.

## Capability discovery

Discovery verifies:

- adapter explicitly enabled;
- system clock skew within five seconds;
- dedicated account number and active status;
- separately verified total portfolio equity;
- allowlisted trading pairs returned as API tradable;
- asset and quote increments;
- minimum amount and maximum order size;
- spot, limit, GTC, cancellation, account, and position visibility.

Any error makes `execution_ready` false. The initial allowlist contains BTC-USD
and ETH-USD only. The adapter accepts spot limit/GTC orders and rejects leverage,
derivatives, lending, staking, unsupported pairs, invalid precision, excessive
size, and sub-minimum notional.

## Verified equity requirement

The documented crypto account response exposes buying power, but Quant Desk
does not relabel buying power as total equity. Restricted-live risk therefore
requires a verified total account-equity value from a reconciled, authoritative
account source. If it is absent, discovery returns
`VERIFIED_TOTAL_EQUITY_UNAVAILABLE`.

## Order lifecycle

1. Risk authorization and mode authorization must be fresh.
2. The adapter re-verifies the dedicated account and capabilities.
3. The exact quantity, limit, side, symbol-bound client order ID, and GTC are
   signed and submitted.
4. The returned state is stored as acknowledgement, not assumed fill.
5. Pending, open, partial, filled, canceled, failed, and unknown states reconcile
   through the official order endpoint.
6. Unknown state blocks resubmission.

## Manual work still required

Create official API credentials through Robinhood’s documented process, store
them only in a local secret provider, verify jurisdiction/account availability,
test signing and discovery without order submission, reconcile account equity,
observe PAPER/SHADOW behavior, and create a separate crypto readiness record.
