import streamlit as st
import pandas as pd
import requests
import json
from io import BytesIO
from datetime import datetime
import plotly.express as px

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="📊 ODEPA - Dashboard de productos", layout="wide", page_icon="🍅")
st.title("📊 Dashboard histórico ODEPA - Hortalizas Lo Valledor")

# === URL DEL ÍNDICE JSON (generado por tu Google Script) ===
INDEX_URL = "https://drive.google.com/uc?export=download&id=1VgfxrxFb3lv8j71MOoUACeleLbo81IAw"  # 👈 reemplázalo por el ID real

# --- FUNCIONES AUXILIARES ---
@st.cache_data
def obtener_archivos_desde_json(index_url):
    """Lee el índice JSON con los metadatos de todos los boletines descargados."""
    try:
        r = requests.get(index_url, timeout=15)
        if r.status_code != 200:
            raise ValueError(f"Error HTTP {r.status_code} al acceder al índice.")
        content = r.text.strip()
        if not content or content.startswith("<!DOCTYPE"):
            raise ValueError("Drive devolvió HTML en lugar del JSON. Verifica que sea público.")
        data = json.loads(content)
        if not isinstance(data, list):
            raise ValueError("El índice JSON no tiene formato de lista.")
        return data
    except Exception as e:
        raise ValueError(f"No se pudo leer el índice: {e}")

@st.cache_data
def leer_excel(url, hoja="Hortalizas_Lo Valledor", skiprows=8):
    """Descarga y lee un archivo Excel desde una URL de descarga directa."""
    r = requests.get(url, allow_redirects=True, timeout=20)
    content_type = r.headers.get("Content-Type", "")
    primeros_bytes = r.content[:100]

    if "html" in content_type.lower() or primeros_bytes.startswith(b"<!DOCTYPE"):
        raise ValueError("Drive devolvió HTML en lugar de Excel (verifica permisos).")

    try:
        df = pd.read_excel(BytesIO(r.content), sheet_name=hoja, skiprows=skiprows, engine="openpyxl")
        return df
    except Exception as e:
        raise ValueError(f"Error al leer Excel: {e}")

# --- PROCESAMIENTO PRINCIPAL ---
try:
    # Cargar lista de archivos desde el JSON
    archivos = obtener_archivos_desde_json(INDEX_URL)

    if not archivos:
        st.error("❌ No se encontraron boletines en el índice JSON.")
        st.stop()

    # Mostrar el último boletín en el sidebar
    ultimo = archivos[0]
    st.sidebar.info(f"🗓️ Último boletín: {ultimo['fecha']}")
    st.sidebar.write(f"📄 Archivo: {ultimo['nombre']}")

    # Construir histórico
    historico = []
    for meta in archivos:
        try:
            url = meta["url_descarga"]
            df = leer_excel(url)
            df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
            df["fecha_boletin"] = meta["fecha"]
            historico.append(df)
        except Exception as e:
            st.warning(f"⚠️ Error al leer {meta['nombre']}: {e}")

    if not historico:
        st.warning("⚠️ No se encontró información en los boletines.")
        st.stop()

    # Combinar todos los boletines
    df_hist = pd.concat(historico, ignore_index=True)
    st.success(f"✅ Histórico cargado: {df_hist['fecha_boletin'].nunique()} días, {len(df_hist)} registros totales.")

    # --- DETECCIÓN AUTOMÁTICA DE COLUMNAS ---
    col_producto = next((c for c in df_hist.columns if "producto" in c or "especie" in c), None)
    col_variedad = next((c for c in df_hist.columns if "variedad" in c), None)
    col_precio = next((c for c in df_hist.columns if "precio" in c), None)
    col_volumen = next((c for c in df_hist.columns if "volumen" in c), None)
    col_origen = next((c for c in df_hist.columns if "origen" in c), None)

    if not col_producto or not col_precio:
        st.error("❌ No se detectaron columnas de producto o precio en los boletines.")
        st.stop()

    # --- FILTRO DE PRODUCTO ---
    productos = sorted(df_hist[col_producto].dropna().unique())
    producto_sel = st.selectbox("🥕 Selecciona un producto", productos)

    df_prod = df_hist[df_hist[col_producto] == producto_sel]

    # --- FILTRO DE VARIEDAD ---
    if col_variedad:
        variedades = sorted(df_prod[col_variedad].dropna().unique())
        variedad_sel = st.selectbox("🍅 Selecciona variedad (opcional)", ["Todas"] + variedades)
        if variedad_sel != "Todas":
            df_prod = df_prod[df_prod[col_variedad] == variedad_sel]

    # --- FILTRO DE ORIGEN ---
    if col_origen:
        origenes = sorted(df_prod[col_origen].dropna().unique())
        origen_sel = st.multiselect("🌍 Selecciona origen (opcional)", origenes, default=origenes)
        df_prod = df_prod[df_prod[col_origen].isin(origen_sel)]

    # --- GRÁFICOS ---
    if col_precio:
        fig_precio = px.line(
            df_prod.groupby("fecha_boletin")[col_precio].mean().reset_index(),
            x="fecha_boletin", y=col_precio,
            title=f"📈 Evolución del precio promedio de {producto_sel}",
            markers=True,
        )
        st.plotly_chart(fig_precio, use_container_width=True)

    if col_volumen:
        fig_volumen = px.bar(
            df_prod.groupby("fecha_boletin")[col_volumen].sum().reset_index(),
            x="fecha_boletin", y=col_volumen,
            title=f"📦 Volumen comercializado de {producto_sel}"
        )
        st.plotly_chart(fig_volumen, use_container_width=True)

    # --- TABLA DETALLADA ---
    with st.expander("📋 Ver tabla completa"):
        st.dataframe(df_prod, use_container_width=True)

except Exception as e:
    st.error(f"❌ Error al procesar los archivos: {e}")