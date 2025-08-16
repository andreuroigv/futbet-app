import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime
import plotly.graph_objects as go

st.set_page_config(page_title="Football Tracker", layout="wide")
st.title("⚽ Seguimiento de Predicciones de Fútbol")

if st.button("🔁 Actualizar datos"):
    st.cache_data.clear()

# Leer datos de la hoja Results
@st.cache_data
def cargar_datos():
    try:
        # Leer la hoja Results que contiene los datos procesados
        df_results = pd.read_excel("predictions_tracker.xlsx", sheet_name="Results")
        
        if not df_results.empty:
            # Convertir fecha a datetime
            df_results['Date'] = pd.to_datetime(df_results['Date'])
            return df_results, True
        else:
            st.warning("No hay resultados procesados aún en la hoja Results")
            return pd.DataFrame(), False
            
    except Exception as e:
        st.warning(f"No se pudo cargar el archivo predictions_tracker.xlsx: {str(e)}")
        return pd.DataFrame(), False

df, has_data = cargar_datos()

if not has_data:
    st.info("Esperando resultados procesados...")
    st.stop()

# Mostrar información básica del dataset
st.sidebar.header("📊 Información del Dataset")
st.sidebar.write(f"**Total de resultados:** {len(df)}")
st.sidebar.write(f"**Columnas:** Date, Liga, Local, Visitante, Resultado_Real, Predicción, Acierto, Profit, ROI")

# Filtros
st.sidebar.header("🔧 Filtros")

# Filtros de fecha
fecha_inicio = st.sidebar.date_input("Desde", value=df['Date'].min().date())
fecha_fin = st.sidebar.date_input("Hasta", value=df['Date'].max().date())
filtro_fecha = (df['Date'] >= pd.to_datetime(fecha_inicio)) & (df['Date'] <= pd.to_datetime(fecha_fin))
df_filtrado = df[filtro_fecha].copy()

# Filtro por liga
ligas_unicas = df['Liga'].dropna().unique()
liga_seleccionada = st.sidebar.multiselect(
    "Filtrar por liga/competición",
    options=sorted(ligas_unicas),
    default=sorted(ligas_unicas)
)

if liga_seleccionada:
    df_filtrado = df_filtrado[df_filtrado['Liga'].isin(liga_seleccionada)]

# Filtro por equipo
equipos_unicos = set()
equipos_unicos.update(df['Local'].dropna().unique())
equipos_unicos.update(df['Visitante'].dropna().unique())

equipo_seleccionado = st.sidebar.selectbox(
    "Filtrar por equipo", 
    ["Todos"] + sorted(list(equipos_unicos))
)

if equipo_seleccionado != "Todos":
    filtro_equipo = (df_filtrado['Local'] == equipo_seleccionado) | (df_filtrado['Visitante'] == equipo_seleccionado)
    df_filtrado = df_filtrado[filtro_equipo]

# Filtro por tipo de resultado
tipo_resultado = st.sidebar.selectbox(
    "Filtrar por resultado",
    ["Todos", "Solo Aciertos", "Solo Fallos"]
)

if tipo_resultado == "Solo Aciertos":
    df_filtrado = df_filtrado[df_filtrado['Acierto'] == True]
elif tipo_resultado == "Solo Fallos":
    df_filtrado = df_filtrado[df_filtrado['Acierto'] == False]

# -------------------------
# KPIs Principales
# -------------------------
st.subheader("📊 Métricas Principales")

if len(df_filtrado) > 0:
    total_predicciones = len(df_filtrado)
    aciertos_totales = (df_filtrado['Acierto'] == True).sum()
    porcentaje_aciertos = (aciertos_totales / total_predicciones * 100) if total_predicciones > 0 else 0
    
    total_unidades = df_filtrado['Profit'].sum()
    yield_total = total_unidades / total_predicciones if total_predicciones > 0 else 0
    
    ganancias = df_filtrado[df_filtrado['Profit'] > 0]['Profit'].sum()
    perdidas = -df_filtrado[df_filtrado['Profit'] < 0]['Profit'].sum()
    profit_factor = ganancias / perdidas if perdidas > 0 else float("inf")
    
    roi_promedio = df_filtrado['ROI'].mean()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🎯 Predicciones totales", total_predicciones)
    col2.metric("✅ Aciertos", f"{aciertos_totales} ({porcentaje_aciertos:.1f}%)")
    col3.metric("💰 Unidades ganadas", round(total_unidades, 2))
    col4.metric("📈 Yield", f"{round(100 * yield_total, 2)}%")
    col5.metric("📊 Profit Factor", round(profit_factor, 2) if profit_factor != float("inf") else "∞")

    # Segunda fila de métricas
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("📅 Última actualización", df_filtrado['Date'].max().strftime('%Y-%m-%d'))
    col2.metric("💵 ROI Promedio", f"{round(roi_promedio, 2)}%")
    col3.metric("💚 Ganancias", f"+{round(ganancias, 2)}")
    col4.metric("💔 Pérdidas", f"-{round(perdidas, 2)}")
    col5.metric("📏 Días de análisis", (df_filtrado['Date'].max() - df_filtrado['Date'].min()).days + 1)

else:
    st.warning("No hay datos para mostrar con los filtros seleccionados")
    st.stop()

# -------------------------
# Análisis temporal
# -------------------------
st.subheader("📈 Evolución Temporal")

tab1, tab2 = st.tabs(["📅 Resumen Mensual", "📊 Evolución Semanal"])

with tab1:
    df_filtrado["mes"] = df_filtrado["Date"].dt.to_period("M").dt.to_timestamp()

    resumen_mensual = df_filtrado.groupby("mes").agg({
        'Profit': ['count', 'sum'],
        'Acierto': lambda x: (x == True).sum()
    }).reset_index()

    # Aplanar columnas multinivel
    resumen_mensual.columns = ['mes', 'predicciones', 'unidades', 'aciertos']
    resumen_mensual['fallos'] = resumen_mensual['predicciones'] - resumen_mensual['aciertos']
    resumen_mensual["yield"] = (resumen_mensual["unidades"] / resumen_mensual["predicciones"] * 100).round(2)
    resumen_mensual["accuracy"] = (resumen_mensual["aciertos"] / resumen_mensual["predicciones"] * 100).round(1)

    # Mapeo de meses al español
    meses_es = {
        "January": "Enero", "February": "Febrero", "March": "Marzo",
        "April": "Abril", "May": "Mayo", "June": "Junio",
        "July": "Julio", "August": "Agosto", "September": "Septiembre",
        "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
    }

    resumen_mensual["Mes"] = resumen_mensual["mes"].dt.strftime("%B %Y").apply(
        lambda x: meses_es.get(x.split()[0], x.split()[0]) + " " + x.split()[1]
    )

    # Formatear para mostrar
    resumen_display = resumen_mensual[['Mes', 'predicciones', 'aciertos', 'fallos', 'unidades', 'yield', 'accuracy']].copy()
    resumen_display.columns = ['Mes', 'Predicciones', 'Aciertos', 'Fallos', 'Unidades', 'Yield (%)', 'Accuracy (%)']
    resumen_display['Unidades'] = resumen_display['Unidades'].round(2)

    st.dataframe(resumen_display, use_container_width=True)

with tab2:
    df_filtrado["semana"] = df_filtrado["Date"].dt.to_period("W").apply(lambda r: r.start_time)

    resumen_semanal = df_filtrado.groupby("semana").agg({
        'Profit': 'sum'
    }).reset_index()
    resumen_semanal.columns = ['semana', 'unidades']
    resumen_semanal["unidades_acumuladas"] = resumen_semanal["unidades"].cumsum()

    fig = go.Figure()

    # Barras: unidades por semana
    fig.add_trace(go.Bar(
        x=resumen_semanal["semana"],
        y=resumen_semanal["unidades"],
        name="Unidades semanales",
        yaxis="y1",
        marker_color=['green' if x >= 0 else 'red' for x in resumen_semanal["unidades"]]
    ))

    # Línea: unidades acumuladas
    fig.add_trace(go.Scatter(
        x=resumen_semanal["semana"],
        y=resumen_semanal["unidades_acumuladas"],
        name="Unidades acumuladas",
        yaxis="y2",
        mode="lines+markers",
        line=dict(color='blue', width=3)
    ))

    fig.update_layout(
        title="📈 Evolución semanal de unidades",
        xaxis_title="Semana",
        yaxis=dict(title="Unidades semanales", side="left"),
        yaxis2=dict(title="Unidades acumuladas", overlaying="y", side="right"),
        legend=dict(x=0.01, y=0.99),
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

# -------------------------
# Análisis detallados
# -------------------------
st.subheader("🔍 Análisis Detallado")

tab1, tab2, tab3 = st.tabs(["🏆 Por Liga/Competición", "📊 Distribuciones", "🎯 Tipos de Apuesta"])

with tab1:
    analisis_liga = df_filtrado.groupby('Liga').agg({
        'Profit': ['count', 'sum', 'mean'],
        'Acierto': lambda x: (x == True).sum(),
        'ROI': 'mean'
    }).round(2)
    
    analisis_liga.columns = ['Predicciones', 'Unidades_Total', 'Unidades_Promedio', 'Aciertos', 'ROI_Promedio']
    analisis_liga['Porcentaje_Aciertos'] = (analisis_liga['Aciertos'] / analisis_liga['Predicciones'] * 100).round(1)
    analisis_liga['Yield'] = (analisis_liga['Unidades_Total'] / analisis_liga['Predicciones'] * 100).round(2)
    
    # Reordenar columnas
    analisis_liga = analisis_liga[['Predicciones', 'Aciertos', 'Porcentaje_Aciertos', 'Unidades_Total', 'Unidades_Promedio', 'Yield', 'ROI_Promedio']]
    
    st.dataframe(analisis_liga.sort_values('Yield', ascending=False), use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)
    
    with col1:
        # Distribución de profits
        fig_profit = px.histogram(
            df_filtrado, 
            x='Profit', 
            title="💰 Distribución de Profit",
            nbins=20,
            color_discrete_sequence=['green']
        )
        st.plotly_chart(fig_profit, use_container_width=True)
    
    with col2:
        # Distribución de ROI
        fig_roi = px.histogram(
            df_filtrado, 
            x='ROI', 
            title="📊 Distribución de ROI",
            nbins=20,
            color_discrete_sequence=['blue']
        )
        st.plotly_chart(fig_roi, use_container_width=True)

with tab3:
    tipo_apuesta_counts = df_filtrado['Predicción'].value_counts()
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_tipos = px.pie(
            values=tipo_apuesta_counts.values,
            names=tipo_apuesta_counts.index,
            title="🎯 Distribución de Tipos de Predicción"
        )
        st.plotly_chart(fig_tipos, use_container_width=True)
    
    with col2:
        rendimiento_tipo = df_filtrado.groupby('Predicción').agg({
            'Profit': ['sum', 'mean', 'count'],
            'Acierto': lambda x: (x == True).sum()
        }).round(2)
        
        rendimiento_tipo.columns = ['Total', 'Promedio', 'Cantidad', 'Aciertos']
        rendimiento_tipo['Accuracy'] = (rendimiento_tipo['Aciertos'] / rendimiento_tipo['Cantidad'] * 100).round(1)
        rendimiento_tipo['Yield'] = (rendimiento_tipo['Total'] / rendimiento_tipo['Cantidad'] * 100).round(2)
        
        st.write("**Rendimiento por tipo de predicción:**")
        st.dataframe(rendimiento_tipo.sort_values('Total', ascending=False))

# -------------------------
# Tabla de historial detallado
# -------------------------
st.subheader("📋 Historial Completo de Resultados")

# Preparar datos para mostrar
df_display = df_filtrado.copy()
df_display['Date'] = df_display['Date'].dt.strftime('%Y-%m-%d')
df_display['Acierto'] = df_display['Acierto'].map({True: '✅', False: '❌'})
df_display['Profit'] = df_display['Profit'].round(2)
df_display['ROI'] = df_display['ROI'].round(2)

# Reordenar columnas para mejor visualización
columnas_display = ['Date', 'Liga', 'Local', 'Visitante', 'Predicción', 'Resultado_Real', 'Acierto', 'Profit', 'ROI']
df_display = df_display[columnas_display]

# Ordenar por fecha (más recientes primero)
df_display = df_display.sort_values('Date', ascending=False)

st.dataframe(df_display, use_container_width=True)

# -------------------------
# Información adicional
# -------------------------
st.markdown("---")
st.markdown("🔄 **Los datos se actualizan automáticamente cada 4 horas**")

with st.expander("ℹ️ Información sobre los datos"):
    st.write("**Fuente de datos:** Hoja 'Results' del archivo predictions_tracker.xlsx")
    st.write("**Estructura:**")
    st.write("- **Date:** Fecha del partido")
    st.write("- **Liga:** Competición del partido")
    st.write("- **Local/Visitante:** Equipos que juegan")
    st.write("- **Predicción:** Pronóstico realizado")
    st.write("- **Resultado_Real:** Resultado real del partido")
    st.write("- **Acierto:** Si la predicción fue correcta")
    st.write("- **Profit:** Ganancia/pérdida en unidades")
    st.write("- **ROI:** Return on Investment en porcentaje")
