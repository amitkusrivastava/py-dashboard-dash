import os

import pytest

from dashboard.config import Settings


def test_settings_env_var_precedence(monkeypatch):
    """Test that environment variables take precedence over .env file."""
    monkeypatch.setenv("APP_TITLE", "FromEnvVar")
    s = Settings()
    assert s.app_title == "FromEnvVar"


def test_settings_aliases_env(monkeypatch):
    monkeypatch.setenv("PORT", "8123")
    monkeypatch.setenv("DEBUG", "1")
    monkeypatch.setenv("DATA_SOURCE", "synthetic")
    s = Settings()
    assert s.port == 8123
    assert s.debug is True
    assert s.data_source == "SYNTHETIC"


def test_direct_instantiation_defaults():
    s = Settings()
    assert isinstance(s.max_rows, int)
    assert s.cache_type in ("SimpleCache", "RedisCache")
