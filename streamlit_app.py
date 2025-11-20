import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# --- CONFIGURACIÓN GENERAL ---
st.set_page_config(page_title="Precios ODEPA", layout="wide")
st.title(" Comparador de precios ODEPA (Datos históricos SQLite)")

DB_PATH = "boletines_odepa.db"
TABLE = "precios"


# --- TEMA DE DISEÑO GLOBAL PARA TODOS LOS GRÁFICOS ---
def aplicar_tema(fig):
    fig.update_traces(
        marker=dict(
            line=dict(width=0.6, color="black")  # bordes suaves
        )
    )
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        template="simple_white",
        legend_title="",
        font=dict(size=14),
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="lightgray")
    )
    return fig


# --- FUNCIONES AUXILIARES ---
@st.cache_data(ttl=300)
def cargar_datos():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(f"SELECT * FROM {TABLE}", conn)
    conn.close()

    df.columns = [c.lower().strip() for c in df.columns]

    if "fecha_boletin" in df.columns:
        df["fecha"] = df["fecha_boletin"]

    df["fecha"] = pd.to_datetime(df["fecha"])

    # 🔧 LIMPIEZA: eliminar prefijo "hortalizas_"
    if "mercado" in df.columns:
        df["mercado"] = df["mercado"].astype(str)
        df["mercado"] = df["mercado"].str.replace("hortalizas_", "", regex=False)

    return df


# --- INTERFAZ ---
try:
    df = cargar_datos()

    required_cols = ["fecha", "mercado", "producto", "precio_promedio"]
    for col in required_cols:
        if col not in df.columns:
            st.error(f"❌ Falta la columna requerida: {col}")
            st.stop()

    # ========== FILTROS ==========
    st.sidebar.header("📅 Filtros de visualización")

    productos = sorted(df["producto"].dropna().unique())
    producto_sel = st.sidebar.selectbox("Selecciona un producto", productos)

    mercados = sorted(df["mercado"].unique())
    mercado_sel = st.sidebar.multiselect("Mercados", mercados, default=mercados)

    fechas = sorted(df["fecha"].dt.date.unique(), reverse=True)
    fecha_sel = st.sidebar.selectbox("Selecciona una fecha", fechas)

    # Filtrar para gráfico diario
    df_dia = df[df["fecha"].dt.date == fecha_sel]
    df_dia = df_dia[df_dia["mercado"].isin(mercado_sel)]
    df_dia = df_dia[df_dia["producto"].str.contains(producto_sel, case=False, na=False)]

    # ========== GRÁFICA GENERAL ==========
    st.subheader(f"📊 Comparación de precios de **{producto_sel}** ({fecha_sel})")

    if not df_dia.empty:
        df_comp = (
            df_dia.groupby("mercado")["precio_promedio"]
            .mean()
            .reset_index()
            .sort_values("precio_promedio", ascending=False)
        )

        fig = px.bar(
            df_comp,
            x="mercado",
            y="precio_promedio",
            text_auto=".2s",
            color="mercado",
            title=f"Precio promedio por mercado – {producto_sel}",
            color_discrete_sequence=px.colors.qualitative.Set2
        )

        fig = aplicar_tema(fig)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay datos diarios para ese producto en esos mercados.")

    # ========== EVOLUCIÓN HISTÓRICA ==========
    st.subheader("📈 Evolución histórica del precio")

    df_hist = df[df["producto"].str.contains(producto_sel, case=False, na=False)]
    df_hist = df_hist[df_hist["mercado"].isin(mercado_sel)]

    if not df_hist.empty:

        df_hist = (
            df_hist.groupby(["fecha", "mercado"])["precio_promedio"]
            .mean()
            .reset_index()
        )

        fig_hist = px.line(
            df_hist,
            x="fecha",
            y="precio_promedio",
            color="mercado",
            markers=True,
            title=f"Evolución histórica del precio – {producto_sel}",
            color_discrete_sequence=px.colors.qualitative.Set2
        )

        fig_hist = aplicar_tema(fig_hist)
        st.plotly_chart(fig_hist, use_container_width=True)

    else:
        st.warning("No hay datos históricos para ese producto en esos mercados.")

    # ========== DETALLE POR MERCADO ==========
    st.subheader("🏬 Detalle por mercado")

    mercado_det = st.sidebar.selectbox("Selecciona mercado para detalle", mercados)
    df_det = df_dia[df_dia["mercado"] == mercado_det]

    if not df_det.empty:

        # -------- Variedad --------
        if "variedad" in df_det.columns:
            df_var = (
                df_det.groupby("variedad")["precio_promedio"]
                .mean()
                .reset_index()
            )
            fig_v = px.bar(
                df_var, x="variedad", y="precio_promedio",
                text_auto=".2s",
                title=f"Precio por variedad - {mercado_det}",
                color_discrete_sequence=px.colors.qualitative.Pastel1
            )
            fig_v = aplicar_tema(fig_v)
            st.plotly_chart(fig_v, use_container_width=True)

        # -------- Origen --------
        if "origen" in df_det.columns:
            df_ori = (
                df_det.groupby("origen")["precio_promedio"]
                .mean()
                .reset_index()
            )
            fig_o = px.bar(
                df_ori, x="origen", y="precio_promedio",
                text_auto=".2s",
                title=f"Precio por origen - {mercado_det}",
                color_discrete_sequence=px.colors.qualitative.Pastel2
            )
            fig_o = aplicar_tema(fig_o)
            st.plotly_chart(fig_o, use_container_width=True)

except Exception as e:
    st.error(f"❌ Error al procesar los datos: {e}")