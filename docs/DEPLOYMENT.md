# Deployment

A hosted deployment is **not required** by the Arthaton brief (it asks for a public repository and a demo video). This guide is for anyone who wants a public URL.

**Status:** not deployed. The Docker image has not been built or run in the test environment, which has no Docker daemon. The non-Docker path (`./run.sh`) was tested end to end.

## Single container (recommended)

The image builds the frontend and serves it from the same FastAPI process, so there is one service and no CORS setup.

```bash
docker build -t summa .
docker run -d -p 8000:8000 -v summa-data:/data \
  -e ANTHROPIC_API_KEY=... -e SUMMA_COOKIE_SECURE=true summa
```

- The SQLite file lives in the `/data` volume. Without a volume, data is lost when the container is replaced.
- Set `SUMMA_COOKIE_SECURE=true` whenever the site is served over HTTPS.
- The container reads `$PORT`, so it runs unchanged on Render, Railway, Fly.io and Google Cloud Run.

### Render or Railway

1. New Web Service from this GitHub repository, environment "Docker".
2. Add a persistent disk mounted at `/data` (or set `DATABASE_URL` to a managed Postgres; add `psycopg[binary]` to `backend/requirements.txt`).
3. Environment: `ANTHROPIC_API_KEY` (secret), `SUMMA_COOKIE_SECURE=true`.
4. Health check path: `/api/health`.

## Without Docker

```bash
cd frontend && npm ci && npm run build
cd ../backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
SUMMA_COOKIE_SECURE=true .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Put it behind a reverse proxy (Caddy, nginx) that terminates TLS.

## Production notes

- **One instance.** Rate limits are held in process memory, and SQLite suits a single writer. For several instances, move to Postgres and a shared rate-limit store.
- **Secrets** come only from environment variables. `.env` is git-ignored.
- **Start-up** trains the two small local models in about four seconds on a background thread; the first request does not wait for it unless it needs a model.
- **Logs** go to stdout. Unhandled errors are logged with a stack trace and return a generic message to the client.
- **Security headers** (CSP, X-Frame-Options, nosniff, no-referrer) are set by the app.
