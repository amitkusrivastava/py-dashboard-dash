# Thin entrypoint exposing Dash `app` and Flask `server`
from dashboard import app, server  # noqa: F401
from dashboard import config


if __name__ == "__main__":  # pragma: no cover
    # For production: use gunicorn with multiple workers, e.g.:
    # gunicorn app:server --workers 4 --threads 2 --timeout 120 --bind 0.0.0.0:8050
    app.run_server(host="0.0.0.0", port=config.PORT, debug=config.DEBUG)
