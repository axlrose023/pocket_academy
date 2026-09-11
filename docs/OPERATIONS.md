# Operations checklist

## Before provider integration

1. Set a real `BOT_BOT__TOKEN`, HTTPS `BOT_API__PUBLIC_BASE_URL`, and
   `BOT_BOT__WEBAPP_URL`.
2. Generate distinct long random values for the Chatterfy and Pocket Option
   webhook secrets. Do not reuse the Telegram token.
3. Configure Chatterfy to call `/api/integrations/chatterfy/leads?token=...`.
   The standard Chatterfy Flow Webhook does not support custom headers.
4. Confirm the Pocket Option postback field mapping, signature method, unique
   event ID, trader ID, amount, timestamp, and withdrawal status values before
   enabling its endpoint.
5. Run controlled test events for registration, FD, RD, withdrawal, cancelled
   withdrawal, duplicate delivery, and reordered delivery.

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
