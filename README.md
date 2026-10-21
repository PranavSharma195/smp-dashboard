# SMP Dashboard — Nepal Product Intelligence

A Django web app that helps entrepreneurs in Nepal research products to resell, estimate what it costs to
import the **minimum order** from China (shipping, duty, other costs), and compare likely gross profit.
It is a research tool, not a shop.

> **Sample data only.** All 42 bundled products carry *illustrative estimates* so the app works offline.
> They are **not** live supplier quotes, customs rates or Nepalese marketplace prices, and nothing here
> proves a product is "trending". Exchange rate and duty rates are configurable estimates. Gross profit is
> **not** net profit (ads, fees, storage, returns, delivery and staff costs come off it).

> **Security warning.** The demo login is `manab` / `manab123`. It is for local use only.
> **Change or remove it before any deployment** (see "Deploy to Vercel").

---

## 1. Run it on your Mac (Apple Silicon or Intel)

```bash
# 1. Unzip, then open Terminal in the folder
cd nepal_product_intelligence

# 2. One-time setup (creates ./venv, installs, migrates, seeds, runs checks + tests)
bash setup_mac.sh

# 3. Start the server
bash run_mac.sh
```

Open **http://127.0.0.1:8000/** and sign in with `manab` / `manab123`.
Needs Python 3.10–3.13 (`brew install python@3.12` if missing). No Docker, Node, Postgres or paid APIs.

### Windows
```bat
setup_windows.bat
run_windows.bat
```
Or by hand:
```bat
py -3 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py ensure_demo_user
python manage.py seed_products
python manage.py test
python manage.py runserver
```

### Manual commands (any OS)
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py ensure_demo_user      # creates manab (hashed password)
python manage.py update_fx              # optional: fetch live CNY→NPR rate (needs internet)
python manage.py seed_products         # safe to re-run; add --refresh to reset sample rows
python manage.py check
python manage.py test
python manage.py runserver
```

Django Admin (add/edit products, prices, MOQs, import estimates, trend scores, data sources, verified flags):
**http://127.0.0.1:8000/admin/** (same login).

---

## 2. Commit to Git and push to GitHub

```bash
cd nepal_product_intelligence
git init -b main
git add .
git status                 # confirm venv/, db.sqlite3 and .env are NOT listed (.gitignore covers them)
git commit -m "Initial commit: SMP Dashboard"

# Create an empty repo on github.com (no README/license), then:
git remote add origin https://github.com/<your-username>/smp-dashboard.git
git push -u origin main
```
Never commit `.env`, `db.sqlite3` or real passwords. Use a **private** repo if you add real supplier data.

---

## 3. Deploy to Vercel (demo-grade) — read the limits first

This project includes `vercel.json` and `api/index.py` so it can run on Vercel's Python runtime.

**Important limits (Vercel is serverless):**
- The filesystem is read-only except `/tmp`, which is **not persistent**. On each cold start the app builds a
  fresh SQLite DB in `/tmp`, seeds the sample products and creates the login. **Watchlists, comparison picks
  saved to the DB, saved filters, password changes and admin edits are lost when the instance recycles.**
- That makes it fine for a **demo/preview**, not for real use. For real use, switch `DATABASES` to a hosted
  Postgres (Neon, Supabase, Vercel Postgres) and install `psycopg[binary]`, and run `migrate` against it.
- Sessions use signed cookies on Vercel (instances don't share a database).
- This Vercel setup was written but **not deployed or tested** by the author. Expect to iterate on it.

**Steps**
1. Push the repo to GitHub (section 2).
2. Go to vercel.com → **Add New → Project** → import the repo. Framework preset: **Other**. Leave build/output empty.
3. Add **Environment Variables** (Project → Settings → Environment Variables):

| Name | Value |
|---|---|
| `DJANGO_SECRET_KEY` | a long random string (`python -c "import secrets; print(secrets.token_urlsafe(50))"`) |
| `DJANGO_DEBUG` | `0` |
| `SMP_DEMO_USERNAME` | your chosen username |
| `SMP_DEMO_PASSWORD` | a **strong, new** password (the login is only created if this is set) |
| `DJANGO_ALLOWED_HOSTS` | your custom domain(s), comma-separated (`*.vercel.app` is allowed automatically) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://your-domain.com` (only for custom domains) |

4. Click **Deploy**. Open the URL and sign in with the username/password you set. The public demo
   credentials `manab`/`manab123` are **not** used on Vercel unless you set them yourself — don't.
5. Redeploys happen automatically on every `git push`.

CLI alternative: `npm i -g vercel && vercel` then `vercel --prod`.

**Troubleshooting:** 500 on first load → check the function logs in Vercel (usually a missing env var or a
dependency that failed to install). CSRF failure on login → add your domain to `DJANGO_CSRF_TRUSTED_ORIGINS`.
Unstyled pages → static files are collected at cold start; check logs for `collectstatic` errors.

---

## 4. What's inside

| Area | Where |
|---|---|
| Overview dashboard, budget slider, charts | `apps/dashboard`, `static/js/charts.js`, `dashboard.js` |
| Product catalogue, filters, sorting, detail pages | `apps/catalog` |
| Viability scoring (configurable weights) | `apps/research/scoring.py` |
| Import cost maths (Decimal, no Django deps) | `apps/finance/calculations.py` |
| Watchlist and comparison (max 4) | `apps/watchlist` |
| Login, settings, demo user command | `apps/accounts` |
| Data-source adapters | `apps/research/adapters` |
| Sample dataset | `apps/catalog/seed_data.py` |

**Budget semantics:** the budget slider (Rs. 0–1,00,000) filters on the **total landed cost of the minimum order**
(product + shipping + duty + other). A separate "cost per unit" filter exists. Cheap unit price with a huge MOQ
will not pass a small total budget.

**Formulas:** purchase = CNY price × rate × MOQ; duties = (purchase + shipping + insurance) × duty %;
landed = purchase + shipping + insurance + duties + other; per unit = landed ÷ MOQ;
profit/unit = selling price − per unit; margin = profit/unit ÷ selling price.

**Viability score (0–100)** — weighted sum of demand, margin, investment, competition, MOQ affordability,
import complexity and data confidence (defaults 22/22/14/14/8/10/10 %). Edit `SMP_SCORE_WEIGHTS` in
`config/settings.py`. It is an **indicative research score**, not a prediction or guarantee.

### Configuration (`.env`, optional — copy `.env.example`)
`SMP_FX_CNY_TO_NPR` (illustrative rate), `SMP_DEFAULT_DUTY_PCT`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`,
`DJANGO_ALLOWED_HOSTS`, `SMP_DEMO_USERNAME`, `SMP_DEMO_PASSWORD`.
Per-product exchange-rate override and duty rate are editable in Admin.

### Using real data later
Replace sample values in Admin, or import researched values from a CSV you maintain:
```bash
python manage.py sync_sources --list
python manage.py sync_sources --adapter csv --file my_observations.csv
```
CSV columns: `product_name,field,value,source,verified` (verified = yes/no). Imported rows record their source,
time and verified flag, and are no longer marked "sample". Adapters for supplier listings, Nepalese ecommerce
prices and search interest are stubs: implement them only against official APIs or licensed feeds whose terms
permit it. Do not scrape sites that forbid it or bypass access controls.

### Product images
Products show a generated illustration by default. Upload real photos in Admin (stored in `media/`).

### Offline behaviour
GSAP and Chart.js are downloaded into `static/vendor/` by the setup script when online. If unavailable, the page
tries a CDN, then falls back to built-in animations and plain bar charts. Login, filters and calculators never
depend on them.

## Known limitations
- All figures are illustrative; no live supplier, customs, exchange-rate or trend data.
- Customs/duty are a single user-set percentage, not Nepal's actual tariff schedule.
- Vercel deployment is non-persistent (see above).
- Development server only; for production use a proper WSGI server, HTTPS and a real database.
