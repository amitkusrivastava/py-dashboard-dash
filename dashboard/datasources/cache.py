from __future__ import annotations

from typing import Callable, Any, Optional

from flask_caching import Cache


class CacheFacade:
    """Thin wrapper over Flask-Caching to make caching injectable and optional.

    When no cache is provided, `memoize` is a no-op and returns the wrapped function.
    """

    def __init__(self, cache: Optional[Cache], timeout_seconds: int) -> None:
        self.cache = cache
        self.timeout_seconds = timeout_seconds

    def memoize(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        if self.cache is None:
            return fn
        return self.cache.memoize(timeout=self.timeout_seconds)(fn)
