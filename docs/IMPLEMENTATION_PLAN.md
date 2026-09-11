# Pocket Academy — implementation plan

Status: planning only. No application code, migration, or deployment configuration
is changed by this document.

## Confirmed scope

- Telegram WebApp with Home, Signals, Academy, and Profile pages;
- separate web admin interface;
- Telegram bot is an entry point and may deliver Telegram messages;
- PostgreSQL, Redis, Docker, Alembic, and Python backend inherit from the
  template;
- Chatterfy sends `tg_id`, `click_id`, and `link_chat` to our API;
- Pocket Option sends registration, FD, RD, and withdrawal postbacks;
- content storage will use S3-compatible storage in a later phase;
- infrastructure credentials, domain, and webhook URLs will be supplied later.

## Delivery order

1. **Foundation**
   - Rename template metadata and introduce backend/API, WebApp, and admin app
     boundaries.
   - Define shared configuration, UTC time policy, error handling, API auth,
     logging, health check, and local Docker development setup.

2. **Domain and persistence**
   - Model users, attribution clicks, external events, deposits, withdrawals,
     PAC ledger, statuses, signals, products/access, notifications, diary
     entries, and audit records.
   - Create the initial Alembic migration and repository/service boundaries.
   - Make every external event idempotent: retain its raw payload, external
     identifier or deterministic fallback fingerprint, received time, and
     processing result.

3. **Integration adapters**
   - Add a protected Chatterfy lead endpoint.
   - Add a protected Pocket Option postback endpoint and map registration, FD,
     RD, and withdrawal events to the domain services.
   - Keep provider field names and link construction configurable, not spread
     through business logic.
   - Test duplicate delivery, delayed events, and out-of-order events.

4. **Core product rules**
   - Calculate PAC, deposit totals, user status/progress, permitted timeframes,
     signal daily limits, waits, and premium-signal limits.
   - Implement transparent access state calculation for withdrawals and manual
     administrative block/unblock.
   - Implement product granting, PAC purchase, and notification creation.

5. **User experience**
   - Build and validate the Telegram WebApp shell, Telegram `initData`
     validation, navigation, loading/error states, and blocked-access screen.
   - Deliver Home, Signals, Academy, and Profile in that order.
   - Add diary editing for the current UTC day, reward rule, notification
     centre, and responsive dark Pocket-Option-inspired visual system.

6. **Admin interface**
   - User lookup and review, manual access controls, products CRUD, and
     configurable pairs/premium parameters.
   - Add deposits/registrations/signals/diary dashboards and conversion
     metrics, including date filters.

7. **Content and operations**
   - Add S3-compatible content upload/delivery when storage details are
     available.
   - Configure production domain, HTTPS, secrets, Telegram webhook, and
     provider webhook URLs.
   - Add monitoring, backup/restore procedure, rate limiting, release checks,
     and automated tests for critical rules.

## External decisions still required before provider go-live

- Exact Pocket Option affiliate-link parameter for `click_id`, postback field
  names, unique event identifier, signature/authentication method, and all
  withdrawal-status values.
- The Chatterfy-supported way to issue a genuinely new `click_id` for the
  re-registration journey. A normal outgoing Chatterfy Webhook cannot set
  custom HTTP headers, so its secret must be passed by an approved supported
  mechanism until that capability is confirmed.
- Final S3 provider/bucket, media size limits, and access model.
- Production credentials and hostnames.

## Verification gates

- Unit tests for status/PAC/limits/withdrawal/diary rules.
- API contract tests for Telegram, Chatterfy, and Pocket Option adapters.
- Migration test against PostgreSQL and end-to-end WebApp smoke tests.
- A test registration, FD, RD, withdrawal, cancellation, and duplicate-event
  sequence in each provider's sandbox or controlled production test setup.
