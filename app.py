import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os

# Isso garante que o Python encontre os CSVs na pasta do servidor
curr_dir = os.path.dirname(__file__)

try:
    # Carregando os dados com caminhos absolutos
    silver_path = os.path.join(curr_dir, "churn_silver_2025.csv")
    gold_path = os.path.join(curr_dir, "churn_gold_2025.csv")
    
    silver = pd.read_csv(silver_path)
    gold = pd.read_csv(gold_path)
    
    # Merge e tratamento de nomes (sua regra de negócio: Dor do Cliente)
    df = pd.merge(silver, gold, on="id_cliente").rename(
        columns={'categoria_principal_voc': 'principal_dor_cliente'}
    )
    df['data_assinatura'] = pd.to_datetime(df['data_assinatura'])

    # Médias Globais para os cálculos de comparação (Deltas)
    GLOBAL_RISK = df['probabilidade_churn'].mean()
    GLOBAL_VOC = df['score_sentimento_voc'].mean()
    GLOBAL_VAL = df['valor_mensalidade'].mean()

except Exception as e:
    print(f"Erro ao carregar arquivos: {e}")
    # Criamos um DF vazio para o app não crashar no build se o arquivo sumir
    df = pd.DataFrame()
    GLOBAL_RISK = 0
    GLOBAL_VOC = 0
    GLOBAL_VAL = 0

# --- INICIALIZAÇÃO DO APP ---
app = dash.Dash(__name__)
server = app.server # O Render usa isso aqui!

# --- COMPONENTES DE UI ---

def create_metric_card(title, value, delta, icon):
    color = "green" if delta >= 0 else "red"
    if "Risco" in title: color = "red" if delta > 0 else "green" # Inverter para risco
    
    return dmc.Paper(
        p="md", withBorder=True, shadow="xs",
        style={"backgroundColor": "#161B22", "borderColor": "#30363D"},
        children=[
            dmc.Group(position="apart", children=[
                dmc.Text(title, size="sm", color="#8B949E", weight=500),
                DashIconify(icon=icon, width=20, color="#8B949E"),
            ]),
            dmc.Group(align="flex-end", spacing="xs", mt=10, children=[
                dmc.Text(value, size="xl", weight=700, color="white"),
                dmc.Badge(f"{delta:+.1f}%", color=color, variant="filled", size="sm")
            ])
        ]
    )

# --- LAYOUT DE LOGIN ---
login_layout = dmc.Container(
    style={"height": "100vh", "display": "flex", "alignItems": "center", "justifyContent": "center"},
    children=[
        dmc.Paper(
            p="xl", withBorder=True, shadow="xl",
            style={"backgroundColor": "#161B22", "borderColor": "#30363D", "width": 400},
            children=[
                dmc.Center(DashIconify(icon="mdi:shield-lock", width=50, color="#238636")),
                dmc.Title("Churn Dashboard", order=2, color="white", align="center", mt="md"),
                dmc.Text("Área Restrita - Mario Schenkel Data Specialist", size="xs", color="#8B949E", align="center", mb="xl"),
                dmc.TextInput(id="user-in", label="Usuário", placeholder="adm", mb="md"),
                dmc.PasswordInput(id="pass-in", label="Senha", placeholder="adm123", mb="xl"),
                dmc.Button("Entrar no Painel", id="login-btn", fullWidth=True, color="green", size="md"),
                html.Div(id="login-err", style={"marginTop": 15})
            ]
        )
    ]
)

# --- LAYOUT DO DASHBOARD ---
def main_dashboard():
    return html.Div(style={"backgroundColor": "#0D1117", "minHeight": "100vh"}, children=[
        # Header Superior
        dmc.Header(height=70, p="md", style={"backgroundColor": "#161B22", "borderBottom": "1px solid #30363D"}, children=[
            dmc.Group(position="apart", children=[
                dmc.Group(children=[
                    DashIconify(icon="mdi:chart-arc", width=30, color="#238636"),
                    dmc.Title("VoC Churn Dashboard", order=3, color="white"),
                ]),
                dmc.Badge("Live Data 2026", color="gray", variant="outline")
            ])
        ]),

        dmc.Container(size="xl", pt="xl", children=[
            # Filtros em Linha (Estilo Profissional)
            dmc.Paper(p="md", mb="xl", withBorder=True, style={"backgroundColor": "#161B22", "borderColor": "#30363D"}, children=[
                dmc.SimpleGrid(cols=3, breakpoints=[{"maxWidth": "sm", "cols": 1}], children=[
                    dmc.MultiSelect(
                        id="dor-filter", label="Principal Dor do Cliente",
                        data=[{"label": i, "value": i} for i in df['principal_dor_cliente'].unique()],
                        value=list(df['principal_dor_cliente'].unique()),
                    ),
                    dmc.Select(
                        id="client-filter", label="Filtrar por ID do Cliente",
                        data=[{"label": "Todos", "value": "all"}] + [{"label": i, "value": i} for i in df['id_cliente'].unique()],
                        value="all", searchable=True
                    ),
                    dmc.RangeSlider(
                        id="risk-slider", label="Faixa de Risco (Modelo)",
                        min=0, max=1, step=0.1, value=[0, 1], color="red", mt="xl"
                    )
                ])
            ]),

            # Cards de Métricas
            html.Div(id="metric-cards-container"),

            dmc.Space(h="xl"),

            # Gráficos Principais
            dmc.Grid(children=[
                dmc.Col(span=4, children=[
                    dmc.Paper(p="md", withBorder=True, style={"backgroundColor": "#161B22", "borderColor": "#30363D"}, children=[
                        dmc.Text("Velocímetro de Risco Médio", size="sm", color="#8B949E", mb="md", weight=500),
                        dcc.Graph(id="gauge-chart", config={'displayModeBar': False})
                    ])
                ]),
                dmc.Col(span=8, children=[
                    dmc.Paper(p="md", withBorder=True, style={"backgroundColor": "#161B22", "borderColor": "#30363D"}, children=[
                        dmc.Text("Correlação: Valor vs Sentimento (Tamanho = Risco)", size="sm", color="#8B949E", mb="md", weight=500),
                        dcc.Graph(id="scatter-chart", config={'displayModeBar': False})
                    ])
                ])
            ]),

            dmc.Space(h="xl"),

            # Top 10 Tabela
            dmc.Paper(p="md", withBorder=True, mb="xl", style={"backgroundColor": "#161B22", "borderColor": "#30363D"}, children=[
                dmc.Text("⚡ Top 10 Clientes Prioritários para Retenção", size="md", color="white", mb="md", weight=600),
                html.Div(id="top-10-table")
            ]),
        ]),

        # Rodapé Customizado
        html.Footer(style={"textAlign": "center", "padding": "40px", "color": "#8B949E", "borderTop": "1px solid #30363D", "backgroundColor": "#0D1117"}, children=[
            dmc.Text("© 2026 | Mario Schenkel - Data Specialist", size="sm")
        ])
    ])

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content")
])

# --- CALLBACKS (Lógica de Negócio) ---

@app.callback(
    Output("page-content", "children"),
    Output("login-err", "children"),
    Input("login-btn", "n_clicks"),
    State("user-in", "value"),
    State("pass-in", "value")
)
def handle_login(n_clicks, user, pw):
    if n_clicks is None: return login_layout, ""
    if user == "adm" and pw == "adm123":
        return main_dashboard(), ""
    return login_layout, dmc.Alert("Credenciais inválidas!", color="red")

@app.callback(
    Output("metric-cards-container", "children"),
    Output("gauge-chart", "figure"),
    Output("scatter-chart", "figure"),
    Output("top-10-table", "children"),
    Input("dor-filter", "value"),
    Input("client-filter", "value"),
    Input("risk-slider", "value")
)
def update_dashboard(dor, client, risk_range):
    # Filtragem
    dff = df[df['principal_dor_cliente'].isin(dor)]
    dff = dff[(dff['probabilidade_churn'] >= risk_range[0]) & (dff['probabilidade_churn'] <= risk_range[1])]
    if client != "all": dff = dff[dff['id_cliente'] == client]

    # Cálculos Métricas
    avg_risk = dff['probabilidade_churn'].mean() or 0
    delta_risk = ((avg_risk - GLOBAL_RISK) / GLOBAL_RISK) * 100
    
    avg_voc = dff['score_sentimento_voc'].mean() or 0
    delta_voc = ((avg_voc - GLOBAL_VOC) / GLOBAL_VOC) * 100

    # Grid de Cards
    cards = dmc.SimpleGrid(cols=4, breakpoints=[{"maxWidth": "md", "cols": 2}], children=[
        create_metric_card("Base Filtrada", f"{len(dff)}", 0, "mdi:account-group"),
        create_metric_card("Risco Médio", f"{avg_risk*100:.1f}%", delta_risk, "mdi:alert-octagon"),
        create_metric_card("Sentimento VoC", f"{avg_voc:.2f}", delta_voc, "mdi:emoticon-happy"),
        create_metric_card("Receita em Risco", f"R$ {dff[dff['previsao_final']==1]['valor_mensalidade'].sum():,.0f}", 0, "mdi:cash-multiple"),
    ])

    # Gráfico Gauge
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = avg_risk * 100,
        number = {'suffix': "%", 'font': {'color': 'white'}},
        gauge = {
            'axis': {'range': [None, 100], 'tickcolor': "#8B949E"},
            'bar': {'color': "#238636"},
            'bgcolor': "#161B22",
            'steps': [
                {'range': [0, 40], 'color': "#1e3a22"},
                {'range': [40, 70], 'color': "#b38600"},
                {'range': [70, 100], 'color': "#8b1a1a"}
            ],
        }
    ))
    fig_gauge.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=220, margin=dict(t=0, b=0, l=20, r=20))

    # Gráfico Scatter
    fig_scatter = px.scatter(
        dff, x="score_sentimento_voc", y="probabilidade_churn",
        size="valor_mensalidade", color="principal_dor_cliente",
        hover_name="id_cliente", template="plotly_dark",
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    fig_scatter.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title="Score de Sentimento", gridcolor="#30363D"),
        yaxis=dict(title="Probabilidade Churn", gridcolor="#30363D"),
        legend=dict(bgcolor="rgba(0,0,0,0)")
    )

    # Tabela Top 10
    top10 = dff.sort_values("probabilidade_churn", ascending=False).head(10)
    table = dmc.Table(
        striped=True, highlightOnHover=True, verticalSpacing="sm",
        children=[
            html.Thead(html.Tr([
                html.Th("ID Cliente", style={"color": "#8B949E"}),
                html.Th("Principal Dor", style={"color": "#8B949E"}),
                html.Th("Valor", style={"color": "#8B949E"}),
                html.Th("Sentimento", style={"color": "#8B949E"}),
                html.Th("Prob. Churn", style={"color": "#8B949E"})
            ])),
            html.Tbody([
                html.Tr([
                    html.Td(row['id_cliente'], style={"color": "white"}),
                    html.Td(dmc.Badge(row['principal_dor_cliente'], variant="outline", color="gray")),
                    html.Td(f"R$ {row['valor_mensalidade']}"),
                    html.Td(row['score_sentimento_voc']),
                    html.Td(dmc.Text(f"{row['probabilidade_churn']*100:.1f}%", color="red", weight=700 if row['probabilidade_churn'] > 0.7 else 400))
                ]) for _, row in top10.iterrows()
            ])
        ]
    )

    return cards, fig_gauge, fig_scatter, table

if __name__ == "__main__":
    app.run_server(debug=False)
