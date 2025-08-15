import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# Configuración de la página
st.set_page_config(
    page_title="Football Model Tracker",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
.metric-card {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid #1f77b4;
}
.success-metric {
    border-left-color: #2ca02c;
}
.warning-metric {
    border-left-color: #ff7f0e;
}
.error-metric {
    border-left-color: #d62728;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Carga los datos del archivo Excel"""
    try:
        df = pd.read_excel('predictions_tracker.xlsx')
        # Asegurar que las columnas de fecha estén en formato datetime
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        elif 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
        return df
    except FileNotFoundError:
        st.error("⚠️ No se encontró el archivo predictions_tracker.xlsx")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al cargar los datos: {str(e)}")
        return pd.DataFrame()

def calculate_metrics(df):
    """Calcula métricas principales"""
    if df.empty:
        return {}
    
    # Adaptar según las columnas reales de tu Excel
    metrics = {}
    
    # Buscar columnas que puedan contener resultados/predicciones
    prediction_cols = [col for col in df.columns if any(word in col.lower() for word in ['prediction', 'pred', 'forecast'])]
    result_cols = [col for col in df.columns if any(word in col.lower() for word in ['result', 'actual', 'real'])]
    
    if prediction_cols and result_cols:
        # Calcular accuracy si hay columnas de predicción y resultado
        correct_predictions = (df[prediction_cols[0]] == df[result_cols[0]]).sum()
        total_predictions = len(df)
        metrics['accuracy'] = correct_predictions / total_predictions * 100 if total_predictions > 0 else 0
    
    metrics['total_predictions'] = len(df)
    metrics['last_update'] = df['date'].max() if 'date' in df.columns else (df['Date'].max() if 'Date' in df.columns else 'N/A')
    
    return metrics

def main():
    # Título principal
    st.title("⚽ Football Model Results Tracker")
    st.markdown("---")
    
    # Cargar datos
    df = load_data()
    
    if df.empty:
        st.warning("No hay datos disponibles para mostrar.")
        return
    
    # Sidebar con filtros
    st.sidebar.header("🔧 Filtros")
    
    # Mostrar información básica sobre los datos
    st.sidebar.subheader("📊 Información del Dataset")
    st.sidebar.write(f"**Total de registros:** {len(df)}")
    st.sidebar.write(f"**Columnas:** {len(df.columns)}")
    
    # Filtro por fechas (si existe columna de fecha)
    date_col = 'date' if 'date' in df.columns else ('Date' if 'Date' in df.columns else None)
    if date_col:
        min_date = df[date_col].min()
        max_date = df[date_col].max()
        
        date_range = st.sidebar.date_input(
            "Rango de fechas",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        if len(date_range) == 2:
            df_filtered = df[(df[date_col] >= pd.to_datetime(date_range[0])) & 
                           (df[date_col] <= pd.to_datetime(date_range[1]))]
        else:
            df_filtered = df
    else:
        df_filtered = df
    
    # Filtros adicionales basados en las columnas disponibles
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    
    for col in categorical_cols[:3]:  # Mostrar máximo 3 filtros categóricos
        unique_values = df[col].dropna().unique()
        if len(unique_values) <= 20:  # Solo mostrar si hay pocas categorías únicas
            selected_values = st.sidebar.multiselect(
                f"Filtrar por {col}",
                options=unique_values,
                default=unique_values
            )
            df_filtered = df_filtered[df_filtered[col].isin(selected_values)]
    
    # Métricas principales
    metrics = calculate_metrics(df_filtered)
    
    # Dashboard principal
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📊 Total Predicciones",
            value=metrics.get('total_predictions', 0)
        )
    
    with col2:
        accuracy = metrics.get('accuracy', 0)
        st.metric(
            label="🎯 Accuracy",
            value=f"{accuracy:.1f}%" if accuracy > 0 else "N/A"
        )
    
    with col3:
        st.metric(
            label="📅 Última Actualización",
            value=metrics.get('last_update', 'N/A').strftime('%Y-%m-%d') if isinstance(metrics.get('last_update'), pd.Timestamp) else str(metrics.get('last_update', 'N/A'))
        )
    
    with col4:
        st.metric(
            label="📈 Registros Filtrados",
            value=len(df_filtered)
        )
    
    st.markdown("---")
    
    # Tabs para diferentes vistas
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📋 Datos", "📈 Gráficos", "🔍 Análisis"])
    
    with tab1:
        st.subheader("Dashboard Principal")
        
        # Gráfico de tendencia temporal (si hay columna de fecha)
        if date_col and len(df_filtered) > 1:
            # Agrupar por fecha para ver tendencias
            daily_stats = df_filtered.groupby(df_filtered[date_col].dt.date).size().reset_index()
            daily_stats.columns = ['date', 'predictions']
            
            fig_trend = px.line(
                daily_stats, 
                x='date', 
                y='predictions',
                title="📈 Predicciones por Día",
                color_discrete_sequence=['#1f77b4']
            )
            fig_trend.update_layout(height=400)
            st.plotly_chart(fig_trend, use_container_width=True)
        
        # Distribución de columnas numéricas
        numeric_cols = df_filtered.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols:
            col_selected = st.selectbox("Selecciona una columna para analizar:", numeric_cols)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Histograma
                fig_hist = px.histogram(
                    df_filtered, 
                    x=col_selected,
                    title=f"📊 Distribución de {col_selected}",
                    color_discrete_sequence=['#2ca02c']
                )
                st.plotly_chart(fig_hist, use_container_width=True)
            
            with col2:
                # Box plot
                fig_box = px.box(
                    df_filtered, 
                    y=col_selected,
                    title=f"📦 Box Plot de {col_selected}",
                    color_discrete_sequence=['#ff7f0e']
                )
                st.plotly_chart(fig_box, use_container_width=True)
    
    with tab2:
        st.subheader("📋 Datos Completos")
        st.write(f"Mostrando {len(df_filtered)} registros de {len(df)} totales")
        
        # Mostrar dataframe con paginación
        st.dataframe(
            df_filtered,
            use_container_width=True,
            height=400
        )
        
        # Opción de descarga
        csv = df_filtered.to_csv(index=False)
        st.download_button(
            label="📥 Descargar datos filtrados (CSV)",
            data=csv,
            file_name=f"football_predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    with tab3:
        st.subheader("📈 Visualizaciones")
        
        # Permitir crear gráficos personalizados
        chart_type = st.selectbox(
            "Tipo de gráfico:",
            ["Dispersión", "Barras", "Línea", "Torta"]
        )
        
        numeric_cols = df_filtered.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df_filtered.select_dtypes(include=['object']).columns.tolist()
        
        if chart_type == "Dispersión" and len(numeric_cols) >= 2:
            x_col = st.selectbox("Eje X:", numeric_cols)
            y_col = st.selectbox("Eje Y:", [col for col in numeric_cols if col != x_col])
            
            fig = px.scatter(df_filtered, x=x_col, y=y_col, title=f"{x_col} vs {y_col}")
            st.plotly_chart(fig, use_container_width=True)
        
        elif chart_type == "Barras" and categorical_cols:
            cat_col = st.selectbox("Columna categórica:", categorical_cols)
            
            value_counts = df_filtered[cat_col].value_counts().head(10)
            fig = px.bar(
                x=value_counts.index,
                y=value_counts.values,
                title=f"Distribución de {cat_col}"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        elif chart_type == "Torta" and categorical_cols:
            cat_col = st.selectbox("Columna para gráfico de torta:", categorical_cols)
            
            value_counts = df_filtered[cat_col].value_counts().head(8)
            fig = px.pie(
                values=value_counts.values,
                names=value_counts.index,
                title=f"Proporción de {cat_col}"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.subheader("🔍 Análisis Detallado")
        
        # Estadísticas descriptivas
        if not df_filtered.empty:
            st.write("**Estadísticas Descriptivas:**")
            st.dataframe(df_filtered.describe(), use_container_width=True)
            
            # Información sobre valores nulos
            null_counts = df_filtered.isnull().sum()
            if null_counts.sum() > 0:
                st.write("**Valores Nulos por Columna:**")
                null_df = pd.DataFrame({
                    'Columna': null_counts.index,
                    'Valores Nulos': null_counts.values,
                    'Porcentaje': (null_counts.values / len(df_filtered) * 100).round(2)
                }).sort_values('Valores Nulos', ascending=False)
                st.dataframe(null_df[null_df['Valores Nulos'] > 0], use_container_width=True)
            
            # Correlaciones (solo para columnas numéricas)
            numeric_df = df_filtered.select_dtypes(include=[np.number])
            if len(numeric_df.columns) > 1:
                st.write("**Matriz de Correlación:**")
                corr_matrix = numeric_df.corr()
                fig_corr = px.imshow(
                    corr_matrix,
                    title="Matriz de Correlación",
                    color_continuous_scale='RdBu_r',
                    aspect="auto"
                )
                st.plotly_chart(fig_corr, use_container_width=True)
    
    # Footer
    st.markdown("---")
    st.markdown("🔄 Los datos se actualizan automáticamente cada 4 horas")

if __name__ == "__main__":
    main()
