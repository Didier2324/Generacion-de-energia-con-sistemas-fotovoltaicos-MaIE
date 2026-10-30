from pathlib import Path
import pandas as pd

T = "Fecha y Hora"
PASO = pd.Timedelta(minutes=5)
carpeta = Path(__file__).parent

# Leer archivos y agregar la fecha del nombre a la hora
dfs = []
for archivo in sorted(carpeta.glob("SFV microrred*.xls")):
    df = pd.read_excel(archivo, engine="xlrd")
    fecha = archivo.stem.split()[2]
    df[T] = pd.to_datetime(fecha + " " + df[T].astype(str))
    df["archivo"] = archivo.name
    dfs.append(df)

# Unir, quitar columnas vacías y ordenar
datos = (pd.concat(dfs, ignore_index=True)
           .dropna(axis=1, how="all")
           .sort_values(T, ignore_index=True))

# Verificaciones
print(f"Fechas repetidas: {datos.duplicated(T).sum()}")
print("Celdas vacías por columna:\n", datos.isna().sum())

# Detectar huecos y crear las marcas de tiempo faltantes
nuevas = []
for i in datos.index[datos[T].diff() > PASO]:
    inicio, fin = datos.at[i - 1, T], datos.at[i, T]
    rango = pd.date_range(inicio, fin, freq=PASO)[1:]
    rango = rango[rango < fin]
    nuevas.extend(rango)
    print(f"  {inicio} -> {fin}  ({len(rango)} faltantes)")

# Insertar filas nuevas y rellenar con el promedio anterior/posterior
datos["relleno"] = False
datos = pd.concat([datos, pd.DataFrame({T: nuevas, "relleno": True})]) \
          .sort_values(T, ignore_index=True)

num = datos.select_dtypes("number").columns
mask = datos["relleno"]
datos.loc[mask, num] = ((datos[num].ffill() + datos[num].bfill()) / 2)[mask]
datos["archivo"] = datos["archivo"].ffill()

print(f"Filas agregadas: {len(nuevas)}")






import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go

# ===================== ESTILO DE LAS GRÁFICAS =====================
FUENTE        = "Times New Roman"
TAM_TEXTO     = 14        # ticks, leyenda, texto general
TAM_TITULO    = 22
TAM_EJES      = 16        # títulos de los ejes
GROSOR_LINEA  = 2
COLOR_GRILLA  = "#E0E0E0"
PALETA = ["#F2A900",  # amarillo solar
          "#1F77B4",  # azul
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




#-------------------------------------------------------------
# 1.a) Gráficar curvas de potencia Gen,Dem,Carga y Descarga :
#-------------------------------------------------------------
# Balance neto de la batería: |Carga| - |Descarga|
datos["Balance W"] = datos["Carga W"].abs() - datos["Descarga W"].abs()

columnas = ["FV", "Carga W", "Descarga W", "Carga de Respaldo W", "Balance W"]
nombres = {"FV": "Generación FV",
           "Carga W": "Carga de batería",
           "Descarga W": "Descarga de batería",
           "Carga de Respaldo W": "Demanda (respaldo)",
           "Balance W": "|Carga| − |Descarga|"}
colores = {"FV": PALETA[0],                 # amarillo
           "Carga W": PALETA[2],            # verde
           "Descarga W": "#7F7F7F",         # gris
           "Carga de Respaldo W": "black",  # negro
           "Balance W": "#4FC3F7"}          # celeste

fig = px.line(datos, x=T, y=columnas,
              title="Flujos de potencia del sistema",
              labels={T: "Fecha y hora", "value": "Potencia (W)", "variable": ""},
              color_discrete_map=colores,
              render_mode="svg")

fig.for_each_trace(lambda t: t.update(name=nombres[t.name]))

for i, col in enumerate(columnas):
    fig.add_scatter(x=datos.loc[mask, T], y=datos.loc[mask, col],
                    mode="markers", marker=dict(color=PALETA[3], size=8, line=dict(color="black", width=1)),
                    name="Datos rellenados", legendgroup="relleno",
                    showlegend=(i == 0))

guardar(fig, "flujos_potencia")





#-------------------------------------------------------------
# 1.b) Gráficar energía horaria de Gen,Dem,Carga y Descarga :
#-------------------------------------------------------------
cols_e = ["FV", "Carga W", "Descarga W", "Carga de Respaldo W"]

p = datos.set_index(T)[cols_e].abs()                  # potencias en W
t = p.index.to_series()
dt_h = (t.shift(-1) - t).dt.total_seconds() / 3600    # Δt de cada intervalo en horas

# Energía de cada intervalo en kWh: (P_i + P_i+1)/2 * Δt / 1000
e_int = (p + p.shift(-1)).div(2).mul(dt_h, axis=0) / 1000

# Sumar por hora y separar día y hora
energia = e_int.resample("h").sum()
energia["Día"] = energia.index.date.astype(str)
energia["Hora"] = energia.index.hour

print("Energía total en el periodo (kWh):")
print(energia[cols_e].sum().round(2))

# Una subgráfica por día (2 columnas x 4 filas)
fig = px.bar(energia, x="Hora", y=cols_e,
             facet_col="Día", facet_col_wrap=2,
             facet_row_spacing=0.09, facet_col_spacing=0.05,
             title="Energía horaria por día",
             labels={"value": "Energía (kWh)", "variable": ""},
             color_discrete_map=colores, barmode="group")

fig.for_each_trace(lambda t: t.update(name=nombres[t.name]))
fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[1]))  # "Día=2026-10-13" -> "2026-10-13"

fig.update_xaxes(dtick=2, range=[-0.5, 23.5], showticklabels=True)
fig.update_yaxes(range=[0, 0.7], autorange=False)


fig.update_xaxes(dtick=2, range=[-0.5, 23.5], showticklabels=True)
fig.update_yaxes(range=[0, 0.7], autorange=False)
fig.update_layout(margin=dict(t=90, b=70))

guardar(fig, "energia_horaria", ancho=2200, alto=1080)


# ============ ENERGÍA DIARIA ============
energia_dia = e_int.resample("D").sum()
energia_dia.index = energia_dia.index.date        # solo la fecha, sin hora

print("Energía diaria (kWh):")
print(energia_dia.round(2))

fig = px.bar(energia_dia.reset_index(names="Fecha"), x="Fecha", y=cols_e,
             title="Energía diaria del sistema",
             labels={"value": "Energía (kWh)", "variable": ""},
             color_discrete_map=colores, barmode="group",
             text_auto=".2f")                     # valor sobre cada barra

fig.for_each_trace(lambda t: t.update(name=nombres[t.name]))
fig.update_xaxes(type="category")                 # una barra por día, sin huecos
fig.update_traces(textposition="outside", cliponaxis=False)

guardar(fig, "energia_diaria", ancho=1400, alto=400)


#-------------------------------------------------------------
# 1.c) Calculo factor de planta:
#-------------------------------------------------------------
CAP_NOMINAL = 280*4/1000     # kWp  

# Periodo completo
E_gen = e_int["FV"].sum()                                     # kWh
horas = (datos[T].iloc[-1] - datos[T].iloc[0]).total_seconds() / 3600
FP_total = E_gen / (CAP_NOMINAL * horas)

print(f"Energía generada: {E_gen:.2f} kWh")
print(f"Tiempo del periodo: {horas:.1f} h")
print(f"Factor de planta total: {FP_total:.2%}")

# Por día
FP_dia = energia_dia["FV"] / (CAP_NOMINAL * 24)
print("\nFactor de planta diario:")
print(FP_dia.map("{:.2%}".format))