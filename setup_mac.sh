#!/usr/bin/env bash
# One-time setup for macOS / Linux. Usage: bash setup_mac.sh
# Creates a project-local virtualenv, installs dependencies, migrates, creates the
# demo login, seeds sample products, runs checks and the test suite. No sudo needed.
set -euo pipefail
cd "$(dirname "$0")"

say()  { printf "\n\033[1;32m==>\033[0m %s\n" "$1"; }
fail() { printf "\n\033[1;31mSetup stopped:\033[0m %s\n" "$1" >&2; exit 1; }
trap 'fail "a step failed (see the message above). Fix it and re-run: bash setup_mac.sh"' ERR

say "1/9 Looking for a compatible Python (3.10 - 3.13)"
PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,13) else 1)' 2>/dev/null; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  fail "No Python 3.10-3.13 found. Install Python 3.12 from https://www.python.org/downloads/ (or 'brew install python@3.12') and run this again."
fi
echo "Using $($PY --version) at $(command -v $PY)"

say "2/9 Creating virtual environment in ./venv"
[ -d venv ] || "$PY" -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate

say "3/9 Installing dependencies"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

say "Optional: fetching GSAP and Chart.js for offline use (skipped quietly if offline)"
mkdir -p static/vendor
[ -s static/vendor/gsap.min.js ] || curl -fsSL --max-time 20 -o static/vendor/gsap.min.js https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js 2>/dev/null || { rm -f static/vendor/gsap.min.js; echo "  (could not download gsap; the CDN or built-in animations will be used)"; }
[ -s static/vendor/chart.umd.min.js ] || curl -fsSL --max-time 20 -o static/vendor/chart.umd.min.js https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js 2>/dev/null || { rm -f static/vendor/chart.umd.min.js; echo "  (could not download chart.js; the CDN or plain bar charts will be used)"; }

say "4/9 Applying database migrations"
python manage.py migrate --noinput

say "5/9 Creating the demo login account"
python manage.py ensure_demo_user

say "6/9 Seeding sample products"
python manage.py seed_products

say "7/9 Running Django system checks"
python manage.py check

say "8/9 Running the automated test suite"
python manage.py test --verbosity 1

say "9/9 All done"
cat <<MSG

  Start the app:   bash run_mac.sh
  Open:            http://127.0.0.1:8000/
  Log in with:     manab / manab123   (demo only: change before deploying)

MSG
