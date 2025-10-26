from typing import Protocol

import pandas as pd


class DataProvider(Protocol):
    """Protocol for data providers returning a pandas DataFrame."""

    def load(self) -> pd.DataFrame: ...
