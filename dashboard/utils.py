import datetime as dt


def today_key() -> str:
    """Cache-busting key that changes daily."""
    return dt.date.today().isoformat()


def fmt_money(x: float) -> str:
    """Compact human-readable money formatting (e.g., 12.3K, 7M)."""
    for unit in ["", "K", "M", "B"]:
        if abs(x) < 1000.0:
            return f"{x:,.0f}{unit}"
        x /= 1000.0
    return f"{x:,.0f}T"
