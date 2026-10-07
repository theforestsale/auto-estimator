# AutoEstimate — AI auto-repair estimator (subscription SaaS)

Turn a customer complaint into a professional, itemized repair estimate in ~30 seconds.
Shops sign up free (3 estimates), upgrade to Pro ($19/mo) for unlimited estimates + their
own shop branding. AI runs on Groq's free tier, so cost per estimate is near zero.

```
Flask  +  Flask-Login  +  SQLite  +  Groq (openai/gpt-oss-120b)  +  reportlab (PDF)
```

## What it does

- **Estimate generation** — paste vehicle + complaint → AI returns diagnosis, itemized
  work breakdown (labor at your shop's rate, parts, shop supplies), customer message, notes.
- **Professional PDF** — branded estimate sheet with correct totals (computed server-side
  in Decimal, never trusted from the model).
- **Free plan limits** — 3 estimates, then an upgrade paywall (server-enforced).
- **Subscriptions** — checkout link + signed webhook auto-activates Pro.
- **Admin CLI** — manually upgrade/downgrade users for testing or manual activation.

## Quickstart (local)

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env   # then edit: GROQ_API_KEY, SECRET_KEY, shop details
.\venv\Scripts\python.exe -m flask run
```

Open http://127.0.0.1:5000, sign up, create an estimate, download the PDF.

Get a free Groq API key (no credit card): https://console.groq.com/keys

### Env vars (see `.env.example`)

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | Groq key (free tier). Without it the app warns on generate. |
| `AI_MODEL` | Default `openai/gpt-oss-120b`. Swap for any Groq model. |
| `SECRET_KEY` | Random: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `SHOP_NAME/PHONE/ADDRESS/EMAIL` | Branding shown on the PDF header. |
| `DEFAULT_LABOR_RATE`, `DEFAULT_TAX_RATE` | Pre-filled in the form. |
| `FREE_PLAN_QUOTA` | Free-plan estimate limit (default 3). |
| `PRO_CHECKOUT_URL` | Upgrade button target (your payment checkout link). |
| `WEBHOOK_SECRET` | Shared secret that verifies billing webhooks (HMAC-SHA256). |
| `CSRF_ENABLED` | 1 = CSRF tokens enforced on all state-changing forms (default 1). Webhook exempt. |
| `RATE_LIMIT_ENABLED` | 1 = per-IP sliding-window limits on auth + estimate generation (default 1). |
| `RATE_LIMIT_GENERATE` | Max estimate generations / min / IP (default 10). |
| `RATE_LIMIT_AUTH` | Max login+signup attempts / min / IP (default 30). |
| `ADMIN_KEY` | Passphrase for the `/admin` activation page. Empty = page hidden (404). |

## Running a live demo (real Groq call)

```powershell
.\venv\Scripts\python.exe smoke_live.py
```

Signs up a demo user, generates a real estimate through the full route stack, renders the
PDF, and fires a signed webhook that upgrades the user to Pro.

## Tests

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

32 tests: auth, quota enforcement, ownership, AI JSON parsing, server-side totals, PDF
render, webhook signing/dedup, CSRF rejection/acceptance, and per-IP rate limiting.

## Payments (how to actually get paid)

Pick one path — **Lite** is the one to start with.

### LITE PATH (no webhooks, 3 steps, ~5 minutes)
This is the fastest way to take money. No webhook config, no signature secrets, no
email matching.

1. Create a free **Lemon Squeezy** account (merchant of record — no company, no VAT work).
2. **Products → New product** → name `AutoEstimate Pro`, price `$19.00` **Monthly
   subscription**. Save → copy the **Checkout URL** into `PRO_CHECKOUT_URL=` in `.env`.
3. Put a random passphrase in `ADMIN_KEY=` in `.env` and restart.

Now the flow is: customer clicks your checkout link → pays → you open
`https://<domain>/admin`, unlock with the passphrase, type their signup email, click
Pro. Done. Their account is live immediately.

The webhook engine is still there for later — when you install it, activation becomes
fully automatic and you can ignore the admin page.

### FULLY AUTOMATIC PATH (webhooks)
1. Set `PRO_CHECKOUT_URL` to a Lemon Squeezy or Stripe checkout/customer portal URL.
2. Add a webhook at `https://<your-domain>/billing/webhook` (Lemon Squeezy events
   `order_created`/`subscription_created`, or Stripe `checkout.session.completed`).
3. Set the provider's signing secret as `WEBHOOK_SECRET=` (Lemon Squeezy "Signing
   secret"; Stripe signature header is verified too).
4. Require customers to use their **signup email** at checkout — the webhook matches
   them by email and flips them to Pro automatically.

### Testing activation without a provider
```powershell
.\venv\Scripts\python.exe -m flask upgrade-user customer@example.com
.\venv\Scripts\python.exe -m flask downgrade-user customer@example.com
```

## Common admin routes

| Method | Path | Notes |
|---|---|---|
| GET | `/` | Landing + pricing |
| GET/POST | `/signup`, `/login` | Auth (werkzeug password hashing) |
| GET | `/dashboard` | Estimate list + plan usage |
| POST | `/estimates` | Generate (quota checked server-side) |
| GET | `/estimates/<id>` | Full estimate view |
| GET | `/estimates/<id>/pdf` | Download professional PDF |
| GET/POST | `/billing/webhook` | Payment webhook (HMAC verified, idempotent) |
| GET | `/api/health` | Health check |

## Deploying

The app is a standard WSGI Flask app. Any host works:

- **Railway / Render / Fly.io** — add a `web` service with start command
  `waitress-serve --host 0.0.0.0 --port $PORT app:app` (install `waitress`),
  or use the platform's Python buildpack.
- **pythonanywhere.com** — upload, create a venv, wire `/billing/webhook` etc.

Set the same env vars in production. SQLite is fine for your first ~100 users; move to
Postgres (flip `SQLALCHEMY_DATABASE_URI`) when you need headroom.

## Notes / security

- Totals are always recomputed server-side; the model's arithmetic is ignored.
- CSRF tokens are enforced on every state-changing form; the billing webhook is exempt
  (it authenticates via the shared-secret HMAC signature instead).
- Basic per-IP rate limiting protects auth and estimate generation (in-process; for
  multi-worker deployments move to Redis or a reverse-proxy limiter).
- If `WEBHOOK_SECRET` is unset the webhook is accepted unverified (dev convenience only).