#!/usr/bin/env bash
# Start the dev server. Usage: bash run_mac.sh [port]
set -euo pipefail
cd "$(dirname "$0")"
[ -d venv ] || { echo "Run 'bash setup_mac.sh' first."; exit 1; }
# shellcheck disable=SC1091
source venv/bin/activate
PORT="${1:-8000}"
echo "SMP Dashboard: http://127.0.0.1:${PORT}/   (Ctrl+C to stop)"
exec python manage.py runserver "127.0.0.1:${PORT}"
