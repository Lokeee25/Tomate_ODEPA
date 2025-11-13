import streamlit as st
import pandas as pd
import sqlite3
import requests
import re
from datetime import datetime
from io import BytesIO

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="Tomate ODEPA", layout="wide")
st.title("🍅 Dashboard de precios ODEPA (Base de datos SQLite)")

# ID de tu carpeta pública de Google Drive
FOLDER_ID = "16h5aEuSqTzVCRUqAht0eFrNTrBMamDEE"
URL_EMBED = f"https://drive.google.com/embeddedfolderview?id={FOLDER_ID}#grid"

# --- FUNCIONES AUXILIARES ---
@st.cache_data
def obtener_ultimo_db(folder_url):
    """Obtiene el archivo más reciente (SQLite) por fecha desde una carpeta pública de Drive."""
    html = requests.get(folder_url).text
    matches = re.findall(r'href="https://drive.google.com/file/d/(.*?)/view', html)
    nombres = re.findall(r'<div class="flip-entry-title">(.*?)</div>', html)

    if not nombres or not matches:
        raise ValueError("No se encontraron archivos visibles en la carpeta.")

    archivos = [(n, i) for n, i in zip(nombres, matches) if n.endswith((".db", ".sqlite", ".xlsx"))]
    if not archivos:
        raise ValueError("No se encontraron archivos de base de datos en la carpeta.")

    def extraer_fecha(nombre):
        m = re.search(r"\d{4}-\d{2}-\d{2}", nombre)
        return datetime.strptime(m.group(), "%Y-%m-%d") if m else datetime.min

    # Seleccionar el más reciente
    nombre, file_id = sorted(archivos, key=lambda x: extraer_fecha(x[0]), reverse=True)[0]
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    return nombre, download_url

def leer_sqlite_drive(download_url):
    """Descarga y lee una base SQLite pública desde Drive."""
    r = requests.get(download_url)
    if "text/html" in r.headers.get("Content-Type", ""):
        raise ValueError("Drive devolvió HTML. Verifica permisos o formato del archivo.")

    # Guardar temporalmente el archivo en memoria
    db_bytes = BytesIO(r.content)

    # Crear conexión SQLite en memoria
    with sqlite3.connect(":memory:") as conn:
        conn.executescript("ATTACH DATABASE ':memory:' AS temp_db;")  # opcional
        with open("temp_db.sqlite", "wb") as f:
            f.write(db_bytes.getbuffer())
        conn_det = sqlite3.connect("temp_db.sqlite")
        tablas = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn_det)
        tabla = tablas.iloc[0, 0]
        df = pd.read_sql(f"SELECT * FROM {tabla}", conn_det)
        conn_det.close()
    return df

# --- EJECUCIÓN PRINCIPAL ---
try:
    nombre, download_url = obtener_ultimo_db(URL_EMBED)
    st.write(f"📦 Base más reciente encontrada: **{nombre}**")

    df = leer_sqlite_drive(download_url)
    st.success(f"✅ Datos cargados correctamente ({len(df)} filas).")

    st.dataframe(df.head())

    # --- FILTRO DE TOMATE ---
    col_especie = [c for c in df.columns if "especie" in c.lower() or "producto" in c.lower()]
    if col_especie:
        col_especie = col_especie[0]
        df_tomate = df[df[col_especie].str.contains("tomate", case=False, na=False)]

        if not df_tomate.empty:
            # Buscar columna de precios
            col_precio = [c for c in df.columns if "precio" in c.lower()]
            if col_precio:
                col_precio = col_precio[0]
                st.subheader("📊 Promedio de precios del tomate")
                st.metric("Precio promedio ($/kg)", round(df_tomate[col_precio].mean(), 1))
            else:
                st.warning("No se encontró columna de precios.")
        else:
            st.warning("No hay registros de tomate en la base.")
    else:
        st.warning("No se encontró columna de especie o producto.")

except Exception as e:
    st.error(f"❌ Error al cargar o procesar el archivo: {e}")