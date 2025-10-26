import pandas as pd
from sqlalchemy import create_engine

from ..config import Settings, get_settings
from .synthetic import SyntheticProvider


class SqlProvider:
    """Loads data from SQL database defined by DB_URL setting."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def load(self) -> pd.DataFrame:
        if not self.settings.db_url:
            return SyntheticProvider(self.settings).load()
        engine = create_engine(self.settings.db_url, pool_pre_ping=True)
        sql = (
            """
            SELECT
                CAST(date AS DATE) AS date,
                product, region, system, team, owner, status,
                revenue::float AS revenue, cost::float AS cost
            FROM analytics_facts
            """
        )
        df = pd.read_sql(sql, engine)
        df["profit"] = df["revenue"] - df["cost"]
        return df
