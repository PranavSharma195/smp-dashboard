"""Django settings for SMP Dashboard (Nepal Product Intelligence)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv():
    """Tiny .env loader (no dependency). Real environment variables win."""
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


_load_dotenv()

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "dev-only-insecure-key-change-before-deploying"
)
ON_VERCEL = bool(os.environ.get("VERCEL"))
DEBUG = os.environ.get("DJANGO_DEBUG", "0" if ON_VERCEL else "1") == "1"
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost,testserver").split(",")
    if h.strip()
]
if ON_VERCEL:
    ALLOWED_HOSTS += [".vercel.app"]
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]
if ON_VERCEL:
    CSRF_TRUSTED_ORIGINS += ["https://*.vercel.app"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.accounts",
    "apps.catalog",
    "apps.research",
    "apps.finance",
    "apps.watchlist",
    "apps.dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if ON_VERCEL:
    # Serverless: no writable project dir, so serve static files with WhiteNoise.
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.dashboard.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        # Vercel's filesystem is read-only except /tmp, and /tmp is NOT persistent.
        "NAME": "/tmp/db.sqlite3" if ON_VERCEL else BASE_DIR / "db.sqlite3",
    }
}
if ON_VERCEL:
    # Instances don't share a database, so keep sessions in a signed cookie.
    SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kathmandu"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = Path("/tmp/staticfiles") if ON_VERCEL else BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:overview"
LOGOUT_REDIRECT_URL = "accounts:login"

# ---------------------------------------------------------------------------
# SMP Dashboard configuration
# ---------------------------------------------------------------------------
SMP_SITE_NAME = "SMP Dashboard"
SMP_SITE_TAGLINE = "Nepal Product Intelligence"

# Illustrative exchange rate (CNY -> NPR). Not a live rate. Change in .env.
SMP_FX_CNY_TO_NPR = os.environ.get("SMP_FX_CNY_TO_NPR", "18.5")
SMP_FX_IS_LIVE = False
# Illustrative default duty/tax percentage applied to new products. Not verified.
SMP_DEFAULT_DUTY_PCT = os.environ.get("SMP_DEFAULT_DUTY_PCT", "15")

# Budget slider bounds (NPR).
SMP_BUDGET_MIN = 0
SMP_BUDGET_MAX = 100_000
SMP_BUDGET_STEP = 500

# Viability score weights (normalised automatically). See apps/research/scoring.py
SMP_SCORE_WEIGHTS = {
    "demand": 0.22,
    "margin": 0.22,
    "investment": 0.14,
    "competition": 0.14,
    "moq": 0.08,
    "complexity": 0.10,
    "confidence": 0.10,
}

# Demo account; created by `manage.py ensure_demo_user`. CHANGE BEFORE DEPLOYING.
# Only a Django-format PBKDF2 hash is stored in code (no plaintext password).
# Set SMP_DEMO_PASSWORD in the environment to use a different password instead.
SMP_DEMO_USERNAME = os.environ.get("SMP_DEMO_USERNAME", "manab")
SMP_DEMO_PASSWORD = os.environ.get("SMP_DEMO_PASSWORD")  # optional, env only
SMP_DEMO_PASSWORD_HASH = "pbkdf2_sha256$1000000$djjjyYOzi4SOFZKW$PmW9yvws17Tpl/0kYNCFtzFVZgmrVxviIruT72dbCS4="

COMPARE_MAX_ITEMS = 4
