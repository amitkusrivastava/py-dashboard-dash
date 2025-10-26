from typing import List

import numpy as np
import pandas as pd
import requests

from ..config import Settings, get_settings
from .synthetic import SyntheticProvider


class RestProvider:
    """Fetches metrics from a REST API and normalizes to the dashboard schema."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _endpoints(self) -> List[str]:
        base = (self.settings.api_base_url or "").rstrip("/")
        if not base:
            return []
        return [f"{base}/metrics"]

    def load(self) -> pd.DataFrame:
        endpoints = self._endpoints()
        if not endpoints:
            return SyntheticProvider(self.settings).load()

        frames: list[pd.DataFrame] = []
        for url in endpoints:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            frames.append(pd.DataFrame(resp.json()))

        if not frames:
            return SyntheticProvider(self.settings).load()

        df = pd.concat(frames, ignore_index=True)

        needed = {"date", "product", "region", "system", "team", "owner", "status", "revenue", "cost"}
        for col in needed - set(df.columns):
            df[col] = np.nan  # type: ignore[name-defined]

        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["profit"] = df["revenue"] - df["cost"]
        return df
