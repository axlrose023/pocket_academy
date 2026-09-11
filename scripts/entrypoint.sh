#!/bin/bash

export PYTHONPATH=/app/src

# Run Migrations
echo "Running migrations..."
uv run --no-sync alembic upgrade head

# Start bot in polling mode
echo "Starting bot..."
exec uv run --no-sync python -m main
