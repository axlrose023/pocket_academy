# Pocket Academy

Pocket Academy is a Telegram Mini App with a Python API, a Telegram bot entry
point, and background-worker infrastructure.

## Foundation

- `src/api`: HTTP API for the Mini App and future external event receivers.
- `src/handlers`: Telegram Bot API transport.
- `src/services`: business use cases (added with the product rules).
- `src/domain`: framework-independent rules and value objects.
- `src/database`: SQLAlchemy models, DAOs, migrations, and unit of work.

The HTTP API and bot polling run as separate processes. Importing the API never
creates a Telegram client or requires a bot token.

## Local setup

```bash
cp .env.dist .env
uv sync --frozen
PYTHONPATH=src uv run uvicorn api.app:app --reload
```

The unauthenticated health endpoint is available at `GET /api/health`.

The Mini App shell is at `/app/`; the separate administration surface is at
`/admin/`. Production provider and storage setup is described in
[`docs/OPERATIONS.md`](docs/OPERATIONS.md).

Do not commit production tokens, database passwords, provider secrets, or a
real `.env` file.
