#!/bin/bash

export PYTHONPATH=/app/src

# Run Migrations
echo "Running Migrations..."
uv run alembic upgrade head

# Start bot in polling mode
echo "Starting bot..."
uv run python -m main
