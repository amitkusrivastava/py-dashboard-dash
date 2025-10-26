import datetime as dt

import numpy as np
import pandas as pd

from ..config import Settings, get_settings


class SyntheticProvider:
    """Generates synthetic dashboard data for demos and local development."""

    def __init__(self, settings: Settings | None = None, seed: int = 42) -> None:
        self.settings = settings or get_settings()
        self.seed = seed

    def load(self) -> pd.DataFrame:
        rows = self.settings.max_rows
        rng = np.random.default_rng(self.seed)
        days = pd.date_range(dt.date.today() - dt.timedelta(days=90), periods=91, freq="D")
        products = ["Alpha", "Beta", "Gamma", "Delta"]
        regions = ["APAC", "EMEA", "AMER", "India"]
        systems = ["Payments", "CoreBanking", "DataLake", "API-Gateway", "Mobile", "Web"]
        teams = ["Platform", "Retail", "Corporate", "Data", "Integration"]
        owners = ["alice", "bob", "carol", "dave", "erin"]
        statuses = ["Green", "Amber", "Red"]
        df = pd.DataFrame({
            "date": rng.choice(days, size=rows),
            "product": rng.choice(products, size=rows),
            "region": rng.choice(regions, size=rows),
            "system": rng.choice(systems, size=rows),
            "team": rng.choice(teams, size=rows),
            "owner": rng.choice(owners, size=rows),
            "status": rng.choice(statuses, size=rows, p=[0.7, 0.2, 0.1]),
            "revenue": (rng.normal(100000, 25000, size=rows)).clip(min=1000),
            "cost": (rng.normal(60000, 15000, size=rows)).clip(min=500),
        })
        df["profit"] = df["revenue"] - df["cost"]
        return df
