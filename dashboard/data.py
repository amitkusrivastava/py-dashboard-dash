from typing import Optional

from flask_caching import Cache
import pandas as pd

from .config import get_settings
from .datasources import DataRepository

# Module-level cache kept for backward compatibility, though repository manages caching internally.
_cache: Optional[Cache] = None

# Singleton repository instance for the module facade, initialized with settings
_repo = DataRepository(settings=get_settings())


def set_cache(cache: Cache) -> None:
    """Wire the Flask-Caching instance into the data repository.

    Backward-compatible entrypoint called from the composition root.
    """
    global _cache
    _cache = cache
    _repo.set_cache(cache)


def get_data(force_key: Optional[str] = None) -> pd.DataFrame:
    """Public data accessor used by UI and callbacks.

    Delegates to the DataRepository which handles provider selection,
    capping, normalization, and caching.
    """
    return _repo.get_data(force_key)
