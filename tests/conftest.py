import os
import threading
import time
from contextlib import contextmanager
from typing import Iterator

import pytest
import requests

# Ensure predictable dev-like environment before importing the app
os.environ.setdefault("APP_ENV", "dev")
os.environ.setdefault("PORT", "8060")  # test port
os.environ.setdefault("DEBUG", "0")
os.environ.setdefault("DISABLE_AUTH", "1")
os.environ.setdefault("DATA_SOURCE", "SYNTHETIC")
os.environ.setdefault("CACHE_TYPE", "SimpleCache")
os.environ.setdefault("CACHE_TIMEOUT_SECONDS", "5")
os.environ.setdefault("MAX_ROWS", "200")


@pytest.fixture(scope="session")
def dash_app_and_server():
    """Import the app after env is set; expose Dash app and Flask server."""
    # Import delayed so config reads env just set above
    from dashboard import app as dash_app, server as flask_server  # noqa: WPS433 (import inside function)
    return dash_app, flask_server


@pytest.fixture(scope="session")
def flask_client(dash_app_and_server):
    """Flask test client with auth disabled by default."""
    _, server = dash_app_and_server
    return server.test_client()


@contextmanager
def run_server_in_thread(port: int) -> Iterator[str]:
    """Run the Dash development server in a background thread for E2E tests.

    Returns the base URL. The server is stopped when the context exits by
    setting the Dash internal Flask server shutdown flag via requests to /shutdown
    is not available in Dash; instead we rely on daemon thread termination at process end.
    """
    from dashboard import app as dash_app  # import here to avoid early import

    base_url = f"http://127.0.0.1:{port}"

    def _run():
        dash_app.run_server(host="127.0.0.1", port=port, debug=False, use_reloader=False)

    th = threading.Thread(target=_run, name="dash-test-server", daemon=True)
    th.start()

    # wait for /health to be ready
    deadline = time.time() + 20
    health = f"{base_url}/health"
    last_err = None
    while time.time() < deadline:
        try:
            r = requests.get(health, timeout=1)
            if r.status_code == 200:
                break
        except Exception as e:  # noqa: BLE001
            last_err = e
        time.sleep(0.2)
    else:
        raise RuntimeError(f"Server failed to start on {base_url}: {last_err}")

    try:
        yield base_url
    finally:
        # No clean shutdown hook for Dash dev server; thread will terminate at test process end.
        pass


@pytest.fixture(scope="session")
def live_server_url() -> str:
    """Start a live server on the configured test port and yield its base URL."""
    port = int(os.environ.get("PORT", "8060"))
    with run_server_in_thread(port) as url:
        yield url
