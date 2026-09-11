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
  attribution.
- The exact Pocket Option event list, unique event identifier, withdrawal
  statuses, request signature, and registration-link parameter are not public
  contracts in this repository. They remain required go-live inputs.

Source: [Chatterfy Pocket Option postbacks](https://help.chatterfy.ai/tracker/funkcional-tracker/pocket-option-postbacks).
