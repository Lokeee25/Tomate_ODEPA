import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from io import BytesIO
from datetime import datetime

# --- CONFIGURACIÓN GENERAL ---
st.set_page_config(page_title="Tomate ODEPA", layout="wide")
st.title("🍅 Dashboard de Precios - ODEPA")

# === CONFIGURACIÓN ===
# URL del archivo JSON con el índice histórico (desde tu carpeta Drive pública)
INDEX_URL = "https://drive.google.com/uc?export=download&id=1-xLlbd8gEtnUWMp0CGp6gbzssTL60EdM"

# --- FUNCIONES ---
@st.cache_data(ttl=600)
def cargar_index(url):
    """Carga el JSON con la lista de archivos disponibles."""
    try:
        data = requests.get(url).json()
        if isinstance(data, dict):
            data = [data]
        return sorted(data, key=lambda x: x["fecha"], reverse=True)
    except Exception as e:
        raise ValueError(f"No se pudo leer el JSON: {e}")

@st.cache_data(ttl=600)
def leer_excel(url, hoja="Hortalizas_Lo Valledor", skiprows=8):
    """Lee un archivo Excel desde Drive y devuelve un DataFrame limpio."""
    try:
        r = requests.get(url)
        r.raise_for_status()
        return pd.read_excel(BytesIO(r.content), sheet_name=hoja, skiprows=skiprows, engine="openpyxl")
    except Exception as e:
        raise ValueError(f"Error al leer Excel: {e}")

# --- CARGAR JSON HISTÓRICO ---
try:
    index = cargar_index(INDEX_URL)
    fechas_disponibles = [i["fecha"] for i in index]
    st.sidebar.header("📅 Filtros de visualización")

    fecha_seleccionada = st.sidebar.selectbox("Selecciona una fecha", fechas_disponibles)
    meta = next(item for item in index if item["fecha"] == fecha_seleccionada)

    st.sidebar.markdown(f"**Archivo seleccionado:** `{meta['nombre']}`")
    st.sidebar.markdown(f"[Descargar Excel]({meta['url_descarga']})")

    # --- CARGAR DATOS DEL EXCEL ---
    df = leer_excel(meta["url_descarga"])
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    # --- SELECCIÓN DE PRODUCTO ---
    col_producto = [c for c in df.columns if "producto" in c or "especie" in c]
    if not col_producto:
        st.error("No se encontró columna de producto o especie.")
    else:
        col_producto = col_producto[0]
        productos = sorted(df[col_producto].dropna().unique())
        producto_seleccionado = st.sidebar.selectbox("Selecciona un producto", productos)

        # Filtrar por producto
        df_filtrado = df[df[col_producto].str.contains(producto_seleccionado, case=False, na=False)]

        if df_filtrado.empty:
            st.warning("No se encontraron registros para ese producto.")
        else:
            # Buscar columnas relevantes
            col_precio = [c for c in df.columns if "precio" in c.lower()]
            col_variedad = [c for c in df.columns if "variedad" in c.lower()]
            col_origen = [c for c in df.columns if "origen" in c.lower()]
            col_volumen = [c for c in df.columns if "volumen" in c.lower()]

            # --- MÉTRICAS ---
            st.subheader(f"📊 Resumen para {producto_seleccionado} ({fecha_seleccionada})")

            if col_precio:
                col_precio = col_precio[0]
                precio_prom = df_filtrado[col_precio].mean()
                st.metric("💰 Precio promedio ($/kg)", f"{precio_prom:,.0f}")

            if col_volumen:
                col_volumen = col_volumen[0]
                volumen_total = df_filtrado[col_volumen].sum()
                st.metric("📦 Volumen total (kg)", f"{volumen_total:,.0f}")

            # --- GRÁFICOS ---
            if col_variedad:
                st.markdown("### 🌿 Precio promedio por variedad")
                df_var = (
                    df_filtrado.groupby(col_variedad[0])[col_precio].mean().reset_index()
                    .sort_values(col_precio, ascending=False)
                )
                fig1 = px.bar(df_var, x=col_variedad[0], y=col_precio, text_auto=".2s",
                              color=col_variedad[0], title="Precio promedio por variedad")
                st.plotly_chart(fig1, use_container_width=True)

            if col_origen:
                st.markdown("### 🗺️ Precio promedio por origen")
                df_ori = (
                    df_filtrado.groupby(col_origen[0])[col_precio].mean().reset_index()
                    .sort_values(col_precio, ascending=False)
                )
                fig2 = px.bar(df_ori, x=col_origen[0], y=col_precio, text_auto=".2s",
                              color=col_origen[0], title="Precio promedio por origen")
                st.plotly_chart(fig2, use_container_width=True)

            # --- DATOS HISTÓRICOS ---
            st.markdown("### 📈 Evolución histórica del producto")

            historico = []
            for item in index:
                try:
                    df_temp = leer_excel(item["url_descarga"])
                    df_temp.columns = [str(c).strip().lower().replace(" ", "_") for c in df_temp.columns]
                    if col_producto in df_temp.columns and col_precio in df_temp.columns:
                        mask = df_temp[col_producto].str.contains(producto_seleccionado, case=False, na=False)
                        precios = df_temp.loc[mask, col_precio]
                        if not precios.empty:
                            historico.append({"fecha": item["fecha"], "precio_prom": precios.mean()})
                except Exception:
                    continue

            if historico:
                df_hist = pd.DataFrame(historico)
                fig3 = px.line(df_hist, x="fecha", y="precio_prom", markers=True,
                               title=f"Evolución histórica de precios - {producto_seleccionado}")
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No hay datos históricos suficientes para este producto.")

except Exception as e:
    st.error(f"❌ Error al procesar los archivos: {e}")