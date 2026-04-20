#!/bin/sh
set -eu

HOST="${1:-postgres}"
PORT="${2:-5432}"

until pg_isready -h "$HOST" -p "$PORT" >/dev/null 2>&1; do
  echo "{\"event\":\"waiting_for_postgres\",\"host\":\"$HOST\",\"port\":\"$PORT\"}"
  sleep 2
done

echo "{\"event\":\"postgres_ready\",\"host\":\"$HOST\",\"port\":\"$PORT\"}"

