import datetime as dt
from typing import Optional
from dash import dcc, html, dash_table

from .config import get_settings
from .auth import current_claims
from .data import get_data


class UIBuilder:
    """Class that encapsulates layout building logic."""

    def __init__(self, title: Optional[str] = None) -> None:
        self.title = title or get_settings().app_title

    @staticmethod
    def kpi_card(label, value, id_suffix):
        return html.Div(
            className="kpi-card",
            children=[
                html.Div(label, className="kpi-label"),
                html.Div(value, className="kpi-value", id=f"kpi-{id_suffix}")
            ],
            style={
                "border": "1px solid #e0e0e0",
                "borderRadius": "8px",
                "padding": "12px 16px",
                "minWidth": "160px",
                "boxShadow": "0 1px 2px rgba(0,0,0,0.04)",
                "background": "white",
            }
        )

    def build_layout(self):
        claims = current_claims()
        role = claims.get("role", "Developer")
        user_name = claims.get("name", claims.get("sub", "User"))

        # Pre-populate controls options from today's data (server-side render)
        df = get_data()  # small data; safe to sample columns
        products = sorted(df["product"].dropna().unique().tolist())
        regions = sorted(df["region"].dropna().unique().tolist())
        systems = sorted(df["system"].dropna().unique().tolist())
        teams = sorted(df["team"].dropna().unique().tolist())

        # Role-based visibility helpers
        show_cio = role == "CIO"
        show_arch = role == "Architect"
        show_dev = role == "Developer"

        return html.Div([
            # Store claims and bootstrap data to the client (per-request, role-aware)
            dcc.Store(id="claims-store", data=claims),
            dcc.Store(id="data-store"),  # filled by a callback on load/refresh
            dcc.Download(id="download-data"),

            html.Div([
                html.H2(self.title, style={"margin": "0"}),
                html.Div(f"Welcome, {user_name} — Role: {role}", style={"color": "#666"}),
            ], style={"display": "flex", "flexDirection": "column", "gap": "4px", "marginBottom": "12px"}),

            # ==== Filters / Controls (Interactive Elements) ====
            html.Div([
                dcc.DatePickerRange(
                    id="date-range",
                    min_date_allowed=(dt.date.today() - dt.timedelta(days=365)),
                    max_date_allowed=dt.date.today(),
                    start_date=(dt.date.today() - dt.timedelta(days=30)),
                    end_date=dt.date.today(),
                    display_format="YYYY-MM-DD",
                ),
                dcc.Dropdown(products, products[:2], id="product-dd", placeholder="Select products", multi=True, style={"minWidth": "220px"}),
                dcc.Dropdown(regions, regions[:2], id="region-dd", placeholder="Select regions", multi=True, style={"minWidth": "220px"}),
                dcc.Dropdown(systems, None, id="system-dd", placeholder="System (optional)", multi=True, style={"minWidth": "220px"}),
                dcc.Dropdown(teams, None, id="team-dd", placeholder="Team (optional)", multi=True, style={"minWidth": "220px"}),

                dcc.Slider(id="min-profit-slider", min=-100000, max=200000, step=1000, value=0,
                           tooltip={"always_visible": False, "placement": "bottom"}),

                dcc.RadioItems(
                    id="agg-radio", options=[{"label": "Sum", "value": "sum"}, {"label": "Average", "value": "mean"}],
                    value="sum", inline=True
                ),
                dcc.Input(id="search-owner", placeholder="Search owner...", type="text"),

                dcc.Dropdown(
                    id="groupby-dd",
                    options=[{"label": l, "value": v} for v, l in [
                        ("date", "By Date"), ("product", "By Product"), ("region", "By Region"),
                        ("system", "By System"), ("team", "By Team"), ("status", "By Status")
                    ]],
                    value="date", clearable=False, style={"minWidth": "220px"}
                ),

                html.Button("Refresh Data", id="refresh-btn", n_clicks=0),
                html.Button("Export CSV", id="export-btn", n_clicks=0),
            ], style={"display": "grid", "gridTemplateColumns": "repeat(4, minmax(220px, 1fr))", "gap": "10px", "alignItems": "center"}),

            html.Hr(),

            # ==== KPI Cards (CIO + Architects by default) ====
            html.Div(
                id="kpi-row",
                children=[
                    UIBuilder.kpi_card("Total Revenue", "—", "rev"),
                    UIBuilder.kpi_card("Total Cost", "—", "cost"),
                    UIBuilder.kpi_card("Total Profit", "—", "profit"),
                    UIBuilder.kpi_card("Red Systems (today)", "—", "red"),
                ],
                style={"display": ("flex" if (show_cio or show_arch) else "none"),
                       "gap": "12px", "flexWrap": "wrap", "marginBottom": "8px"}
            ),

            # ==== Tabs by Persona ====
            dcc.Tabs(id="tabs", value=("cio" if show_cio else "arch" if show_arch else "dev"), children=[
                dcc.Tab(label="CIO Overview", value="cio", children=[
                    dcc.Graph(id="rev-by-dim-graph"),        # Interactive graph (click/hover)
                    dcc.Graph(id="trend-graph"),             # Time series
                ], disabled=not show_cio),

                dcc.Tab(label="Architecture View", value="arch", children=[
                    dcc.Graph(id="system-health-graph"),     # System status/health aggregation
                    dcc.Graph(id="team-workload-graph"),     # Workload by team/system
                ], disabled=not show_arch),

                dcc.Tab(label="Developer View", value="dev", children=[
                    dash_table.DataTable(
                        id="detail-table",
                        columns=[{"name": c, "id": c} for c in
                                 ["date", "product", "region", "system", "team", "owner", "status", "revenue", "cost", "profit"]],
                        page_size=15,
                        sort_action="native",
                        filter_action="native",
                        column_selectable="single",
                        style_table={"overflowX": "auto"},
                        style_cell={"minWidth": 80, "maxWidth": 200, "whiteSpace": "nowrap", "textOverflow": "ellipsis"}
                    )
                ], disabled=not show_dev),
            ]),

            html.Div(id="debug-msg", style={"fontSize": "12px", "color": "#999", "marginTop": "6px"}),

        ])


def serve_layout():
    return UIBuilder().build_layout()
