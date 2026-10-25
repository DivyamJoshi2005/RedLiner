#!/bin/bash
# RedLiner - Start Server Script
cd "$(dirname "$0")"

echo "=================================================="
echo " Starting RedLiner B2B Contract Negotiation Server"
echo " Dashboard URL: http://127.0.0.1:8000"
echo " Health API:    http://127.0.0.1:8000/api/health"
echo "=================================================="

PYTHONPATH=. .venv/bin/uvicorn server.app:app --host 127.0.0.1 --port 8000 --reload
