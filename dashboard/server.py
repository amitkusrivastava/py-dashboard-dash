import datetime as dt
from flask import Flask
from flask_caching import Cache
from dash import Dash
from typing import Optional

from .config import Settings, get_settings


class ServerFactory:
    """Class-based factory for Flask server, Cache, and Dash app."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def create_server(self) -> Flask:
        server = Flask(__name__)

        @server.route("/health")
        def health():
            return {"status": "ok", "time": dt.datetime.utcnow().isoformat()}

        return server

    def create_cache(self, server: Flask) -> Cache:
        cache = Cache(server, config={
            "CACHE_TYPE": self.settings.cache_type,
            "CACHE_DEFAULT_TIMEOUT": self.settings.cache_timeout_seconds,
            **({"CACHE_REDIS_URL": self.settings.redis_url} if self.settings.cache_type == "RedisCache" else {})
        })
        return cache

    def create_app(self, server: Flask) -> Dash:
        app = Dash(
            __name__,
            server=server,
            suppress_callback_exceptions=True,
            title=self.settings.app_title,
        )
        app._favicon = None
        return app


# Backward-compatible function wrappers

def create_server() -> Flask:
    return ServerFactory().create_server()


def create_cache(server: Flask) -> Cache:
    return ServerFactory().create_cache(server)


def create_app(server: Flask) -> Dash:
    return ServerFactory().create_app(server)
