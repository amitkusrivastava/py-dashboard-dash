from __future__ import annotations

from typing import Optional

import pandas as pd
from flask_caching import Cache

from ..config import Settings, get_settings
from ..utils import today_key
from .base import DataProvider
from .cache import CacheFacade
from .rest import RestProvider
from .sql import SqlProvider
from .synthetic import SyntheticProvider


class DataRepository:
    """High-level data access with provider selection, capping, normalization, and caching."""

    def __init__(
        self,
        provider: Optional[DataProvider] = None,
        cache_facade: Optional[CacheFacade] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.provider = provider or self._default_provider()
        self.cache_facade = cache_facade or CacheFacade(cache=None, timeout_seconds=self.settings.cache_timeout_seconds)

    # ---- Provider selection ----
    def _default_provider(self) -> DataProvider:
        src = self.settings.data_source
        if src == "REST":
            return RestProvider(self.settings)
        if src == "SQL":
            return SqlProvider(self.settings)
        return SyntheticProvider(self.settings)

    # ---- Loaders ----
    def load_uncached(self) -> pd.DataFrame:
        df = self.provider.load()
        if len(df) > self.settings.max_rows:
            df = df.sample(self.settings.max_rows, random_state=1).reset_index(drop=True)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        return df

    def load_cached(self, day_key: str) -> pd.DataFrame:
        @self.cache_facade.memoize
        def _inner(_k: str) -> pd.DataFrame:  # pragma: no cover - thin wrapper
            return self.load_uncached()

        return _inner(day_key)

    def get_data(self, force_key: Optional[str] = None) -> pd.DataFrame:
        key = force_key if force_key else today_key()
        df = self.load_cached(key)
        return df.copy()

    # ---- Cache wiring ----
    def set_cache(self, cache: Cache) -> None:
        self.cache_facade = CacheFacade(cache, timeout_seconds=self.settings.cache_timeout_seconds)
