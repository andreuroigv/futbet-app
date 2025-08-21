# app.py
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="Football Bets Tracker", layout="wide")
st.title("⚽️ Seguimiento de Apuestas de Fútbol")

if st.button("🔁 Actualizar datos"):
    st.cache_data.clear()

# -----------------------------
# Utilidades
# -----------------------------
COL_SHEET = "Predictions"
FILE_PATH = "predictions_tracker.xlsx"

MESES_ES = {
    "January": "Enero", "February": "Febrero", "March": "Marzo",
    "April": "Abril", "May": "Mayo", "June": "Junio",
    "July": "Julio", "August": "Agosto", "September": "Septiembre",
    "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
}

def _to_float(x, default=np.nan):
    if pd.isna(x):
        return default
    s = str(x).strip().replace(",", ".").replace("%", "")
    try:
        return float(s)
    except Exception:
        return default

def _norm_str(s):
    if pd.isna(s):
        return ""
    return str(s).strip()

def _norm_outcome(x: str) -> str:
    """Normaliza outcomes para comparaciones si hiciera falta."""
    t = _norm_str(x).lower()
    aliases = {
        "home win": "home win", "1": "home win", "home": "home win", "local": "home win", "h": "home win",
        "away win": "away win", "2": "away win", "away": "away win", "visitante": "away win", "a": "away win",
        "draw": "draw", "empate": "draw", "x": "draw",
    }
    return aliases.get(t, t)

# -----------------------------
# Carga y normalización
# -----------------------------
@st.cache_data
def cargar_tracker(path: str = FILE_PATH, sheet: str = COL_SHEET) -> pd.DataFrame:
    try:
        df = pd.read_excel(path, sheet_name=sheet)
    except Exception as e:
        st.warning(f"No se pudo cargar {path} ({sheet}): {e}")
        return pd.DataFrame()

    # Homogeneiza nombres de columnas frecuentes
    lower = {c.lower().strip(): c for c in df.columns}
    ren = {}
    # Predicción con/ sin tilde -> Prediccion
    pred_col = lower.get("prediccion") or lower.get("predicción")
    if pred_col and pred_col != "Prediccion":
        ren[pred_col] = "Prediccion"
    # Resultado_Real variaciones
    rr_col = lower.get("resultado_real") or lower.get("resultado real")
    if rr_col and rr_col != "Resultado_Real":
        ren[rr_col] = "Resultado_Real"
    # Estándares
    for target in ["Date", "Liga", "Local", "Visitante", "Status", "Result", "Profit", "ROI", "Stake", "Cuota_Bet365", "Enviado"]:
        lc = target.lower()
        if lc in lower and lower[lc] != target:
            ren[lower[lc]] = target

    if ren:
        df = df.rename(columns=ren)

    # Fecha
    if "Date" in df.columns:
        df["fecha"] = pd.to_datetime(df["Date"], errors="coerce")
    else:
        df["fecha"] = pd.NaT

    # Numéricos
    if "Profit" in df.columns:
        df["Profit"] = pd.to_numeric(df["Profit"], errors="coerce")
    else:
        df["Profit"] = np.nan

    if "ROI" in df.columns:
        # ROI puede venir como % o número; lo dejamos en porcentaje (p.ej., 12.5)
        roi_num = df["ROI"].apply(lambda x: _to_float(x))
        # Si parece fracción (<=1) lo convertimos a %
        df["ROI"] = np.where(roi_num <= 1, roi_num * 100.0, roi_num)
    else:
        df["ROI"] = np.nan

    # Campos de texto principales asegurados
    for c in ["Liga", "Local", "Visitante", "Prediccion", "Result", "Resultado_Real", "Status"]:
        if c not in df.columns:
            df[c] = ""

    # Normaliza status
    df["Status_norm"] = df["Status"].astype(str).str.strip().str.lower()

    # Acierto/Fallo: algunos flujos escriben 'Acierto'/'Fallo' ahí.
    df["Resultado_Real"] = df["Resultado_Real"].astype(str).str.strip()

    # Resultado real oficial del partido (de API) está en 'Result'
    df["Result"] = df["Result"].astype(str).strip()

    # Predicción normalizada (si hiciera falta para comparaciones)
    df["Prediccion_norm"] = df["Prediccion"].apply(_norm_outcome)
    df["Result_norm"] = df["Result"].apply(_norm_outcome)

    return df

df = cargar_tracker()

if df.empty:
    st.stop()

# -----------------------------
# Filtros
# -----------------------------
st.sidebar.header("Filtros")

min_date = df["fecha"].min()
max_date = df["fecha"].max()
if pd.isna(min_date) or pd.isna(max_date):
    # fallback si las fechas no están
    min_date = pd.Timestamp.today() - pd.Timedelta(days=30)
    max_date = pd.Timestamp.today()

fecha_inicio = st.sidebar.date_input("Desde", value=min_date.date())
fecha_fin = st.sidebar.date_input("Hasta", value=max_date.date())

ligas = sorted([x for x in df["Liga"].dropna().unique().tolist() if x != ""])
liga_sel = st.sidebar.multiselect("Ligas", options=ligas, default=ligas)

equipos = sorted(set(df["Local"].dropna().unique()) | set(df["Visitante"].dropna().unique()))
equipo_sel = st.sidebar.selectbox("Filtrar por equipo", ["Todos"] + equipos)

status_opts = ["Todos", "Pending", "Completed"]
status_sel = st.sidebar.selectbox("Estado", status_opts, index=2)  # por defecto 'Completed'

filtro = (df["fecha"] >= pd.to_datetime(fecha_inicio)) & (df["fecha"] <= pd.to_datetime(fecha_fin))
if liga_sel:
    filtro &= df["Liga"].isin(liga_sel)
if equipo_sel != "Todos":
    filtro &= (df["Local"] == equipo_sel) | (df["Visitante"] == equipo_sel)

if status_sel != "Todos":
    filtro &= (df["Status_norm"] == status_sel.lower())

df_filtrado = df[filtro].copy()

# -----------------------------
# Preparar conjunto validado (evaluadas)
# -----------------------------
# Consideramos evaluadas las que están 'Completed' y tienen Profit no nulo
df_validadas = df_filtrado[df_filtrado["Status_norm"] == "completed"].copy()
# En algunos casos ROI/Profit pueden ser NaN si no se pudo calcular; filtramos por Profit no NaN para los KPIs
df_validadas = df_validadas[pd.notna(df_validadas["Profit"])]

# -----------------------------
# KPIs
# -----------------------------
total_apuestas = len(df_validadas)
total_unidades = df_validadas["Profit"].sum() if total_apuestas else 0.0
yield_total = (total_unidades / total_apuestas) if total_apuestas else 0.0

ganancias = df_validadas.loc[df_validadas["Profit"] > 0, "Profit"].sum()
perdidas = -df_validadas.loc[df_validadas["Profit"] < 0, "Profit"].sum()
profit_factor = (ganancias / perdidas) if perdidas > 0 else float("inf")

# Aciertos/Fallos (Resultado_Real contiene 'Acierto'/'Fallo')
aciertos_totales = (df_validadas["Resultado_Real"].str.lower() == "acierto").sum()
fallos_totales = (df_validadas["Resultado_Real"].str.lower() == "fallo").sum()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("🎯 Apuestas evaluadas", total_apuestas)
col2.metric("✅ Aciertos", int(aciertos_totales))
col3.metric("💸 Unidades ganadas", round(float(total_unidades), 2))
col4.metric("📈 Yield", f"{round(100 * yield_total, 2)}%")
col5.metric("📊 Profit Factor", round(profit_factor, 2) if profit_factor != float("inf") else "∞")

# -----------------------------
# Resumen mensual
# -----------------------------
if not df_validadas.empty:
    df_validadas["mes"] = df_validadas["fecha"].dt.to_period("M").dt.to_timestamp()

    resumen_mensual = df_validadas.groupby("mes", as_index=False).agg(
        Apuestas=("Profit", "count"),
        Aciertos=("Resultado_Real", lambda x: (x.str.lower() == "acierto").sum()),
        Fallos=("Resultado_Real", lambda x: (x.str.lower() == "fallo").sum()),
        Unidades=("Profit", "sum"),
    )
    resumen_mensual["yield_num"] = resumen_mensual["Unidades"] / resumen_mensual["Apuestas"]
    resumen_mensual["Mes"] = resumen_mensual["mes"].dt.strftime("%B").map(MESES_ES)
    resumen_mensual["Yield"] = (resumen_mensual["yield_num"] * 100).round(2).astype(str) + "%"
    resumen_mensual = resumen_mensual.drop(columns=["yield_num", "mes"])

    st.subheader("📆 Resumen mensual")
    st.dataframe(resumen_mensual[["Mes", "Apuestas", "Aciertos", "Fallos", "Unidades", "Yield"]],
                 use_container_width=True)
else:
    st.info("No hay apuestas evaluadas en el rango/ filtros actuales para el resumen mensual.")

# -----------------------------
# Gráfico semanal: unidades y acumuladas
# -----------------------------
st.subheader("📈 Evolución semanal de unidades")
if not df_validadas.empty:
    df_validadas["semana"] = df_validadas["fecha"].dt.to_period("W").apply(lambda r: r.start_time)
    resumen_semanal = df_validadas.groupby("semana", as_index=False).agg(unidades=("Profit", "sum"))
    resumen_semanal["unidades_acumuladas"] = resumen_semanal["unidades"].cumsum()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=resumen_semanal["semana"],
        y=resumen_semanal["unidades"],
        name="Unidades semanales",
        yaxis="y1"
    ))
    fig.add_trace(go.Scatter(
        x=resumen_semanal["semana"],
        y=resumen_semanal["unidades_acumuladas"],
        name="Unidades acumuladas",
        yaxis="y2",
        mode="lines+markers"
    ))
    fig.update_layout(
        xaxis_title="Semana",
        yaxis=dict(title="Unidades semanales", side="left"),
        yaxis2=dict(title="Unidades acumuladas", overlaying="y", side="right"),
        legend=dict(x=0.01, y=0.99),
        barmode="group",
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No hay datos suficientes para el gráfico semanal con los filtros actuales.")

# -----------------------------
# Historial detallado
# -----------------------------
st.subheader("📋 Historial completo de apuestas")

# Construye columnas legibles para la tabla
df_hist = df_filtrado.copy()
# Si quieres mostrar solo evaluadas, descomenta la línea:
# df_hist = df_hist[df_hist["Status_norm"] == "completed"].copy()

# Selección y renombrado
df_hist = df_hist.sort_values("fecha", ascending=False)
cols_existentes = df_hist.columns

cols_table = []
for c in ["fecha", "Liga", "Local", "Visitante", "Prediccion", "Result", "Resultado_Real", "Cuota_Bet365", "Stake", "Profit", "ROI", "Status", "Enviado"]:
    if c in cols_existentes:
        cols_table.append(c)

st.dataframe(df_hist[cols_table], use_container_width=True)
