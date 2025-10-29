from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from flask import Flask
from flask_caching import Cache

from dashboard.datasources.repository import DataRepository
from dashboard.datasources.base import DataProvider
from dashboard.config import Settings
from dashboard.utils import today_key


@dataclass
class FakeProvider(DataProvider):
    rows: int

    def load(self) -> pd.DataFrame:  # type: ignore[override]
        df = pd.DataFrame({
            "date": ["2025-01-01"] * self.rows,
            "product": ["A"] * self.rows,
            "region": ["APAC"] * self.rows,
            "system": ["Core"] * self.rows,
            "team": ["Data"] * self.rows,
            "owner": ["alice"] * self.rows,
            "status": ["Green"] * self.rows,
            "revenue": [100.0] * self.rows,
            "cost": [60.0] * self.rows,
        })
        df["profit"] = df["revenue"] - df["cost"]
        return df


def test_repository_capping_and_normalization():
    s = Settings(max_rows=50)
    repo = DataRepository(provider=FakeProvider(rows=200), settings=s)
    df = repo.load_uncached()
    # Should be capped
    assert len(df) == 50
    # date coerced to date
    assert pd.api.types.is_object_dtype(df["date"]) or str(df["date"].dtype).startswith("datetime")


def test_repository_caching_with_flask_cache(monkeypatch):
    s = Settings(max_rows=30)
    repo = DataRepository(provider=FakeProvider(rows=30), settings=s)

    # wire cache
    server = Flask(__name__)
    cache = Cache(server, config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 60})
    repo.set_cache(cache)

    calls = {"count": 0}
    orig = repo.load_uncached

    def wrapped():
        calls["count"] += 1
        return orig()

    monkeypatch.setattr(repo, "load_uncached", wrapped)

    key = today_key()
    _ = repo.get_data()  # first call
    _ = repo.get_data()  # second call should be cached
    assert calls["count"] == 1

    # Force key should bypass same memoized value
    _ = repo.get_data(force_key=f"{key}__123")
    assert calls["count"] == 2
