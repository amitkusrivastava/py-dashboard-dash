import datetime as dt
import time
from typing import List, Dict, Any, Optional, Literal

import pandas as pd
from dash import Input, Output, State, no_update
from pydantic import BaseModel, field_validator, ValidationError

from . import config
from .data import get_data
from .utils import today_key, fmt_money


class Filters(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    products: Optional[List[str]] = None
    regions: Optional[List[str]] = None
    systems: Optional[List[str]] = None
    teams: Optional[List[str]] = None
    min_profit: Optional[float] = None
    owner_query: Optional[str] = None
    agg: Literal["sum", "mean"] = "sum"
    groupby: str = "date"

    @field_validator("products", "regions", "systems", "teams", mode="before")
    @classmethod
    def ensure_list(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, list):
            return v
        return [v]

    @field_validator("owner_query", mode="before")
    @classmethod
    def normalize_query(cls, v):
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None


def _filter_df(df: pd.DataFrame,
               start_date, end_date, products, regions, systems, teams, min_profit, owner_query) -> pd.DataFrame:
    if start_date:
        df = df[df["date"] >= pd.to_datetime(start_date).date()]
    if end_date:
        df = df[df["date"] <= pd.to_datetime(end_date).date()]
    if products:
        df = df[df["product"].isin(products)]
    if regions:
        df = df[df["region"].isin(regions)]
    if systems:
        df = df[df["system"].isin(systems)]
    if teams:
        df = df[df["team"].isin(teams)]
    if owner_query:
        q = owner_query.strip().lower()
        df = df[df["owner"].str.lower().str.contains(q, na=False)]
    if min_profit is not None:
        df = df[df["profit"] >= float(min_profit)]
    return df


def register_callbacks(app):

    @app.callback(
        Output("data-store", "data"),
        Output("debug-msg", "children"),
        Input("refresh-btn", "n_clicks"),
        State("claims-store", "data"),
        prevent_initial_call=False
    )
    def bootstrap_data(n_clicks, claims):
        """
        Load data on first page load and when 'Refresh Data' is clicked.
        Uses daily memoized cache; clicking refresh busts cache with a random key.
        Applies simple RBAC row-level narrowing for Developer (by team if present).
        """
        force_key = None
        if n_clicks and n_clicks > 0:
            force_key = f"{today_key()}__{int(time.time())}"

        df = get_data(force_key=force_key)

        # RBAC: If Developer and token has 'team', scope data to their team
        role = (claims or {}).get("role", "Developer")
        team = (claims or {}).get("team")
        if role == "Developer" and team:
            df = df[df["team"] == team].copy()

        data_json = df.to_dict(orient="records")
        msg = f"Rows available: {len(df)} | Source: {config.DATA_SOURCE} | Role: {role}" + (f" | Team: {team}" if team else "")
        return data_json, msg

    @app.callback(
        Output("kpi-rev", "children"),
        Output("kpi-cost", "children"),
        Output("kpi-profit", "children"),
        Output("kpi-red", "children"),
        Output("rev-by-dim-graph", "figure"),
        Output("trend-graph", "figure"),
        Output("system-health-graph", "figure"),
        Output("team-workload-graph", "figure"),
        Output("detail-table", "data"),
        Input("data-store", "data"),
        Input("date-range", "start_date"),
        Input("date-range", "end_date"),
        Input("product-dd", "value"),
        Input("region-dd", "value"),
        Input("system-dd", "value"),
        Input("team-dd", "value"),
        Input("min-profit-slider", "value"),
        Input("search-owner", "value"),
        Input("agg-radio", "value"),
        Input("groupby-dd", "value"),
        State("claims-store", "data"),
        prevent_initial_call=True
    )
    def update_viz(data_json, start_date, end_date, products, regions, systems, teams,
                   min_profit, owner_query, agg, groupby, claims):
        if not data_json:
            empty_fig = {"data": [], "layout": {"paper_bgcolor": "white", "plot_bgcolor": "white"}}
            return "—", "—", "—", "—", empty_fig, empty_fig, empty_fig, empty_fig, []

        # Validate/normalize filters via Pydantic
        try:
            flt = Filters(
                start_date=start_date,
                end_date=end_date,
                products=products,
                regions=regions,
                systems=systems,
                teams=teams,
                min_profit=min_profit,
                owner_query=owner_query,
                agg=agg,
                groupby=groupby,
            )
        except ValidationError as e:
            # In case of bad inputs, return empty visuals with a hint in debug
            empty_fig = {"data": [], "layout": {"paper_bgcolor": "white", "plot_bgcolor": "white"}}
            return "—", "—", "—", "—", empty_fig, empty_fig, empty_fig, empty_fig, []

        df = pd.DataFrame.from_records(data_json)
        fdf = _filter_df(df, flt.start_date, flt.end_date, flt.products, flt.regions, flt.systems, flt.teams, flt.min_profit, flt.owner_query)

        # KPIs
        rev = float(fdf["revenue"].sum()) if not fdf.empty else 0.0
        cost = float(fdf["cost"].sum()) if not fdf.empty else 0.0
        profit = float(fdf["profit"].sum()) if not fdf.empty else 0.0
        today = pd.to_datetime(end_date).date() if end_date else dt.date.today()
        red_count = int(fdf[(fdf["date"] == today) & (fdf["status"] == "Red")]["system"].nunique())

        kpi_rev = f"${fmt_money(rev)}"
        kpi_cost = f"${fmt_money(cost)}"
        kpi_profit = f"${fmt_money(profit)}"
        kpi_red = str(red_count)

        # Aggregation
        agg_fn = {"sum": "sum", "mean": "mean"}.get(agg, "sum")
        if fdf.empty:
            grouped = pd.DataFrame(columns=[groupby, "revenue", "cost", "profit"])
        else:
            grouped = fdf.groupby(groupby).agg({"revenue": agg_fn, "cost": agg_fn, "profit": agg_fn}).reset_index()

        # Figure 1
        fig1 = {
            "data": [
                {"type": "bar", "x": grouped[groupby], "y": grouped["revenue"], "name": "Revenue"},
                {"type": "bar", "x": grouped[groupby], "y": grouped["cost"], "name": "Cost"},
            ],
            "layout": {"barmode": "group", "title": f"Revenue/Cost by {groupby.capitalize()}", "paper_bgcolor": "white", "plot_bgcolor": "white"}
        }

        # Figure 2
        if fdf.empty:
            trend = pd.DataFrame(columns=["date", "profit"])
        else:
            trend = fdf.groupby("date")["profit"].sum().reset_index().sort_values("date")
        fig2 = {
            "data": [{"type": "scatter", "mode": "lines+markers", "x": trend["date"], "y": trend["profit"], "name": "Profit"}],
            "layout": {"title": "Profit Trend", "paper_bgcolor": "white", "plot_bgcolor": "white"}
        }

        # Figure 3
        if fdf.empty:
            sys_health = pd.DataFrame(columns=["system", "status", "count"])
        else:
            sys_health = fdf.groupby(["system", "status"]).size().reset_index(name="count")
        statuses = ["Green", "Amber", "Red"]
        fig3_data = []
        for s in statuses:
            part = sys_health[sys_health["status"] == s]
            fig3_data.append({"type": "bar", "x": part["system"], "y": part["count"], "name": s})
        fig3 = {"data": fig3_data, "layout": {"barmode": "stack", "title": "System Health", "paper_bgcolor": "white", "plot_bgcolor": "white"}}

        # Figure 4
        if fdf.empty:
            team_work = pd.DataFrame(columns=["team", "rows"])
        else:
            team_work = fdf.groupby("team").size().reset_index(name="rows")
        fig4 = {"data": [{"type": "bar", "x": team_work["team"], "y": team_work["rows"], "name": "Rows"}],
                "layout": {"title": "Workload by Team", "paper_bgcolor": "white", "plot_bgcolor": "white"}}

        table_rows = fdf.to_dict(orient="records")
        return kpi_rev, kpi_cost, kpi_profit, kpi_red, fig1, fig2, fig3, fig4, table_rows

    @app.callback(
        Output("download-data", "data"),
        Input("export-btn", "n_clicks"),
        State("detail-table", "data"),
        prevent_initial_call=True
    )
    def export_csv(n_clicks, table_rows):
        if not n_clicks:
            return no_update
        df = pd.DataFrame.from_records(table_rows or [])
        csv = df.to_csv(index=False)
        return dict(content=csv, filename=f"dashboard_export_{dt.date.today().isoformat()}.csv")
