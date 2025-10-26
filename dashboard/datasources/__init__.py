"""Data layer package: providers, cache facade, and repository.

Public exports:
- DataProvider protocol
- SyntheticProvider, RestProvider, SqlProvider
- CacheFacade
- DataRepository
"""
from .base import DataProvider
from .synthetic import SyntheticProvider
from .rest import RestProvider
from .sql import SqlProvider
from .cache import CacheFacade
from .repository import DataRepository

__all__ = [
    "DataProvider",
    "SyntheticProvider",
    "RestProvider",
    "SqlProvider",
    "CacheFacade",
    "DataRepository",
]
