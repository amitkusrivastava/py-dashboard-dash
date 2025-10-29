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
```bash
uv run start
```

The server binds to port from `PORT` (default 8050).

Alternatively, you can run directly with:
```bash
python app.py
```

## Available Commands

This project uses `uv run` for task management (similar to `npm run`). Available commands:

| Command | Description |
|---------|-------------|
| `uv run start` | Start the development server |
| `uv run test` | Run unit tests (fast, skips E2E) |
| `uv run test-all` | Run full test suite including E2E tests |
| `uv run cov` | Generate coverage report for unit tests |
| `uv run cov-all` | Generate coverage report for all tests |
| `uv run cov-html` | Generate HTML coverage report |

**Examples:**
```bash
# Start the app
uv run start

# Run tests with coverage
uv run cov

# Generate HTML coverage report
uv run cov-html
```

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

## Testing and Coverage

### Setup
Install test dependencies:
```bash
uv sync --group test
```

This installs pytest, pytest-cov, pytest-playwright, requests-mock, freezegun, and playwright.

### Running Tests

**Unit tests only (fast, skip E2E):**
```bash
uv run test
```

**Full test suite (includes E2E with Playwright):**
```bash
uv run test-all
```

Note: For E2E tests, you need to install Playwright browsers first:
```bash
python -m playwright install
```

You can also run pytest directly if needed:
```bash
pytest -q -m "not e2e"  # unit tests
pytest -q                # all tests
```

### Coverage Reports

Coverage is automatically generated when running tests (configured in `pytest.ini`).

**Unit tests with coverage:**
```bash
uv run cov
```

**Full tests with coverage:**
```bash
uv run cov-all
```

**HTML coverage report:**
```bash
uv run cov-html
```
Then open `htmlcov/index.html` in your browser.

You can also run with pytest directly:
```bash
pytest -q -m "not e2e"                      # unit tests with coverage
pytest -q                                    # all tests with coverage
pytest -q -m "not e2e" --cov-report=html    # HTML report
```

### Current Coverage (Unit Tests)
```
Name                                  Stmts   Miss  Cover   Missing
-------------------------------------------------------------------
dashboard\auth.py                        60     20    67%   
dashboard\callbacks.py                  120     73    39%   
dashboard\config.py                      64      2    97%   
dashboard\datasources\repository.py      37      3    92%   
dashboard\datasources\rest.py            32     15    53%   
dashboard\datasources\sql.py             15      5    67%   
dashboard\server.py                      28      1    96%   
dashboard\ui.py                          27      9    67%   
dashboard\utils.py                        9      1    89%   
-------------------------------------------------------------------
TOTAL                                   459    129    72%
```

### Test Markers
- `@pytest.mark.e2e` - End-to-end UI tests with Playwright
- `@pytest.mark.slow` - Slow-running tests

For custom marker filtering, use pytest directly:
```bash
pytest -q -m "not slow"     # skip slow tests
pytest -q -m "e2e"          # only E2E tests
```

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