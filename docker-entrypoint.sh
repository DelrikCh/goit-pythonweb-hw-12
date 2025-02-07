#!/bin/bash
# Wait for DB to be ready (you can adjust this for your specific needs)
echo "Waiting for PostgreSQL to be ready..."
while ! pg_isready -h db -U ${POSTGRES_USER}; do
  sleep 1
done

# Run Alembic migrations (only if not already applied)
echo "Running migrations..."
alembic upgrade head

# Start FastAPI app
exec "$@"
