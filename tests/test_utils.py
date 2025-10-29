import datetime as dt

from dashboard.utils import today_key, fmt_money


def test_today_key(monkeypatch):
    class FakeDate(dt.date):
        @classmethod
        def today(cls):
            return cls(2025, 1, 15)

    monkeypatch.setattr(dt, "date", FakeDate)
    assert today_key() == "2025-01-15"


def test_fmt_money_ranges():
    assert fmt_money(0) == "0"
    assert fmt_money(999) == "999"
    assert fmt_money(12_300) == "12K"
    assert fmt_money(12_900) == "13K"
    assert fmt_money(7_000_000) == "7M"
    assert fmt_money(1_500_000_000) == "1B"
    assert fmt_money(2_000_000_000_000) == "2T"
