import os
from functools import lru_cache

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html
from flask import Flask, redirect, render_template_string, request, session, url_for


PRIMARY_PAIN_LABEL = "Principal Dor do Cliente"
BACKGROUND = "#0D1117"
CARD = "#161B22"
BORDER = "#30363D"
TEXT = "#E6EDF3"
MUTED = "#8B949E"
SUCCESS = "#2EA043"
WARNING = "#D29922"
DANGER = "#F85149"
ACCENT = "#58A6FF"


LOGIN_TEMPLATE = """
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>VoC Churn Dashboard | Login</title>
    <style>
      :root {
        color-scheme: dark;
        --bg: #0d1117;
        --bg-soft: #161b22;
        --border: #30363d;
        --text: #e6edf3;
        --muted: #8b949e;
        --accent: #58a6ff;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 24px;
        background:
          radial-gradient(circle at top left, rgba(88,166,255,0.16), transparent 30%),
          radial-gradient(circle at bottom right, rgba(248,81,73,0.12), transparent 24%),
          linear-gradient(135deg, #0d1117 0%, #111827 45%, #0d1117 100%);
        color: var(--text);
        font-family: Inter, "Segoe UI", Roboto, Arial, sans-serif;
      }
      .login-shell {
        width: min(100%, 430px);
        padding: 32px;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 24px;
        background: rgba(22, 27, 34, 0.9);
        backdrop-filter: blur(16px);
        box-shadow: 0 30px 80px rgba(0, 0, 0, 0.35);
      }
      .eyebrow {
        display: inline-flex;
        gap: 8px;
        padding: 8px 12px;
        border-radius: 999px;
        background: rgba(88, 166, 255, 0.12);
        color: #9cc5ff;
        font-size: 12px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }
      h1 { margin: 20px 0 8px; font-size: 32px; line-height: 1.05; }
      p { margin: 0 0 24px; color: var(--muted); line-height: 1.6; }
      form { display: grid; gap: 16px; }
      label { display: grid; gap: 8px; font-size: 14px; color: #c9d1d9; }
      input {
        width: 100%;
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 14px 16px;
        background: rgba(13, 17, 23, 0.9);
        color: var(--text);
        outline: none;
      }
      input:focus {
        border-color: var(--accent);
        box-shadow: 0 0 0 4px rgba(88, 166, 255, 0.16);
      }
      button {
        border: 0;
        border-radius: 14px;
        padding: 14px 16px;
        font-size: 15px;
        font-weight: 600;
        color: white;
        background: linear-gradient(135deg, #1f6feb, #58a6ff);
        cursor: pointer;
      }
      .hint {
        margin-top: 18px;
        padding: 12px 14px;
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,0.06);
        background: rgba(13, 17, 23, 0.7);
        color: var(--muted);
        font-size: 13px;
      }
      .error {
        margin: 0 0 16px;
        border: 1px solid rgba(248,81,73,0.35);
        background: rgba(248,81,73,0.1);
        color: #ffb3ad;
        border-radius: 14px;
        padding: 12px 14px;
        font-size: 14px;
      }
    </style>
  </head>
  <body>
    <section class="login-shell">
      <div class="eyebrow">Premium Dark SaaS</div>
      <h1>VoC Churn Dashboard</h1>
      <p>Análise preditiva de retenção baseada na dor do cliente, com foco em priorização comercial e clareza executiva.</p>
      {% if error %}
      <div class="error">{{ error }}</div>
      {% endif %}
      <form method="post">
        <label>
          Usuário
          <input type="text" name="username" autocomplete="username" required>
        </label>
        <label>
          Senha
          <input type="password" name="password" autocomplete="current-password" required>
        </label>
        <button type="submit">Entrar no Dashboard</button>
      </form>
      <div class="hint">Acesso padrão: <strong>adm</strong> / <strong>adm123</strong></div>
    </section>
  </body>
</html>
"""


server = Flask(__name__)
server.secret_key = os.getenv("SECRET_KEY", "voc-churn-dashboard-secret")


@lru_cache(maxsize=1)
def load_data() -> pd.DataFrame:
    silver = pd.read_csv("churn_silver_2025.csv")
    gold = pd.read_csv("churn_gold_2025.csv")
    merged = silver.merge(gold, on="id_cliente", how="inner")
    merged = merged.rename(columns={"categoria_principal_voc": PRIMARY_PAIN_LABEL})
    merged["data_assinatura"] = pd.to_datetime(merged["data_assinatura"], errors="coerce")
    merged["probabilidade_churn"] = merged["probabilidade_churn"].astype(float)
    merged["valor_mensalidade"] = merged["valor_mensalidade"].astype(float)
    merged["score_sentimento_voc"] = merged["score_sentimento_voc"].astype(float)
    merged["previsao_final"] = merged["previsao_final"].astype(int)
    return merged


def compute_delta(current: float, baseline: float) -> str:
    if baseline == 0:
        return "0% vs média da base"
    delta = ((current - baseline) / baseline) * 100
    prefix = "+" if delta >= 0 else ""
    return f"{prefix}{delta:.1f}% vs média da base"


def format_currency(value: float) -> str:
    formatted = f"{value:,.2f}"
    return f"R$ {formatted}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def risk_color(value: float) -> str:
    if value < 0.4:
        return SUCCESS
    if value < 0.7:
        return WARNING
    return DANGER


def build_gauge(value: float) -> go.Figure:
    figure = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=max(0, min(value * 100, 100)),
            number={"suffix": "%", "font": {"size": 42, "color": TEXT}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": MUTED, "tickfont": {"color": MUTED}},
                "bar": {"color": "#E6EDF3", "thickness": 0.24},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 40], "color": "rgba(46, 160, 67, 0.85)"},
                    {"range": [40, 70], "color": "rgba(210, 153, 34, 0.9)"},
                    {"range": [70, 100], "color": "rgba(248, 81, 73, 0.9)"},
                ],
                "threshold": {
                    "line": {"color": ACCENT, "width": 4},
                    "thickness": 0.85,
                    "value": max(0, min(value * 100, 100)),
                },
            },
        )
    )
    figure.update_layout(
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        margin=dict(l=24, r=24, t=32, b=20),
        font=dict(color=TEXT, family="Inter, Segoe UI, sans-serif"),
        height=350,
    )
    return figure


def build_scatter(dataframe: pd.DataFrame) -> go.Figure:
    if dataframe.empty:
        figure = go.Figure()
        figure.update_layout(
            paper_bgcolor=CARD,
            plot_bgcolor=CARD,
            font=dict(color=TEXT, family="Inter, Segoe UI, sans-serif"),
            xaxis={"visible": False},
            yaxis={"visible": False},
            annotations=[{"text": "Nenhum cliente encontrado com os filtros selecionados.", "xref": "paper", "yref": "paper", "showarrow": False, "font": {"size": 16, "color": MUTED}}],
            margin=dict(l=20, r=20, t=40, b=20),
            height=420,
        )
        return figure

    figure = px.scatter(
        dataframe,
        x="score_sentimento_voc",
        y="probabilidade_churn",
        size="valor_mensalidade",
        color=PRIMARY_PAIN_LABEL,
        hover_name="id_cliente",
        color_discrete_sequence=["#58A6FF", "#F778BA", "#2EA043", "#D29922", "#FF7B72", "#A371F7"],
    )
    customdata = dataframe[["id_cliente", "valor_mensalidade", PRIMARY_PAIN_LABEL]].to_numpy()
    figure.update_traces(
        marker={"opacity": 0.82, "line": {"width": 1, "color": "rgba(230,237,243,0.15)"}},
        customdata=customdata,
        hovertemplate=(
            "<b>ID Cliente:</b> %{customdata[0]}<br>"
            f"<b>{PRIMARY_PAIN_LABEL}:</b> " + "%{customdata[2]}<br>"
            "<b>Score VoC:</b> %{x:.3f}<br>"
            "<b>Prob. Churn:</b> %{y:.1%}<br>"
            "<b>Ticket Mensal:</b> R$ %{customdata[1]:,.2f}<br>"
            "<extra></extra>"
        ),
    )
    figure.update_layout(
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        font=dict(color=TEXT, family="Inter, Segoe UI, sans-serif"),
        margin=dict(l=24, r=24, t=24, b=24),
        height=420,
        legend_title_text=PRIMARY_PAIN_LABEL,
        xaxis_title="Score de Sentimento VoC",
        yaxis_title="Probabilidade de Churn",
    )
    figure.update_xaxes(gridcolor="rgba(139,148,158,0.12)", zeroline=False)
    figure.update_yaxes(gridcolor="rgba(139,148,158,0.12)", tickformat=".0%", zeroline=False)
    return figure


def build_kpi_card(title: str, value: str, delta: str, icon: str, tone: str) -> html.Div:
    return html.Div(
        className="kpi-card",
        children=[
            html.Div(className="kpi-topline", children=[html.Span(icon, className=f"kpi-icon tone-{tone}"), html.Span(title, className="kpi-title")]),
            html.Div(value, className="kpi-value"),
            html.Div(delta, className=f"kpi-delta tone-{tone}"),
        ],
    )


def build_risk_bar(probability: float) -> html.Div:
    color = risk_color(probability)
    return html.Div(
        className="risk-cell",
        children=[
            html.Div(className="risk-track", children=[html.Div(className="risk-fill", style={"width": f"{probability * 100:.1f}%", "background": color})]),
            html.Span(format_percent(probability), className="risk-label", style={"color": color}),
        ],
    )


def build_priority_table(dataframe: pd.DataFrame) -> html.Div:
    ordered = dataframe.sort_values("probabilidade_churn", ascending=False).head(10)
    if ordered.empty:
        return html.Div("Nenhum cliente elegível para priorização com os filtros atuais.", className="empty-state")

    header = html.Div(
        className="table-row table-header",
        children=[html.Div("ID Cliente"), html.Div("Principal Dor (VoC)"), html.Div("Ticket Mensal"), html.Div("Score Sentimento"), html.Div("Grau de Risco")],
    )
    rows = []
    for _, row in ordered.iterrows():
        rows.append(
            html.Div(
                className="table-row table-body-row",
                children=[
                    html.Div(row["id_cliente"], className="mono"),
                    html.Div(row[PRIMARY_PAIN_LABEL]),
                    html.Div(format_currency(row["valor_mensalidade"])),
                    html.Div(f'{row["score_sentimento_voc"]:.3f}'),
                    html.Div(build_risk_bar(row["probabilidade_churn"])),
                ],
            )
        )
    return html.Div(className="action-table", children=[header, *rows])


def filter_dataframe(pains, client_ids, risk_range):
    dataframe = load_data().copy()
    if pains:
        dataframe = dataframe[dataframe[PRIMARY_PAIN_LABEL].isin(pains)]
    if client_ids:
        dataframe = dataframe[dataframe["id_cliente"].isin(client_ids)]
    if risk_range:
        low, high = risk_range
        dataframe = dataframe[(dataframe["probabilidade_churn"] >= float(low)) & (dataframe["probabilidade_churn"] <= float(high))]
    return dataframe


@server.before_request
def require_login():
    path = request.path or "/"
    if path.startswith("/assets/") or path.startswith("/_favicon"):
        return None
    if path in {"/", "/login"}:
        if session.get("authenticated"):
            return redirect("/dashboard/")
        return None
    if path == "/logout":
        return None
    if path.startswith("/dashboard") and not session.get("authenticated"):
        return redirect(url_for("login"))
    return None


@server.route("/", methods=["GET", "POST"])
@server.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username == "adm" and password == "adm123":
            session["authenticated"] = True
            return redirect("/dashboard/")
        error = "Usuário ou senha inválidos."
    return render_template_string(LOGIN_TEMPLATE, error=error)


@server.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


app = Dash(__name__, server=server, routes_pathname_prefix="/dashboard/", suppress_callback_exceptions=True, title="VoC Churn Dashboard")


base_df = load_data()
pain_options = [{"label": value, "value": value} for value in sorted(base_df[PRIMARY_PAIN_LABEL].dropna().unique())]
client_options = [{"label": value, "value": value} for value in sorted(base_df["id_cliente"].dropna().unique())]


app.layout = html.Div(
    className="app-shell",
    children=[
        html.Div(className="page-glow page-glow-left"),
        html.Div(className="page-glow page-glow-right"),
        html.Div(
            className="main-container",
            children=[
                html.Header(
                    className="topbar glass-card",
                    children=[
                        html.Div(children=[html.Div("VoC Churn Dashboard", className="hero-title"), html.Div("Análise Preditiva de Retenção baseada na Dor do Cliente", className="hero-subtitle")]),
                        html.Div(className="topbar-actions", children=[html.Div(className="live-badge", children=[html.Span(className="live-dot"), html.Span("Live Data")]), html.A("Logout", href="/logout", className="logout-button")]),
                    ],
                ),
                html.Section(
                    className="filters-panel glass-card",
                    children=[
                        html.Div(className="section-title-wrap", children=[html.Div("Filtros Inteligentes", className="section-title"), html.Div("Refine a visão por dor do cliente, IDs específicos e faixa de risco.", className="section-subtitle")]),
                        html.Div(
                            className="filters-grid",
                            children=[
                                html.Div(className="filter-group", children=[html.Label(PRIMARY_PAIN_LABEL, className="filter-label"), dcc.Dropdown(id="pain-filter", options=pain_options, multi=True, placeholder="Selecione uma ou mais dores", className="premium-dropdown")]),
                                html.Div(className="filter-group", children=[html.Label("Filtrar por Cliente (ID)", className="filter-label"), dcc.Dropdown(id="client-filter", options=client_options, multi=True, placeholder="Busque clientes específicos", className="premium-dropdown")]),
                                html.Div(className="filter-group slider-group", children=[html.Label("Nível de Risco (Probabilidade)", className="filter-label"), dcc.RangeSlider(id="risk-filter", min=0, max=1, step=0.01, value=[0, 1], marks={0: {"label": "0.0"}, 0.25: {"label": "0.25"}, 0.5: {"label": "0.50"}, 0.75: {"label": "0.75"}, 1: {"label": "1.0"}}, tooltip={"always_visible": False, "placement": "bottom"}, allowCross=False)]),
                            ],
                        ),
                    ],
                ),
                html.Div(id="kpi-row", className="kpi-grid"),
                html.Section(
                    className="viz-grid",
                    children=[
                        html.Div(className="viz-card glass-card", children=[html.Div("Velocímetro de Risco", className="section-title"), html.Div("Probabilidade média de churn na base filtrada.", className="section-subtitle"), dcc.Graph(id="gauge-chart", config={"displayModeBar": False})]),
                        html.Div(className="viz-card glass-card", children=[html.Div("Mapa de Dispersão VoC x Churn", className="section-title"), html.Div("Explore ticket, sentimento e risco em uma única leitura.", className="section-subtitle"), dcc.Graph(id="scatter-chart", config={"displayModeBar": False})]),
                    ],
                ),
                html.Section(className="table-card glass-card", children=[html.Div("📋 Top 10 Clientes Prioritários para Ação de Retenção", className="section-title"), html.Div("Ordenado automaticamente pelos maiores níveis de risco para facilitar a atuação imediata.", className="section-subtitle"), html.Div(id="priority-table")]),
                html.Footer("Mario Schenkel - Data Specialist", className="footer-note"),
            ],
        ),
    ],
)


@app.callback(
    Output("kpi-row", "children"),
    Output("gauge-chart", "figure"),
    Output("scatter-chart", "figure"),
    Output("priority-table", "children"),
    Input("pain-filter", "value"),
    Input("client-filter", "value"),
    Input("risk-filter", "value"),
)
def update_dashboard(selected_pains, selected_clients, selected_risk):
    filtered = filter_dataframe(selected_pains, selected_clients, selected_risk)
    baseline = load_data()
    total_clients = int(filtered["id_cliente"].nunique())
    base_clients = int(baseline["id_cliente"].nunique())
    filtered_alerts = int((filtered["previsao_final"] == 1).sum())
    base_alerts = int((baseline["previsao_final"] == 1).sum())
    filtered_ticket = float(filtered["valor_mensalidade"].mean()) if not filtered.empty else 0
    base_ticket = float(baseline["valor_mensalidade"].mean())
    filtered_voc = float(filtered["score_sentimento_voc"].mean()) if not filtered.empty else 0
    base_voc = float(baseline["score_sentimento_voc"].mean())

    kpis = [
        build_kpi_card("Total Clientes Analisados", f"{total_clients:,}".replace(",", "."), compute_delta(total_clients, base_clients), "◉", "info"),
        build_kpi_card("Alertas de Churn (Previsão)", f"{filtered_alerts:,}".replace(",", "."), compute_delta(filtered_alerts, base_alerts), "▲", "danger"),
        build_kpi_card("Ticket Médio Mensal", format_currency(filtered_ticket), compute_delta(filtered_ticket, base_ticket), "R$", "success"),
        build_kpi_card("Score VoC Médio", f"{filtered_voc:.3f}", compute_delta(filtered_voc, base_voc), "∞", "info"),
    ]

    gauge_value = float(filtered["probabilidade_churn"].mean()) if not filtered.empty else 0
    return kpis, build_gauge(gauge_value), build_scatter(filtered), build_priority_table(filtered)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", "8050")))
