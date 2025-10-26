# Environment configuration (.env)

This project now uses Pydantic-based settings with dotenv support. Real environment variables always win; values from `.env` files are used as convenient defaults for local development.

Layered precedence (lowest to highest among files):
- `.env`
- `.env.dev`
- `.env.{APP_ENV}` (e.g., `.env.development`, `.env.staging`, `.env.production`)
- `.env.local`
- `.env.{APP_ENV}.local`

Real OS environment variables override any file values.

## Quick start

1) Install dependencies
- Using uv (recommended): `uv pip install -r pyproject.toml` or `uv sync`
- Using pip: `pip install -e .` or `pip install -r requirements` (see `pyproject.toml` deps)

2) Create your env file
- Copy `.env.example` to `.env` and adjust values for your machine.
- Or use the provided `.env.dev` for a shared development baseline (auth enabled by default). Set `APP_ENV=dev` or `APP_ENV=development` to load it.
- You can also set `APP_ENV=development|staging|production` to switch stacks. Real env vars still take precedence.

3) Run the app (development)
- Windows PowerShell:
  - `python app.py`
- macOS/Linux:
  - `python app.py`

The server binds to port from `PORT` (default 8050).

## JWT auth quick test

1) Ensure in `.env`:
```
DISABLE_AUTH=0
JWT_SECRET=change-me-strong
```

2) Generate a token:
```
python - << 'PY'
import jwt, time
print(jwt.encode({"sub":"cio@corp","name":"CIO","role":"CIO","exp":int(time.time())+3600}, "change-me-strong", algorithm="HS256"))
PY
```

3) Call the app:
```
curl -H "Authorization: Bearer <token>" http://localhost:8050
```

Tip: In development you can bypass auth with `DISABLE_AUTH=1` in `.env`.

## Selecting a data source

Set in `.env`:
- `DATA_SOURCE=SYNTHETIC` (default)
- `DATA_SOURCE=REST` with `API_BASE_URL=https://api.example.com`
- `DATA_SOURCE=SQL` with `DB_URL=postgresql+psycopg2://user:pass@host/db`

Limit rows with `MAX_ROWS`.

## Caching

- Default: `CACHE_TYPE=SimpleCache`
- Production: `CACHE_TYPE=RedisCache` and set `REDIS_URL=redis://host:6379/0`
- Configure TTL with `CACHE_TIMEOUT_SECONDS` (default one day)

## Running in production

Provide environment via your process manager (systemd, Docker, Heroku, etc.) or mount an appropriate `.env` file. Example gunicorn command:
```
gunicorn app:server \
  -k uvicorn_worker.UvicornWorker \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --timeout 60 --graceful-timeout 30 \
  --keep-alive 5 \
  --forwarded-allow-ips="10.0.0.0/8,127.0.0.1" \
  --access-logfile - --error-logfile -
```

Security notes:
- Never commit real secrets. `.env` files are git-ignored; use `.env.example` as a template.
- In production, keep `DISABLE_AUTH=0` and set a strong `JWT_SECRET`.