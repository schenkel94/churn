import dash
from dash import dcc, html, Input, Output, State
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os

# --- 1. CARREGAMENTO DE DADOS (OTIMIZADO) ---
curr_dir = os.path.dirname(__file__)

def load_data():
    try:
        # Carregamos apenas as colunas necessárias para poupar memória no Render
        cols_silver = ['id_cliente', 'data_assinatura', 'valor_mensalidade', 'score_sentimento_voc', 'categoria_principal_voc']
        cols_gold = ['id_cliente', 'probabilidade_churn', 'previsao_final']
        
        silver = pd.read_csv(os.path.join(curr_dir, "churn_silver_2025.csv"), usecols=cols_silver)
        gold = pd.read_csv(os.path.join(curr_dir, "churn_gold_2025.csv"), usecols=cols_gold)
        
        df = pd.merge(silver, gold, on="id_cliente")
        df = df.rename(columns={'categoria_principal_voc': 'principal_dor_cliente'})
        df['data_assinatura'] = pd.to_datetime(df['data_assinatura'])
        return df
    except Exception as e:
        print(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

df = load_data()

# Cálculos Globais para os Deltas
if not df.empty:
    GLOBAL_RISK = df['probabilidade_churn'].mean()
    GLOBAL_VOC = df['score_sentimento_voc'].mean()
else:
    GLOBAL_RISK = 0
    GLOBAL_VOC = 0

# --- 2. INICIALIZAÇÃO DO APP ---
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server # Necessário para o Gunicorn/Render

# --- 3. COMPONENTES DE INTERFACE ---

def create_metric_card(title, value, delta, icon):
    # Lógica de cor do Delta (Invertida para Risco)
    is_risk = "Risco" in title or "Alertas" in title
    color = "red" if (delta > 0 if is_risk else delta < 0) else "green"
    
    return dmc.Paper(
        p="md", withBorder=True,
        style={"backgroundColor": "#161B22", "borderColor": "#30363D", "borderRadius": "10px"},
        children=[
            dmc.Group(position="apart", children=[
                dmc.Text(title, size="sm", color="#8B949E", weight=500),
                DashIconify(icon=icon, width=20, color="#8B949E"),
            ]),
            dmc.Group(align="flex-end", spacing="xs", mt=10, children=[
                dmc.Text(value, size="xl", weight=700, color="white"),
                dmc.Badge(f"{delta:+.1f}%", color=color, variant="filled", size="sm") if delta != 0 else None
            ])
        ]
    )

# --- 4. LAYOUTS (LOGIN E DASHBOARD) ---

login_layout = dmc.Container(
    style={"height": "90vh", "display": "flex", "alignItems": "center", "justifyContent": "center"},
    children=[
        dmc.Paper(
            p="xl", withBorder=True,
            style={"backgroundColor": "#161B22", "borderColor": "#30363D", "width": 350},
            children=[
                dmc.Center(DashIconify(icon="mdi:shield-lock", width=40, color="#238636")),
                dmc.Title("Churn Dashboard", order=3, color="white", align="center", mt="md"),
                dmc.Text("Acesso Especialista - Mario Schenkel", size="xs", color="#8B949E", align="center", mb="xl"),
                dmc.TextInput(id="user-in", label="Usuário", placeholder="adm", mb="md"),
                dmc.PasswordInput(id="pass-in", label="Senha", placeholder="adm123", mb="xl"),
                dmc.Button("Entrar", id="login-btn", fullWidth=True, color="green"),
                html.Div(id="login-err", style={"marginTop": 10})
            ]
        )
    ]
)

def main_dashboard():
    return html.Div([
        # Header
        dmc.Header(height=60, p="md", style={"backgroundColor": "#161B22", "borderBottom": "1px solid #30363D"}, children=[
            dmc.Group(position="apart", children=[
                dmc.Group([
                    DashIconify(icon="mdi:chart-arc", width=25, color="#238636"),
                    dmc.Title("VoC Churn Dashboard", order=4, color="white"),
                ]),
                dmc.Text("Mario Schenkel | Data Specialist", size="xs", color="#8B949E")
            ])
        ]),

        dmc.Container(size="xl", pt="md", children=[
            # Filtros
            dmc.Paper(p="md", mb="md", withBorder=True, style={"backgroundColor": "#161B22", "borderColor": "#30363D"}, children=[
                dmc.SimpleGrid(cols=3, breakpoints=[{"maxWidth": "sm", "cols": 1}], children=[
                    dmc.MultiSelect(
                        id="dor-filter", label="Principal Dor do Cliente",
                        data=[{"label": i, "value": i} for i in df['principal_dor_cliente'].unique()] if not df.empty else [],
                        value=list(df['principal_dor_cliente'].unique()) if not df.empty else [],
                    ),
                    dmc.Select(
                        id="client-filter", label="Cliente Específico",
                        data=[{"label": "Todos", "value": "all"}] + [{"label": i, "value": i} for i in df['id_cliente'].unique()] if not df.empty else [],
                        value="all", searchable=True
                    ),
                    dmc.RangeSlider(
                        id="risk-slider", label="Filtro de Risco",
                        min=0, max=1, step=0.1, value=[0, 1], color="red"
                    )
                ])
            ]),

            # Cards de Métricas
            html.Div(id="metric-cards-container"),

            dmc.Space(h="md"),

            # Gráficos
            dmc.Grid(children=[
                dmc.Col(span=4, children=[
                    dmc.Paper(p="md", withBorder=True, style={"backgroundColor": "#161B22", "borderColor": "#30363D"}, children=[
                        dmc.Text("Risco Médio (Velocímetro)", size="sm", color="#8B949E", mb="sm"),
                        dcc.Graph(id="gauge-chart", config={'displayModeBar': False}, style={"height": "250px"})
                    ])
                ]),
                dmc.Col(span=8, children=[
                    dmc.Paper(p="md", withBorder=True, style={"backgroundColor": "#161B22", "borderColor": "#30363D"}, children=[
                        dmc.Text("Risco vs Sentimento", size="sm", color="#8B949E", mb="sm"),
                        dcc.Graph(id="scatter-chart", config={'displayModeBar': False}, style={"height": "250px"})
                    ])
                ])
            ]),

            dmc.Space(h="md"),

            # Tabela Top 10
            dmc.Paper(p="md", withBorder=True, style={"backgroundColor": "#161B22", "borderColor": "#30363D"}, children=[
                dmc.Text("⚡ Top 10 Prioritários", size="sm", color="white", mb="sm"),
                html.Div(id="top-10-table")
            ]),
            
            dmc.Space(h="xl"),
        ]),
        
        # Footer
        html.Footer(style={"textAlign": "center", "padding": "20px", "color": "#8B949E", "fontSize": "12px"}, children=[
            dmc.Text("© 2026 | Mario Schenkel - Data Specialist")
        ])
    ])

# --- 5. APP LAYOUT PRINCIPAL ---
app.layout = dmc.MantineProvider(
    theme={"colorScheme": "dark"},
    children=[
        dcc.Location(id="url", refresh=False),
        html.Div(id="page-content", children=login_layout)
    ]
)

# --- 6. CALLBACKS ---

@app.callback(
    Output("page-content", "children"),
    Output("login-err", "children"),
    Input("login-btn", "n_clicks"),
    State("user-in", "value"),
    State("pass-in", "value")
)
def handle_login(n, user, pw):
    if n is None: return login_layout, ""
    if user == "adm" and pw == "adm123":
        return main_dashboard(), ""
    return login_layout, dmc.Alert("Senha incorreta", color="red", mt="sm")

@app.callback(
    [Output("metric-cards-container", "children"),
     Output("gauge-chart", "figure"),
     Output("scatter-chart", "figure"),
     Output("top-10-table", "children")],
    [Input("dor-filter", "value"),
     Input("client-filter", "value"),
     Input("risk-slider", "value")]
)
def update_dash(dor, client, risk):
    if df.empty: return "", go.Figure(), go.Figure(), ""

    # Filtros
    dff = df[df['principal_dor_cliente'].isin(dor)]
    dff = dff[(dff['probabilidade_churn'] >= risk[0]) & (dff['probabilidade_churn'] <= risk[1])]
    if client != "all": dff = dff[dff['id_cliente'] == client]

    # Métricas
    avg_risk = dff['probabilidade_churn'].mean() or 0
    delta_risk = ((avg_risk - GLOBAL_RISK) / GLOBAL_RISK * 100) if GLOBAL_RISK != 0 else 0
    
    avg_voc = dff['score_sentimento_voc'].mean() or 0
    delta_voc = ((avg_voc - GLOBAL_VOC) / GLOBAL_VOC * 100) if GLOBAL_VOC != 0 else 0

    cards = dmc.SimpleGrid(cols=4, breakpoints=[{"maxWidth": "md", "cols": 2}], children=[
        create_metric_card("Clientes", f"{len(dff)}", 0, "mdi:account-group"),
        create_metric_card("Risco Médio", f"{avg_risk*100:.1f}%", delta_risk, "mdi:alert"),
        create_metric_card("Score VoC", f"{avg_voc:.2f}", delta_voc, "mdi:message-text"),
        create_metric_card("Alertas Churn", f"{len(dff[dff['previsao_final']==1])}", 0, "mdi:bell-ring"),
    ])

    # Gauge
    fig_g = go.Figure(go.Indicator(
        mode="gauge+number", value=avg_risk*100,
        number={'suffix': "%", 'font': {'size': 40, 'color': 'white'}},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#238636"}, 
               'steps': [{'range': [70, 100], 'color': "#8b1a1a"}]}
    ))
    fig_g.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, height=200, margin=dict(t=0, b=0, l=10, r=10))

    # Scatter
    fig_s = px.scatter(dff, x="score_sentimento_voc", y="probabilidade_churn", color="principal_dor_cliente", size="valor_mensalidade", template="plotly_dark")
    fig_s.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=10, b=10))

    # Tabela
    top10 = dff.sort_values("probabilidade_churn", ascending=False).head(10)
    table = dmc.Table([
        html.Thead(html.Tr([html.Th("ID"), html.Th("Dor"), html.Th("Valor"), html.Th("Risco")])),
        html.Tbody([html.Tr([
            html.Td(r['id_cliente']), html.Td(r['principal_dor_cliente']), 
            html.Td(f"R$ {r['valor_mensalidade']}"), 
            html.Td(f"{r['probabilidade_churn']*100:.1f}%", style={"color": "red" if r['probabilidade_churn'] > 0.5 else "white"})
        ]) for _, r in top10.iterrows()])
    ])

    return cards, fig_g, fig_s, table

if __name__ == "__main__":
    app.run_server(debug=False)
