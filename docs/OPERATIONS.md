# Operations checklist

## Before provider integration

1. Set a real `BOT_BOT__TOKEN`, HTTPS `BOT_API__PUBLIC_BASE_URL`, and
   `BOT_BOT__WEBAPP_URL`.
2. Set `BOT_ADMIN__TELEGRAM_IDS` to the JSON array of initial administrator
   Telegram IDs, for example `[123456789]`.
3. Generate distinct long random values for the Chatterfy and Pocket Option
   webhook secrets. Do not reuse the Telegram token.
4. Configure Chatterfy to call `/api/integrations/chatterfy/leads?token=...`.
   The standard Chatterfy Flow Webhook does not support custom headers.
5. Confirm the Pocket Option postback field mapping, signature method, unique
   event ID, trader ID, amount, timestamp, and withdrawal status values before
   enabling its endpoint.
6. Run controlled test events for registration, FD, RD, withdrawal, cancelled
   withdrawal, duplicate delivery, and reordered delivery.

The initial migration supplies EUR/USD, GBP/USD, USD/JPY, EUR/CHF, and their
OTC variants. Review and maintain this list in the admin interface before the
first release.

## S3-compatible content storage

Product materials use `storage_key` already. Enable object storage only when
the endpoint, bucket, credentials, region, media limits, and access model are
chosen. The application must issue short-lived authorized download URLs rather
than storing public bucket URLs in products.

## Release checks

- Apply Alembic migrations once through the `migrate` service.
- Keep PostgreSQL backups encrypted and test a restore before launch.
- Restrict database/Redis to the private network; expose only the HTTPS reverse
  proxy.
- Keep `.env` outside Git and rotate any token that was exposed.
- Monitor non-2xx webhook responses, rejected events, and duplicate-event
  volume.
- Redis/KeyDB also applies a fixed 60-second window to Telegram WebApp and
  webhook traffic. Defaults are 120 authenticated WebApp requests and 60
  webhook requests per credential per window; set the `BOT_RATE_LIMIT__*`
  values only when provider traffic requires it.

## Scheduled operations

`taskiq-worker` executes the queued tasks and `taskiq-scheduler` enqueues two
UTC schedules. Keep both services running:

- every 10 minutes, received Pocket Option events are retried in chronological
  order (up to 100 events per run), allowing a delayed Chatterfy attribution or
  registration to unblock an earlier event;
- at 18:00 UTC, users who have opened Pocket Academy but have not completed
  today's diary receive one in-app diary reminder. The database unique key
  makes repeated scheduler runs safe.

The scheduler starts with `--skip-first-run` so a deploy does not execute a
scheduled operation immediately. It does not send direct Telegram messages;
the WebApp notification centre is the defined delivery channel.
