import dash
from dash import dcc, html, Input, Output, dash_table
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import MarkerCluster
import plotly.express as px


# Cargar datos
colombia_geo = gpd.read_file('https://raw.githubusercontent.com/lihkir/Uninorte/main/AppliedStatisticMS/DataVisualizationRPython/Lectures/Python/PythonDataSets/Colombia.geo.json')
data = pd.read_csv("PreciosGasNaturalVehicula.csv")

# Convertir fechas
data['FECHA_PRECIO'] = pd.to_datetime(data['FECHA_PRECIO'])
data['AÑO'] = data['FECHA_PRECIO'].dt.year

# Inicializar la app
app = dash.Dash(__name__, external_stylesheets=['https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css'])
server = app.server


app.layout = html.Div([
    dcc.Tabs([
        dcc.Tab(label="Contexto", children=[
            html.Div([
                html.H3("Contextualización"),
                html.P(
                    "Los datos de este proyecto han sido extraídos del Sistema de Información de Combustibles (SICOM) y "
                    "publicados en el portal de datos abiertos del Gobierno de Colombia. Esta información abarca el período "
                    "comprendido entre 2021 y 2025, permitiendo realizar un análisis detallado de los precios promedio del "
                    "Gas Natural Comprimido Vehicular (GNCV) a nivel municipal y departamental en Colombia."
                ),
                html.H3("Sobre los datos"),
                html.P(
                    "El conjunto de datos proporciona información actualizada y detallada sobre los precios promedio del "
                    "Gas Natural Comprimido Vehicular (GNCV) en diferentes estaciones de servicio (EDS) de Colombia. "
                    "Esta base de datos es una herramienta clave para monitorear el comportamiento del mercado del GNCV en "
                    "el país, permitiendo evaluar las variaciones de precios a lo largo del tiempo y entre diferentes regiones."
                ),
                html.Ul([
                    html.Li("Fecha del Precio: Día, mes y año de publicación del precio promedio."),
                    html.Li("Departamento y Municipio: Ubicación geográfica de la estación de servicio (EDS)."),
                    html.Li("Nombre Comercial de la EDS: Identificación del establecimiento que suministra GNCV."),
                    html.Li("Precio Promedio Publicado: Valor promedio en pesos colombianos ($COP/m³) para el GNCV."),
                    html.Li("Tipo de Combustible: En este caso, GNCV."),
                    html.Li("Código DANE del Municipio: Código oficial del municipio según el DANE."),
                    html.Li("Coordenadas Geográficas: Latitud y longitud de la EDS, lo que facilita el análisis espacial."),
                ])
            ], style={'padding': '20px'})
        ]),
        
        dcc.Tab(label="Mapa Coroplético", children=[
            html.Div([
                dcc.Dropdown(
                    id="year-dropdown",
                    options=[{'label': str(y), 'value': y} for y in sorted(data['AÑO'].unique())],
                    value=data['AÑO'].min(),
                    clearable=False
                ),
                html.Iframe(id="mapa", width="100%", height="600px")
            ])
        ]),

        dcc.Tab(label="Evolución Temporal", children=[
            html.Div([
                dcc.Dropdown(
                    id="departamento-dropdown",
                    options=[{'label': d, 'value': d} for d in sorted(data['DEPARTAMENTO_EDS'].unique())],
                    value=data['DEPARTAMENTO_EDS'].iloc[0],
                    clearable=False
                ),
                dcc.Graph(id="evolucion-plot")
            ])
        ]),

        dcc.Tab(label="Datos", children=[
            html.Div([
                dcc.Input(
                    id="search-input",
                    type="text",
                    placeholder="Buscar...",
                    debounce=True, 
                    style={'margin-bottom': '10px', 'width': '100%', 'padding': '10px'}
                ),
                dash_table.DataTable(
                    id='tabla-datos',
                    columns=[{"name": i, "id": i} for i in data.columns],
                    data=data.to_dict('records'),
                    page_size=10,
                    filter_action="native",  
                    sort_action="native",  
                    style_table={'overflowX': 'auto'}
                )
            ])
        ])

    ])
])

@app.callback(
    Output("mapa", "srcDoc"),
    Input("year-dropdown", "value")
)
def update_map(selected_year):
    df_filtered = data[data["AÑO"] == selected_year].groupby("DEPARTAMENTO_EDS", as_index=False).agg({"PRECIO_PROMEDIO_PUBLICADO": "mean"})
    merged_data = colombia_geo.merge(df_filtered, left_on="NOMBRE_DPT", right_on="DEPARTAMENTO_EDS", how="left")

    m = folium.Map(location=[4, -72], zoom_start=5)

    choropleth = folium.Choropleth(
        geo_data=merged_data,
        name="choropleth",
        data=merged_data,
        columns=["NOMBRE_DPT", "PRECIO_PROMEDIO_PUBLICADO"],
        key_on="feature.properties.NOMBRE_DPT",
        fill_color="YlGnBu",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name="Precio Promedio GNCV"
    ).add_to(m)

    for _, row in merged_data.iterrows():
        precio = round(row["PRECIO_PROMEDIO_PUBLICADO"], 2) if pd.notna(row["PRECIO_PROMEDIO_PUBLICADO"]) else "No disponible"
        popup_text = f"<b>{row['NOMBRE_DPT']}</b><br>Precio Promedio: {precio}"
        folium.GeoJson(
            data=row["geometry"],
            name=row["NOMBRE_DPT"],
            style_function=lambda x: {"fillColor": "transparent", "color": "black", "weight": 1},
            highlight_function=lambda x: {"fillColor": "#ffaf00", "color": "red", "weight": 2, "fillOpacity": 0.5},
            tooltip=popup_text
        ).add_to(m)

    return m._repr_html_()


@app.callback(
    Output("evolucion-plot", "figure"),
    Input("departamento-dropdown", "value")
)
def update_evolucion(departamento):
    df_filtered = data[data["DEPARTAMENTO_EDS"] == departamento].groupby(["FECHA_PRECIO", "MUNICIPIO_EDS"], as_index=False)["PRECIO_PROMEDIO_PUBLICADO"].mean()
    fig = px.line(df_filtered, x="FECHA_PRECIO", y="PRECIO_PROMEDIO_PUBLICADO", color="MUNICIPIO_EDS",
                  title=f"Evolución del Precio Promedio en {departamento}",
                  labels={"FECHA_PRECIO": "Fecha", "PRECIO_PROMEDIO_PUBLICADO": "Precio Promedio"})
    return fig

if __name__ == "__main__":
    app.run(debug=True)

