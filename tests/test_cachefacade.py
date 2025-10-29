from __future__ import annotations

import time

import pandas as pd
from flask import Flask
from flask_caching import Cache

from dashboard.datasources.cache import CacheFacade


def test_cachefacade_no_cache_is_noop(monkeypatch):
    calls = {"n": 0}

    def fn(x):
        calls["n"] += 1
        return x * 2

    facade = CacheFacade(cache=None, timeout_seconds=1)
    wrapped = facade.memoize(fn)
    assert wrapped(3) == 6
    assert wrapped(3) == 6
    # Without cache, both calls executed the function
    assert calls["n"] == 2


def test_cachefacade_with_flask_cache_memoizes():
    server = Flask(__name__)
    cache = Cache(server, config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 60})
    facade = CacheFacade(cache=cache, timeout_seconds=60)

    calls = {"n": 0}

    def fn(x):
        calls["n"] += 1
        return x + 1

    wrapped = facade.memoize(fn)
    assert wrapped(10) == 11
    assert wrapped(10) == 11
    # Second call should hit cache
    assert calls["n"] == 1
