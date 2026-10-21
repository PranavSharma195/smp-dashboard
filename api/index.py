"""Vercel serverless entry point (demo deployment only).

Vercel's filesystem is read-only apart from /tmp, which is wiped between
instances. So on each cold start this builds a throw-away SQLite database in
/tmp, seeds the sample products, and (only if SMP_DEMO_PASSWORD is set) creates
the login account. Anything users save (watchlists, password changes) is lost
when the instance recycles. Use a hosted database for real use; see README.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402
from django.core.management import call_command  # noqa: E402

django.setup()
call_command("migrate", interactive=False, verbosity=0)
call_command("collectstatic", interactive=False, verbosity=0)
call_command("seed_products", verbosity=0)

if os.environ.get("SMP_DEMO_PASSWORD"):
    call_command("ensure_demo_user", verbosity=0)

from django.core.wsgi import get_wsgi_application  # noqa: E402

app = application = get_wsgi_application()
