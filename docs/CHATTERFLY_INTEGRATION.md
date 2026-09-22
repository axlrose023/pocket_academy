# Chatterfly integration

Pocket Academy accepts the initial lead and relayed Pocket Partners events at
one authenticated endpoint:

```text
GET|POST https://<academy-host>/api/integrations/chatterfly/events
```

Authenticate with `X-Webhook-Secret: <secret>` or, when Chatterfly can only
configure a URL, append `?token=<secret>`. Never send the Telegram bot token.

The endpoint returns the following JSON for an accepted request:

```json
{"accepted": true, "duplicate": false}
```

Repeated requests are safe. Events received before the matching lead or
registration remain pending and are retried after the missing link arrives.

## Lead before the welcome message

Use a constant `event=lead` and substitute the Chatterfly variables for the
other values:

```text
https://<academy-host>/api/integrations/chatterfly/events?token=<secret>
  &event=lead
  &telegram_id=<Telegram-chat-ID-variable>
  &click_id={{tracker.clickid}}
  &username=<Telegram-username-variable>
  &chatterfly_id=<internal-Chatterfly-chat-ID-variable>
  &occurred_at=<created-at-variable>
```

Only `telegram_id` and `click_id` are required. Pocket Academy creates the
user if needed, stores the attribution, and reuses that click ID in the
registration link shown inside the Mini App.

## Events relayed after Pocket Partners postbacks

Configure Chatterfly to call the same endpoint when its tracker receives these
events. The value on the left is the field Pocket Academy expects; the value
on the right is the Chatterfly variable populated by the Pocket Partners
postback.

| Chatterfly event | Constant `event` | Required values |
| --- | --- | --- |
| Registration | `registration` | `click_id`, `trader_id`, `occurred_at` |
| First deposit | `ftd` or `sale` | `trader_id`, `amount`, `occurred_at` |
| Re-deposit | `rd` or `resale` | `trader_id`, `amount`, `occurred_at` |
| Withdrawal | `withdrawal` | `trader_id`, `amount`, `status`, `occurred_at` |

Pocket Academy also accepts the Pocket Partners field names `clickid`,
`tracker.clickid`, `sumdep`, `wdr_sum`, `event_at`, and `date_time`. Withdrawal
statuses can be `pending`, `canceled`/`cancelled`, or `success`; the aliases
`new`, `rejected`, `approved`, `completed`, and `paid` are accepted too.

Send a stable `event_id`, `transaction_id`, or `withdrawal_id` when Chatterfly
exposes one. If Pocket Partners does not expose a withdrawal ID, Pocket Academy
derives a repeat-safe reference from the trader, amount, and event timestamp.

## Registration link

Set `BOT_INTEGRATIONS__POCKET_OPTION_REGISTRATION_URL` to the final Pocket
Partners URL without a templated `click_id`. Pocket Academy adds the stored
click ID using `BOT_INTEGRATIONS__POCKET_OPTION_CLICK_ID_PARAMETER=click_id`.

The Chatterfly message may use its own link template ending in:

```text
click_id={{tracker.clickid}}
```

Both links must carry exactly the same resolved click ID.

## Handover test

Use one new test user and send events in this order: lead, registration, FTD,
RD, and successful withdrawal. Repeat the FTD request once to confirm that PAC
is not credited twice. Then send an RD before registration for a second test
click and confirm it is processed after registration arrives.
