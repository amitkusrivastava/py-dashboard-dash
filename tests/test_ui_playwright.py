import pytest


@pytest.mark.e2e
@pytest.mark.slow
def test_ui_loads_kpis_and_exports_csv(live_server_url):
    pw = pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(accept_downloads=True)
        page = ctx.new_page()

        page.goto(live_server_url, wait_until="networkidle")
        # Basic elements present
        page.wait_for_selector("#refresh-btn")
        page.wait_for_selector("#export-btn")

        # Trigger data load refresh and wait for debug message
        page.click("#refresh-btn")
        page.wait_for_selector('#debug-msg:has-text("Rows available")')

        # Wait for KPIs to populate and assert not placeholders
        page.wait_for_selector("#kpi-rev")
        rev_text = page.inner_text("#kpi-rev").strip()
        assert rev_text != "—"

        # Verify graphs exist (Dash renders as svg/canvas inside .js-plotly-plot)
        page.wait_for_selector(".js-plotly-plot")

        # Try exporting CSV
        with page.expect_download() as dl_info:
            page.click("#export-btn")
        download = dl_info.value
        assert download.suggested_filename.startswith("dashboard_export_")

        browser.close()
