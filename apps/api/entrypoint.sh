#!/bin/bash
set -e

echo "Starting MyElectricalData API..."

# Run database migrations
echo "Applying database migrations..."
alembic upgrade head
echo "Migrations applied successfully"

# Start the application
# If arguments are passed (from docker-compose command), use them
# Otherwise use default (production) settings
echo "Starting uvicorn server..."
if [ $# -gt 0 ]; then
    echo "Using custom command: $@"
    exec "$@"
else
    echo "Using default production settings"
    exec uvicorn src.main:app --host 0.0.0.0 --port 8000
fi
