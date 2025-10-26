# app.py
import datetime as dt
import os
import time

import jwt  # PyJWT
import numpy as np
import pandas as pd
import requests
from dash import Dash, dcc, html, Input, Output, State, dash_table, no_update
from flask import Flask, request, abort, g
from flask_caching import Cache
from sqlalchemy import create_engine

# =========================
# Configuration (ENV-DRIVEN)
# =========================
APP_TITLE = os.getenv("APP_TITLE", "Enterprise Analytics Dashboard")
DATA_SOURCE = os.getenv("DATA_SOURCE", "SYNTHETIC").upper()  # "REST" | "SQL" | "SYNTHETIC"
API_BASE_URL = os.getenv("API_BASE_URL", "")                 # Used when DATA_SOURCE="REST"
DB_URL = os.getenv("DB_URL", "")                             # Used when DATA_SOURCE="SQL"
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")           # HS256 dev secret (use strong secret in prod)
JWT_ISSUER = os.getenv("JWT_ISSUER", None)                   # Optional: issuer to validate
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", None)               # Optional: audience to validate
DISABLE_AUTH = os.getenv("DISABLE_AUTH", "0") == "1"         # For local dev only
CACHE_TYPE = os.getenv("CACHE_TYPE", "SimpleCache")          # "RedisCache" with REDIS_URL for prod
CACHE_TIMEOUT_SECONDS = int(os.getenv("CACHE_TIMEOUT_SECONDS", str(24 * 60 * 60)))  # ~daily
MAX_ROWS = int(os.getenv("MAX_ROWS", "7000"))

# =========================
# Flask server + Dash app
# =========================
server = Flask(__name__)

cache = Cache(server, config={
    "CACHE_TYPE": CACHE_TYPE,
    "CACHE_DEFAULT_TIMEOUT": CACHE_TIMEOUT_SECONDS,
    **({"CACHE_REDIS_URL": os.getenv("REDIS_URL")} if CACHE_TYPE == "RedisCache" else {})
})

app = Dash(
    __name__,
    server=server,
    suppress_callback_exceptions=True,
    title=APP_TITLE,
)
app._favicon = None

# -------------------------
# Health endpoint (ops)
# -------------------------
@server.route("/health")
def health():
    return {"status": "ok", "time": dt.datetime.utcnow().isoformat()}

# ==================================
# Authentication: JWT (HS256 example)
# ==================================
def _decode_jwt(token: str) -> dict:
    """
    Decode and validate a JWT (HS256 by default). In production:
      - Prefer asymmetric (RS256) and JWKS validation.
      - Validate issuer/audience/exp/nbf properly.
    """
    options = {"require": ["exp"], "verify_exp": True}
    kwargs = {"algorithms": ["HS256"]}
    if JWT_ISSUER:
        kwargs["issuer"] = JWT_ISSUER
    if JWT_AUDIENCE:
        kwargs["audience"] = JWT_AUDIENCE
    return jwt.decode(token, JWT_SECRET, options=options, **kwargs)

def _default_claims():
    # Safe local dev defaults
    return {
        "sub": "devuser@example.com",
        "name": "Dev User",
        "role": os.getenv("DEFAULT_ROLE", "Developer"),
        "team": os.getenv("DEFAULT_TEAM", "Platform"),
        "exp": int(time.time()) + 3600,
    }

@server.before_request
def require_auth():
    """
    Secure all routes (including /_dash* update endpoints).
    Allow unauthenticated only if DISABLE_AUTH=1 (dev) or for health/assets.
    Expect 'Authorization: Bearer <JWT>'.
    """
    path = request.path or ""
    if path.startswith("/assets") or path == "/health":
        return None

    if DISABLE_AUTH:
        g.claims = _default_claims()
        return None

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        abort(401, description="Missing or invalid Authorization header")

    token = auth.split(" ", 1)[1].strip()
    try:
        claims = _decode_jwt(token)
    except Exception as e:
        abort(401, description=f"Invalid token: {e}")

    # Normalize role
    role = claims.get("role", "Developer")
    role_map = {
        "CIO": "CIO",
        "ChiefInformationOfficer": "CIO",
        "Architect": "Architect",
        "EnterpriseArchitect": "Architect",
        "SystemArchitect": "Architect",
        "SolutionArchitect": "Architect",
        "Developer": "Developer",
        "Engineer": "Developer",
    }
    claims["role"] = role_map.get(role, "Developer")
    g.claims = claims
    return None

def current_claims():
    """Access JWT claims for this request."""
    return getattr(g, "claims", _default_claims())


# ====================================
# Data loading & daily caching strategy
# ====================================
def _today_key():
    """Cache-busting key that changes daily."""
    return dt.date.today().isoformat()

def _synthetic_data(rows=MAX_ROWS, seed=42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    days = pd.date_range(dt.date.today() - dt.timedelta(days=90), periods=91, freq="D")
    products = ["Alpha", "Beta", "Gamma", "Delta"]
    regions = ["APAC", "EMEA", "AMER", "India"]
    systems = ["Payments", "CoreBanking", "DataLake", "API-Gateway", "Mobile", "Web"]
    teams = ["Platform", "Retail", "Corporate", "Data", "Integration"]
    owners = ["alice", "bob", "carol", "dave", "erin"]
    statuses = ["Green", "Amber", "Red"]

    df = pd.DataFrame({
        "date": rng.choice(days, size=rows),
        "product": rng.choice(products, size=rows),
        "region": rng.choice(regions, size=rows),
        "system": rng.choice(systems, size=rows),
        "team": rng.choice(teams, size=rows),
        "owner": rng.choice(owners, size=rows),
        "status": rng.choice(statuses, size=rows, p=[0.7, 0.2, 0.1]),
        "revenue": (rng.normal(100000, 25000, size=rows)).clip(min=1000),
        "cost": (rng.normal(60000, 15000, size=rows)).clip(min=500),
    })
    df["profit"] = df["revenue"] - df["cost"]
    return df

def _fetch_rest() -> pd.DataFrame:
    """
    Example: hit multiple REST endpoints from a virtualization layer.
    Expect JSON arrays with consistent schema; merge/join as needed.
    """
    if not API_BASE_URL:
        # Fallback to synthetic if not configured
        return _synthetic_data()

    # Example endpoints (customize to your API)
    endpoints = [
        f"{API_BASE_URL.rstrip('/')}/metrics",
    ]
    frames = []
    for url in endpoints:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        frames.append(pd.DataFrame(payload))
    if not frames:
        return _synthetic_data()
    df = pd.concat(frames, ignore_index=True)
    # Ensure required columns exist (normalize)
    needed = {"date", "product", "region", "system", "team", "owner", "status", "revenue", "cost"}
    for col in needed - set(df.columns):
        df[col] = np.nan
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["profit"] = df["revenue"] - df["cost"]
    return df

def _fetch_sql() -> pd.DataFrame:
    if not DB_URL:
        return _synthetic_data()
    engine = create_engine(DB_URL, pool_pre_ping=True)
    # Example SQL; JOIN your 5–6 tables as a view or CTE in production.
    sql = """
    SELECT
        CAST(date AS DATE) AS date,
        product, region, system, team, owner, status,
        revenue::float AS revenue, cost::float AS cost
    FROM analytics_facts
    """
    df = pd.read_sql(sql, engine)
    df["profit"] = df["revenue"] - df["cost"]
    return df

@cache.memoize(timeout=CACHE_TIMEOUT_SECONDS)
def load_data_cached(day_key: str) -> pd.DataFrame:
    """
    Memoized by 'day_key' so it refreshes daily. For a manual refresh,
    we can pass a unique key to bypass cache.
    """
    if DATA_SOURCE == "REST":
        df = _fetch_rest()
    elif DATA_SOURCE == "SQL":
        df = _fetch_sql()
    else:
        df = _synthetic_data()

    # Safety: cap rows if desired
    if len(df) > MAX_ROWS:
        df = df.sample(MAX_ROWS, random_state=1).reset_index(drop=True)

    # Normalize dtypes
    df["date"] = pd.to_datetime(df["date"]).dt.date
    # Lightweight aggregates for KPI cards
    return df

def get_data(force_key: str | None = None) -> pd.DataFrame:
    """
    Wrapper to fetch data; when force_key is provided, bypass cache by using a distinct key.
    """
    key = force_key if force_key else _today_key()
    df = load_data_cached(key)
    # Return a copy to avoid accidental cross-request mutation
    return df.copy()

# ====================================
# Role-based layout & interactive UI
# ====================================
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

def serve_layout():
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
            html.H2(APP_TITLE, style={"margin": "0"}),
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
                kpi_card("Total Revenue", "—", "rev"),
                kpi_card("Total Cost", "—", "cost"),
                kpi_card("Total Profit", "—", "profit"),
                kpi_card("Red Systems (today)", "—", "red"),
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

        # Light styles
        html.Style("""
            body { font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }
            .kpi-label { color: #666; font-size: 12px; }
            .kpi-value { font-weight: 700; font-size: 20px; margin-top: 4px; }
        """),
    ])

app.layout = serve_layout

# ====================================
# Callbacks: data bootstrapping & refresh
# ====================================
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
        # Bypass cache with a unique key
        force_key = f"{_today_key()}__{int(time.time())}"

    df = get_data(force_key=force_key)

    # RBAC: If Developer and token has 'team', scope data to their team
    role = (claims or {}).get("role", "Developer")
    team = (claims or {}).get("team")
    if role == "Developer" and team:
        df = df[df["team"] == team].copy()

    # Serialize to msgpack-like (records is ok for ~7k rows)
    data_json = df.to_dict(orient="records")
    msg = f"Rows available: {len(df)} | Source: {DATA_SOURCE} | Role: {role}" + (f" | Team: {team}" if team else "")
    return data_json, msg

# ====================================
# Helper: filter dataframe based on UI
# ====================================
def filter_df(df: pd.DataFrame,
              start_date, end_date, products, regions, systems, teams, min_profit, owner_query):
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

# ====================================
# KPI + Graphs + Table updates
# ====================================
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
        # First render can occur before data-store is filled
        empty_fig = {"data": [], "layout": {"paper_bgcolor": "white", "plot_bgcolor": "white"}}
        return "—", "—", "—", "—", empty_fig, empty_fig, empty_fig, empty_fig, []

    df = pd.DataFrame.from_records(data_json)
    # Filter
    fdf = filter_df(df, start_date, end_date, products, regions, systems, teams, min_profit, owner_query)

    # KPIs
    rev = float(fdf["revenue"].sum()) if not fdf.empty else 0.0
    cost = float(fdf["cost"].sum()) if not fdf.empty else 0.0
    profit = float(fdf["profit"].sum()) if not fdf.empty else 0.0
    # Red systems (today) — simple example: count rows with status Red for end_date
    today = pd.to_datetime(end_date).date() if end_date else dt.date.today()
    red_count = int(fdf[(fdf["date"] == today) & (fdf["status"] == "Red")]["system"].nunique())

    def fmt_money(x):  # compact formatting
        for unit in ["", "K", "M", "B"]:
            if abs(x) < 1000.0:
                return f"{x:,.0f}{unit}"
            x /= 1000.0
        return f"{x:,.0f}T"

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

    # Figure 1: Revenue by selected dimension
    fig1 = {
        "data": [
            {"type": "bar", "x": grouped[groupby], "y": grouped["revenue"], "name": "Revenue"},
            {"type": "bar", "x": grouped[groupby], "y": grouped["cost"], "name": "Cost"},
        ],
        "layout": {"barmode": "group", "title": f"Revenue/Cost by {groupby.capitalize()}", "paper_bgcolor": "white", "plot_bgcolor": "white"}
    }

    # Figure 2: Trend over time (profit)
    if fdf.empty:
        trend = pd.DataFrame(columns=["date", "profit"])
    else:
        trend = fdf.groupby("date")["profit"].sum().reset_index().sort_values("date")
    fig2 = {
        "data": [{"type": "scatter", "mode": "lines+markers", "x": trend["date"], "y": trend["profit"], "name": "Profit"}],
        "layout": {"title": "Profit Trend", "paper_bgcolor": "white", "plot_bgcolor": "white"}
    }

    # Figure 3: System health (count by status per system)
    if fdf.empty:
        sys_health = pd.DataFrame(columns=["system", "status", "count"])
    else:
        sys_health = fdf.groupby(["system", "status"]).size().reset_index(name="count")
    # Pivot to stacked bars
    statuses = ["Green", "Amber", "Red"]
    fig3_data = []
    for s in statuses:
        part = sys_health[sys_health["status"] == s]
        fig3_data.append({"type": "bar", "x": part["system"], "y": part["count"], "name": s})
    fig3 = {"data": fig3_data, "layout": {"barmode": "stack", "title": "System Health", "paper_bgcolor": "white", "plot_bgcolor": "white"}}

    # Figure 4: Workload by team (rows per team over selected window)
    if fdf.empty:
        team_work = pd.DataFrame(columns=["team", "rows"])
    else:
        team_work = fdf.groupby("team").size().reset_index(name="rows")
    fig4 = {"data": [{"type": "bar", "x": team_work["team"], "y": team_work["rows"], "name": "Rows"}],
            "layout": {"title": "Workload by Team", "paper_bgcolor": "white", "plot_bgcolor": "white"}}

    # Developer table: return filtered rows
    table_rows = fdf.to_dict(orient="records")

    return kpi_rev, kpi_cost, kpi_profit, kpi_red, fig1, fig2, fig3, fig4, table_rows

# ====================================
# Export CSV
# ====================================
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

# ====================================
# Entrypoint
# ====================================
if __name__ == "__main__":
    # For production: use gunicorn with multiple workers, e.g.:
    # gunicorn app:server --workers 4 --threads 2 --timeout 120 --bind 0.0.0.0:8050
    app.run_server(host="0.0.0.0", port=int(os.getenv("PORT", "8050")), debug=os.getenv("DEBUG", "0") == "1")
