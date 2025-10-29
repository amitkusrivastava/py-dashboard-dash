import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from dashboard.datasources.synthetic import SyntheticProvider
from dashboard.datasources.rest import RestProvider
from dashboard.datasources.sql import SqlProvider
from dashboard.config import Settings


def test_synthetic_provider_respects_max_rows():
    s = Settings(max_rows=123)
    prov = SyntheticProvider(settings=s, seed=1)
    df = prov.load()
    assert len(df) == 123
    assert {"date","product","region","system","team","owner","status","revenue","cost","profit"} <= set(df.columns)


def test_rest_provider_falls_back_to_synthetic_when_no_base_url(monkeypatch):
    s = Settings(api_base_url="")
    prov = RestProvider(settings=s)
    df = prov.load()
    assert not df.empty


def test_rest_provider_fetch_and_normalize(monkeypatch):
    s = Settings(api_base_url="https://api.example.com")

    payload = [
        {
            "date": "2025-01-01",
            "product": "Alpha",
            "region": "EMEA",
            "system": "Core",
            "team": "Platform",
            "owner": "alice",
            "status": "Green",
            "revenue": 100.0,
            "cost": 60.0,
        }
    ]

    class FakeResp:
        def __init__(self, obj):
            self._obj = obj
        def raise_for_status(self):
            return None
        def json(self):
            return self._obj

    def fake_get(url, timeout):  # noqa: ARG001
        assert url.endswith("/metrics")
        return FakeResp(payload)

    monkeypatch.setattr("requests.get", fake_get)

    df = RestProvider(settings=s).load()
    assert set(["date","product","region","system","team","owner","status","revenue","cost","profit"]) <= set(df.columns)
    assert float(df.loc[0, "profit"]) == 40.0


def test_sql_provider_fetch_and_normalize(monkeypatch):
    s = Settings(db_url="postgresql://u:p@h/db")

    class DummyEngine: ...

    def fake_create_engine(url, pool_pre_ping):  # noqa: ARG001
        assert url == s.db_url
        return DummyEngine()

    def fake_read_sql(sql, engine):  # noqa: ARG001
        return pd.DataFrame([
            {"date": "2025-01-02", "product":"A", "region":"APAC", "system":"Core", "team":"Data", "owner":"bob", "status":"Amber", "revenue": 200.0, "cost": 50.0}
        ])

    monkeypatch.setattr("dashboard.datasources.sql.create_engine", fake_create_engine)
    monkeypatch.setattr(pd, "read_sql", fake_read_sql)

    df = SqlProvider(settings=s).load()
    assert float(df.loc[0, "profit"]) == 150.0
