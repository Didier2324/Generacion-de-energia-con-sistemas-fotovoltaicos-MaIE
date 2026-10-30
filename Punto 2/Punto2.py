import pandas as pd

from pathlib import Path
import plotly.io as pio
import plotly.graph_objects as go
carpeta = Path(__file__).parent
# ===================== ESTILO DE LAS GRÁFICAS =====================
FUENTE        = "Times New Roman"
TAM_TEXTO     = 14        # ticks, leyenda, texto general
TAM_TITULO    = 22
TAM_EJES      = 16        # títulos de los ejes
GROSOR_LINEA  = 2
COLOR_GRILLA  = "#E0E0E0"
PALETA = ["#003B6D",  # azul oscuro → NSRDB
          "#FF9B49",  # naranja → Solcast
          "#2CA02C",  # verde
          "#D62728",  # rojo
          "#9467BD",  # morado
          "#8C564B"]  # café
ANCHO, ALTO   = 1400, 600

pio.templates["sfv"] = go.layout.Template(
    layout=dict(
        font=dict(family=FUENTE, size=TAM_TEXTO, color="#222"),
        title=dict(font=dict(size=TAM_TITULO), x=0.5),        # título centrado
        colorway=PALETA,
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(title_font=dict(size=TAM_EJES), showgrid=True,
                   gridcolor=COLOR_GRILLA, showline=True, linecolor="#444",
                   mirror=True, ticks="outside"),
        yaxis=dict(title_font=dict(size=TAM_EJES), showgrid=True,
                   gridcolor=COLOR_GRILLA, showline=True, linecolor="#444",
                   mirror=True, ticks="outside", zeroline=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
        hovermode="x unified",
        margin=dict(l=70, r=30, t=80, b=60),
    ),
    data=dict(scatter=[go.Scatter(line=dict(width=GROSOR_LINEA))]),
)
pio.templates.default = "sfv"
pio.renderers.default = "browser"


def guardar(fig, nombre, ancho=ANCHO, alto=ALTO):
    """Guarda la figura en HTML y PNG y la muestra."""
    fig.write_html(carpeta / f"{nombre}.html")
    fig.write_image(carpeta / f"{nombre}.png", width=ancho, height=alto, scale=2)
    fig.show()
# ==================================================================





# Lectura de datos de NSRDB
cols = ["Year", "Month", "Day", "Hour", "Minute"]
def leer(año):
    df = pd.read_csv(f"NSRDB_{año}.csv", skiprows=2)
    df["Fecha"] = pd.to_datetime(df[cols])
    return df.set_index("Fecha").drop(columns=cols)

df_NSRDB = pd.concat([leer(a) for a in [2023, 2024, 2025]]).sort_index()

# lectura y ajuste horario Solcast
df_Solcast = pd.read_csv("solcastCSV_2023_2025.csv")
df_Solcast["Fecha"] = pd.to_datetime(df_Solcast["period_end"]).dt.tz_convert("America/Bogota").dt.tz_localize(None)
df_Solcast = df_Solcast.set_index("Fecha").sort_index()

# Obtención de dias intersectados entre Solcast y NSRDB
dias = df_NSRDB.index.normalize().unique().intersection(df_Solcast.index.normalize().unique())
df_NSRDB = df_NSRDB[df_NSRDB.index.normalize().isin(dias)]
df_Solcast = df_Solcast[df_Solcast.index.normalize().isin(dias)]

# Filtrado por fecha 
inicio = pd.Timestamp("2023-01-01 00:00")
fin    = pd.Timestamp("2025-12-31 23:59")
df_NSRDB   = df_NSRDB.loc[inicio:fin]
df_Solcast = df_Solcast.loc[inicio:fin]


# Estandarización de nombres de variables
df_NSRDB = df_NSRDB.rename(columns={"Temperature": "Temperatura", "Surface Albedo": "Albedo", "Cloud Type":"Nubosidad",
                                    "Relative Humidity":"Humedad Relativa","Solar Zenith Angle":"Cenital", "SSA":"Azimutal"})

df_Solcast = df_Solcast.rename(columns={"air_temp": "Temperatura", "albedo": "Albedo", "cloud_opacity":"Nubosidad",
                                    "relative_humidity":"Humedad Relativa","zenith":"Cenital", "azimuth":"Azimutal",
                                    "dhi":"DHI", "ghi":"GHI", "dni":"DNI","gti":"GTI"})



# Histograma comparativo de albedo
columna = "Albedo"
datos = pd.concat([df_NSRDB[columna], df_Solcast[columna]]).dropna()
n_bins = 50
xbins = dict(start=datos.min(), end=datos.max(),
             size=(datos.max() - datos.min()) / n_bins)

fig = go.Figure()
for df, nombre in [(df_NSRDB, "NSRDB"), (df_Solcast, "Solcast")]:
    fig.add_trace(go.Histogram(
        x=df[columna].dropna(), name=nombre, xbins=xbins,
        histnorm="percent", opacity=0.6,
        marker_line=dict(width=1, color="white"),
    ))

fig.update_layout(
    title=f"Distribución de {columna}: NSRDB vs Solcast",
    xaxis_title=columna,
    yaxis_title="Frecuencia (%)",
    barmode="overlay",
)

guardar(fig, f"histograma_{columna}",ancho=1400, alto=400)


#-----------------------------------------
# Potencia instalada :
P_nom = 650*2070
# Eficiencia global 
nG = 0.8248
# Factor de bifasialidad 
bF = 0.75
#----------------------------------------

# CALCULO DE LA POTENCIA GENERADA ESTIMADA
df_NSRDB["P. estimada"] = df_NSRDB["GHI"]*P_nom*(1+df_NSRDB["Albedo"]*bF)*nG/1000
df_Solcast["P. estimada"] = df_Solcast["GHI"]*P_nom*(1+df_Solcast["Albedo"]*bF)*nG/1000



# Gráfica de potencia estimada: NSRDB vs Solcast
fig = go.Figure()
for df, nombre in [(df_NSRDB, "NSRDB"), (df_Solcast, "Solcast")]:
    fig.add_trace(go.Scattergl(
        x=df.index, y=df["P. estimada"] / 1000,   # W → kW
        name=nombre, mode="lines",
        line=dict(width=GROSOR_LINEA),
    ))

fig.update_layout(
    title="Potencia estimada: NSRDB vs Solcast",
    xaxis_title="Fecha",
    yaxis_title="Potencia (kW)"
)

guardar(fig, "potencia_estimada_NSRDB_vs_Solcast")


# Gráfica de potencia estimada entre dos fechas determinadas
ini_periodo = pd.Timestamp("2024-08-01")
fin_periodo = pd.Timestamp("2024-08-07")

fin_incl = fin_periodo + pd.Timedelta(days=1) - pd.Timedelta(minutes=1)  # incluye todo el último día

fig = go.Figure()
for df, nombre in [(df_NSRDB, "NSRDB"), (df_Solcast, "Solcast")]:
    d = df.loc[ini_periodo:fin_incl]
    fig.add_trace(go.Scatter(
        x=d.index, y=d["P. estimada"] / 1000,   # W → kW
        name=nombre, mode="lines",
    ))

fig.update_layout(
    title=f"Potencia estimada: NSRDB vs Solcast "
          f"({ini_periodo:%d/%m/%Y} – {fin_periodo:%d/%m/%Y})",
    xaxis_title="Fecha",
    yaxis_title="Potencia (kW)",
)

guardar(fig, f"potencia_estimada_{ini_periodo:%Y-%m-%d}_a_{fin_periodo:%Y-%m-%d}")


from scipy.integrate import trapezoid
from plotly.subplots import make_subplots

# ===================== ENERGÍA (REGLA DEL TRAPECIO) =====================
energia = lambda s: trapezoid(s.dropna(), (s.dropna().index - s.index[0]).total_seconds() / 3600) / 1e6  # W → MWh

E_mes = pd.DataFrame({n: df["P. estimada"].groupby(df.index.to_period("M")).apply(energia)
                      for df, n in [(df_NSRDB, "NSRDB"), (df_Solcast, "Solcast")]})
E_año = E_mes.groupby(E_mes.index.year).sum()
E_tot = E_mes.sum().to_frame("Total").T
E_mes.index = E_mes.index.strftime("%b-%Y")

# ===================== GRÁFICA DE ENERGÍAS =====================
fig = make_subplots(rows=2, cols=2, specs=[[{"colspan": 2}, None], [{}, {}]],
                    subplot_titles=("Mensual", "Anual", "Total"), vertical_spacing=0.15)

for tabla, r, c in [(E_mes, 1, 1), (E_año, 2, 1), (E_tot, 2, 2)]:
    print(tabla.assign(**{"Dif. (%)": (tabla.Solcast / tabla.NSRDB - 1) * 100}).round(2), "\n")
    for i, n in enumerate(["NSRDB", "Solcast"]):
        fig.add_trace(go.Bar(x=tabla.index.astype(str), y=tabla[n], name=n, marker_color=PALETA[i],
                             legendgroup=n, showlegend=r == 1, text=tabla[n].round(1) if r > 1 else None,
                             textposition="outside", cliponaxis=False), r, c)

fig.update_yaxes(title_text="Energía (MWh)", col=1)
fig.update_layout(title="Energía estimada: NSRDB vs Solcast", barmode="group")
guardar(fig, "energia_mensual_anual_total")

# ===================== FACTOR DE PLANTA ANUAL =====================
horas = pd.Series(df_NSRDB.index.normalize().unique()).dt.year.value_counts().sort_index() * 24
FP = E_año.div(P_nom / 1e6 * horas, axis=0) * 100   # P_nom: W → MW
print("Factor de planta anual (%):\n", FP.round(2))
