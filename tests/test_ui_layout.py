from dash.development.base_component import Component

from dashboard.ui import serve_layout


def test_serve_layout_returns_component():
    layout = serve_layout()
    assert isinstance(layout, Component)
    # Ensure key IDs exist in the tree by stringifying
    s = str(layout)
    assert "date-range" in s
    assert "product-dd" in s
    assert "region-dd" in s
    assert "refresh-btn" in s
    assert "export-btn" in s
