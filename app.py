import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime
import plotly.graph_objects as go

st.set_page_config(page_title="Football Tracker", layout="wide")
st.title("⚽ Seguimiento de Predicciones de Fútbol")

if st.button("🔁 Actualizar datos"):
    st.cache_data.clear()

# Leer datos
@st.cache_data
def cargar_datos():
    try:
        df = pd.read_excel("predictions_tracker.xlsx")
        # Intentar diferentes nombres de columna para fecha
        fecha_cols = ['fecha', 'date', 'Date', 'Fecha']
        fecha_col = None
        for col in fecha_cols:
            if col in df.columns:
                fecha_col = col
                break
        
        if fecha_col:
            df[fecha_col] = pd.to_datetime(df[fecha_col])
        else:
            st.warning("No se encontró columna de fecha en el archivo")
        
        return df, fecha_col
    except Exception as e:
        st.warning(f"No se pudo cargar el archivo predictions_tracker.xlsx: {str(e)}")
        return pd.DataFrame(), None

df, fecha_col = cargar_datos()

if df.empty:
    st.error("No hay datos disponibles para mostrar")
    st.stop()

# Mostrar información básica del dataset
st.sidebar.header("📊 Información del Dataset")
st.sidebar.write(f"**Total de registros:** {len(df)}")
st.sidebar.write(f"**Columnas disponibles:** {list(df.columns)}")

# Filtros
st.sidebar.header("🔧 Filtros")

# Filtros de fecha (si hay columna de fecha)
if fecha_col:
    fecha_inicio = st.sidebar.date_input("Desde", value=df[fecha_col].min().date())
    fecha_fin = st.sidebar.date_input("Hasta", value=df[fecha_col].max().date())
    filtro_fecha = (df[fecha_col] >= pd.to_datetime(fecha_inicio)) & (df[fecha_col] <= pd.to_datetime(fecha_fin))
    df_filtrado = df[filtro_fecha].copy()
else:
    df_filtrado = df.copy()

# Filtros adicionales basados en columnas disponibles
equipo_cols = [col for col in df.columns if any(word in col.lower() for word in ['equipo', 'team', 'local', 'visitante', 'home', 'away'])]
liga_cols = [col for col in df.columns if any(word in col.lower() for word in ['liga', 'league', 'competition', 'campeonato'])]

# Filtro por equipo
if equipo_cols:
    equipos_unicos = set()
    for col in equipo_cols:
        equipos_unicos.update(df[col].dropna().unique())
    
    equipo_seleccionado = st.sidebar.selectbox(
        "Filtrar por equipo", 
        ["Todos"] + sorted(list(equipos_unicos))
    )
    
    if equipo_seleccionado != "Todos":
        filtro_equipo = False
        for col in equipo_cols:
            filtro_equipo |= (df_filtrado[col] == equipo_seleccionado)
        df_filtrado = df_filtrado[filtro_equipo]

# Filtro por liga
if liga_cols:
    ligas_unicas = df[liga_cols[0]].dropna().unique()
    liga_seleccionada = st.sidebar.multiselect(
        "Filtrar por liga/competición",
        options=sorted(ligas_unicas),
        default=sorted(ligas_unicas)
    )
    
    if liga_seleccionada:
        df_filtrado = df_filtrado[df_filtrado[liga_cols[0]].isin(liga_seleccionada)]

# Detectar columnas importantes
resultado_cols = [col for col in df.columns if any(word in col.lower() for word in ['resultado', 'result', 'outcome'])]
prediccion_cols = [col for col in df.columns if any(word in col.lower() for word in ['prediccion', 'prediction', 'forecast', 'pronostico'])]
profit_cols = [col for col in df.columns if any(word in col.lower() for word in ['profit', 'ganancia', 'beneficio', 'units', 'unidades'])]
cuota_cols = [col for col in df.columns if any(word in col.lower() for word in ['cuota', 'odd', 'quota'])]

# Excluir resultados anulados si hay columna de resultado
if resultado_cols:
    df_filtrado = df_filtrado[~df_filtrado[resultado_cols[0]].isin(['Anulado', 'Void', 'Cancelled'])]

# -------------------------
# KPIs
# -------------------------
st.subheader("📊 Métricas Principales")

# Calcular métricas si tenemos las columnas necesarias
if profit_cols:
    df_validadas = df_filtrado.dropna(subset=[profit_cols[0]]).copy()
    
    total_predicciones = df_validadas.shape[0]
    total_unidades = df_validadas[profit_cols[0]].sum()
    yield_total = total_unidades / total_predicciones if total_predicciones else 0
    
    if resultado_cols:
        aciertos_totales = (df_validadas[resultado_cols[0]].isin(['Acierto', 'Win', 'Green', '✅'])).sum()
        fallos_totales = (df_validadas[resultado_cols[0]].isin(['Fallo', 'Loss', 'Red', '❌'])).sum()
        porcentaje_aciertos = (aciertos_totales / total_predicciones * 100) if total_predicciones else 0
    else:
        # Si no hay columna de resultado, intentar calcular basado en profit
        aciertos_totales = (df_validadas[profit_cols[0]] > 0).sum()
        fallos_totales = (df_validadas[profit_cols[0]] < 0).sum()
        porcentaje_aciertos = (aciertos_totales / total_predicciones * 100) if total_predicciones else 0
    
    ganancias = df_validadas[df_validadas[profit_cols[0]] > 0][profit_cols[0]].sum()
    perdidas = -df_validadas[df_validadas[profit_cols[0]] < 0][profit_cols[0]].sum()
    profit_factor = ganancias / perdidas if perdidas else float("inf")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🎯 Predicciones totales", total_predicciones)
    col2.metric("✅ Aciertos", f"{aciertos_totales} ({porcentaje_aciertos:.1f}%)")
    col3.metric("💰 Unidades ganadas", round(total_unidades, 2))
    col4.metric("📈 Yield", f"{round(100 * yield_total, 2)}%")
    col5.metric("📊 Profit Factor", round(profit_factor, 2) if profit_factor != float("inf") else "∞")

else:
    # Si no hay columna de profit, mostrar métricas básicas
    total_predicciones = len(df_filtrado)
    col1, col2, col3 = st.columns(3)
    col1.metric("🎯 Predicciones totales", total_predicciones)
    
    if resultado_cols:
        aciertos_totales = (df_filtrado[resultado_cols[0]].isin(['Acierto', 'Win', 'Green', '✅'])).sum()
        porcentaje_aciertos = (aciertos_totales / total_predicciones * 100) if total_predicciones else 0
        col2.metric("✅ Aciertos", f"{aciertos_totales} ({porcentaje_aciertos:.1f}%)")
    
    if fecha_col:
        ultima_actualizacion = df_filtrado[fecha_col].max().strftime('%Y-%m-%d')
        col3.metric("📅 Última actualización", ultima_actualizacion)

# -------------------------
# Análisis temporal (solo si hay fecha y profit)
# -------------------------
if fecha_col and profit_cols and len(df_filtrado) > 0:
    st.subheader("📈 Evolución Temporal")
    
    # Tabs para diferentes vistas temporales
    tab1, tab2 = st.tabs(["📅 Resumen Mensual", "📊 Evolución Semanal"])
    
    with tab1:
        df_validadas = df_filtrado.dropna(subset=[profit_cols[0]]).copy()
        df_validadas["mes"] = df_validadas[fecha_col].dt.to_period("M").dt.to_timestamp()

        resumen_mensual = df_validadas.groupby("mes").agg({
            profit_cols[0]: ['count', 'sum'],
            resultado_cols[0] if resultado_cols else profit_cols[0]: lambda x: (x.isin(['Acierto', 'Win', 'Green', '✅']) if resultado_cols else x > 0).sum()
        }).reset_index()

        # Aplanar columnas multinivel
        resumen_mensual.columns = ['mes', 'predicciones', 'unidades', 'aciertos']
        resumen_mensual['fallos'] = resumen_mensual['predicciones'] - resumen_mensual['aciertos']
        resumen_mensual["yield"] = (resumen_mensual["unidades"] / resumen_mensual["predicciones"] * 100).round(2)

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
        resumen_display = resumen_mensual[['Mes', 'predicciones', 'aciertos', 'fallos', 'unidades', 'yield']].copy()
        resumen_display.columns = ['Mes', 'Predicciones', 'Aciertos', 'Fallos', 'Unidades', 'Yield (%)']
        resumen_display['Unidades'] = resumen_display['Unidades'].round(2)

        st.dataframe(resumen_display, use_container_width=True)

    with tab2:
        df_validadas = df_filtrado.dropna(subset=[profit_cols[0]]).copy()
        df_validadas["semana"] = df_validadas[fecha_col].dt.to_period("W").apply(lambda r: r.start_time)

        resumen_semanal = df_validadas.groupby("semana").agg({
            profit_cols[0]: 'sum'
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
# Análisis adicionales
# -------------------------
if len(df_filtrado) > 0:
    st.subheader("🔍 Análisis Detallado")
    
    tab1, tab2, tab3 = st.tabs(["🏆 Por Liga/Competición", "📊 Distribuciones", "🎯 Tipos de Apuesta"])
    
    with tab1:
        if liga_cols and profit_cols:
            analisis_liga = df_filtrado.groupby(liga_cols[0]).agg({
                profit_cols[0]: ['count', 'sum', 'mean'],
                resultado_cols[0] if resultado_cols else profit_cols[0]: lambda x: (x.isin(['Acierto', 'Win', 'Green', '✅']) if resultado_cols else x > 0).sum()
            }).round(2)
            
            analisis_liga.columns = ['Predicciones', 'Unidades_Total', 'Unidades_Promedio', 'Aciertos']
            analisis_liga['Porcentaje_Aciertos'] = (analisis_liga['Aciertos'] / analisis_liga['Predicciones'] * 100).round(1)
            analisis_liga['Yield'] = (analisis_liga['Unidades_Total'] / analisis_liga['Predicciones'] * 100).round(2)
            
            st.dataframe(analisis_liga.sort_values('Yield', ascending=False), use_container_width=True)
    
    with tab2:
        if cuota_cols:
            col1, col2 = st.columns(2)
            with col1:
                fig_cuotas = px.histogram(
                    df_filtrado, 
                    x=cuota_cols[0], 
                    title="📊 Distribución de Cuotas",
                    nbins=20
                )
                st.plotly_chart(fig_cuotas, use_container_width=True)
            
            with col2:
                if profit_cols:
                    fig_profit = px.histogram(
                        df_filtrado, 
                        x=profit_cols[0], 
                        title="💰 Distribución de Profit",
                        nbins=20,
                        color_discrete_sequence=['green']
                    )
                    st.plotly_chart(fig_profit, use_container_width=True)
    
    with tab3:
        if prediccion_cols:
            tipo_apuesta_counts = df_filtrado[prediccion_cols[0]].value_counts()
            
            col1, col2 = st.columns(2)
            with col1:
                fig_tipos = px.pie(
                    values=tipo_apuesta_counts.values,
                    names=tipo_apuesta_counts.index,
                    title="🎯 Distribución de Tipos de Apuesta"
                )
                st.plotly_chart(fig_tipos, use_container_width=True)
            
            with col2:
                if profit_cols:
                    rendimiento_tipo = df_filtrado.groupby(prediccion_cols[0])[profit_cols[0]].agg(['sum', 'mean', 'count']).round(2)
                    rendimiento_tipo.columns = ['Total', 'Promedio', 'Cantidad']
                    st.write("**Rendimiento por tipo de apuesta:**")
                    st.dataframe(rendimiento_tipo.sort_values('Total', ascending=False))

# -------------------------
# Tabla de historial detallado
# -------------------------
st.subheader("📋 Historial Completo de Predicciones")

# Seleccionar columnas más relevantes para mostrar
columnas_importantes = []
if fecha_col:
    columnas_importantes.append(fecha_col)

# Añadir columnas de equipos
columnas_importantes.extend([col for col in equipo_cols[:4]])  # Máximo 4 columnas de equipos

# Añadir otras columnas importantes
for col_list in [prediccion_cols, cuota_cols, resultado_cols, profit_cols]:
    if col_list:
        columnas_importantes.append(col_list[0])

# Filtrar solo columnas que existen en el dataframe
columnas_a_mostrar = [col for col in columnas_importantes if col in df_filtrado.columns]

# Si no hay columnas importantes detectadas, mostrar todas
if not columnas_a_mostrar:
    columnas_a_mostrar = list(df_filtrado.columns)

# Ordenar por fecha si existe, sino por índice
if fecha_col:
    df_ordenado = df_filtrado.sort_values(fecha_col, ascending=False)[columnas_a_mostrar]
else:
    df_ordenado = df_filtrado[columnas_a_mostrar]

st.dataframe(df_ordenado, use_container_width=True)

# -------------------------
# Información adicional
# -------------------------
st.markdown("---")
st.markdown("🔄 **Los datos se actualizan automáticamente cada 3 horas y media**")

with st.expander("ℹ️ Información sobre las columnas detectadas"):
    st.write("**Columnas detectadas automáticamente:**")
    if fecha_col:
        st.write(f"📅 **Fecha:** {fecha_col}")
    if equipo_cols:
        st.write(f"⚽ **Equipos:** {', '.join(equipo_cols)}")
    if liga_cols:
        st.write(f"🏆 **Liga/Competición:** {', '.join(liga_cols)}")
    if prediccion_cols:
        st.write(f"🎯 **Predicción:** {', '.join(prediccion_cols)}")
    if cuota_cols:
        st.write(f"💱 **Cuota:** {', '.join(cuota_cols)}")
    if resultado_cols:
        st.write(f"📊 **Resultado:** {', '.join(resultado_cols)}")
    if profit_cols:
        st.write(f"💰 **Profit:** {', '.join(profit_cols)}")
