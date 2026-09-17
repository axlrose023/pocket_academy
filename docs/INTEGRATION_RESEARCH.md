# Public integration research

This note records only behaviour confirmed by public documentation. Provider
credentials and the final field contracts must still be verified in the team's
accounts before an integration is enabled.

## Telegram Mini App

- The Mini App must send the raw `Telegram.WebApp.initData` value to our API;
  `initDataUnsafe` must never be trusted for authentication.
- The backend validates its HMAC signature using the bot token and rejects
  expired `auth_date` values before it reads the user data.
- Telegram IDs are stored as signed 64-bit integers.

Source: [Telegram Mini Apps](https://core.telegram.org/bots/webapps).

## Pocket Option postbacks

- Pocket Partners documents affiliate-link parameters and postback macros. The
  application adds its internal `click_id` to the configured partner link and
  uses the same value to match later events.
- The receiver accepts `sale` as a first deposit and `resale` as a repeat
  deposit alongside the canonical `fd` and `rd` values.
- The implementation records every raw postback before processing it, stores
  normalized fields alongside valid payloads, and records unsupported payloads
  as rejected with their reason. It retries valid events that arrive before
  their broker registration. A duplicate event is identified by the provider
  event ID when supplied; otherwise a fingerprint of its complete payload is
  used.

### Canonical receiver contract

Configure the Pocket Option postback URL to send these names whenever its
account exposes matching macros:

```text
https://<api-host>/api/integrations/pocket-option/events?token=<secret>
  &event=registration|fd|rd|withdrawal
  &click_id=<provider-click-id>
  &trader_id=<provider-trader-id>
  &amount=<usd-amount>
  &event_id=<stable-provider-event-id>
  &withdrawal_id=<stable-withdrawal-reference>
  &status=pending|canceled|success
  &occurred_at=<ISO-8601-or-Unix-time>
  &currency=usd
```

`click_id` is required for registrations; `trader_id` and `amount` are
required for FD/RD; withdrawals additionally require `event_id` (or a stable
`withdrawal_id`) and `status`.
The receiver also supports the commonly documented aliases `clickid`,
`playerid`, `sum`, `sumdep`, `revenue`, `tid`, and `transaction_id` to make
the handover safer. It rejects a non-USD currency rather than calculating PAC
with an unknown exchange rate.

The final Pocket Option account must still confirm its macro names, signature
mechanism, registration-link parameter, and withdrawal-status values before
the webhook secret is configured for production.

Sources: [Pocket Partners: affiliate-link anatomy](https://playbook.affpartners.io/en/affiliate/lessons/affiliate-link-anatomy/), [Pocket Partners: postback setup](https://playbook.affpartners.io/en/affiliate/lessons/postback-setup/).
