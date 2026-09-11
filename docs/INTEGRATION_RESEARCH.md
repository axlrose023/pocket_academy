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

## Chatterfy

- An outgoing Flow Webhook supports GET or POST and can substitute `{chatId}`,
  `{username}`, `{createdAt}`, and `{tracker.clickid}` into a request.
- Its template syntax uses single braces (`{var}`), unlike the double-brace
  syntax used elsewhere in Chatterfy.
- The standard Flow Webhook does not provide custom HTTP-header settings and
  does not retry a failed request. The receiving endpoint therefore needs an
  approved supported secret mechanism and must acknowledge accepted payloads
  promptly.

Source: [Chatterfy outgoing Webhook](https://docs.chatterfy.ai/en/crm/tracking/webhook).

## Pocket Option postbacks

- Chatterfy's Pocket Option setup guide confirms separate provider postbacks
  are configured for events and that a `click_id` parameter can be used for
  attribution. Its event examples include `registration` and `resale`.
- Chatterfy's Custom Postback reference identifies `sale` as a first deposit
  and `resale` as a repeat deposit. The receiver accepts these aliases along
  with the canonical `fd` and `rd` values.
- The implementation records every accepted raw postback before processing it,
  stores its normalized fields alongside the original payload, and retries
  events that arrive before their Chatterfy attribution or broker registration.
  A duplicate event is identified by the provider event ID when supplied;
  otherwise a fingerprint of its complete payload is used.

### Canonical receiver contract

Configure the Pocket Option (or its intermediary) postback URL to send these
names whenever its account exposes matching macros:

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

Sources: [Chatterfy Pocket Option postbacks](https://help.chatterfy.ai/tracker/funkcional-tracker/pocket-option-postbacks), [Chatterfy Custom Postback](https://docs.chatterfy.ai/en/tracker/integrations/custom-postback).
