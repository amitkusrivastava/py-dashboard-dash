from dashboard.server import ServerFactory
from dashboard import config


def test_health_endpoint(flask_client):
    rv = flask_client.get("/health")
    assert rv.status_code == 200
    js = rv.get_json()
    assert js["status"] == "ok"
    assert "time" in js


def test_server_factory_title_and_cache():
    settings = config.get_settings()
    factory = ServerFactory(settings)
    server = factory.create_server()
    cache = factory.create_cache(server)
    app = factory.create_app(server)
    # Dash app title comes from settings
    assert app.title == settings.app_title
    # Cache configured type matches settings
    assert cache.config.get("CACHE_TYPE") == settings.cache_type
