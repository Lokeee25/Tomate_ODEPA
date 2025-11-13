import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from io import BytesIO

# --- CONFIGURACIÓN GENERAL ---
st.set_page_config(page_title="Precios ODEPA", layout="wide")
st.title("🍅 Comparador de precios ODEPA por mercado")

# === CONFIGURACIÓN ===
INDEX_URL = "https://drive.google.com/uc?export=download&id=1-xLlbd8gEtnUWMp0CGp6gbzssTL60EdM"  # index_archivos.json

# --- FUNCIONES AUXILIARES ---
@st.cache_data(ttl=600)
def cargar_index(url):
    data = requests.get(url).json()
    if isinstance(data, dict):
        data = [data]
    return sorted(data, key=lambda x: x["fecha"], reverse=True)

@st.cache_data(ttl=600)
def obtener_hojas(url):
    r = requests.get(url)
    xls = pd.ExcelFile(BytesIO(r.content))
    return [h for h in xls.sheet_names if "hortalizas" in h.lower()]

@st.cache_data(ttl=600)
def leer_hoja(url, hoja, skiprows=8):
    r = requests.get(url)
    df = pd.read_excel(BytesIO(r.content), sheet_name=hoja, skiprows=skiprows, engine="openpyxl")
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    df["mercado"] = hoja
    return df

# --- INTERFAZ ---
try:
    index = cargar_index(INDEX_URL)
    fechas_disponibles = [i["fecha"] for i in index]
    st.sidebar.header("📅 Filtros de visualización")

    fecha_seleccionada = st.sidebar.selectbox("Selecciona una fecha", fechas_disponibles)
    meta = next(item for item in index if item["fecha"] == fecha_seleccionada)

    hojas = obtener_hojas(meta["url_descarga"])
    st.sidebar.markdown(f"📘 **Archivo:** {meta['nombre']}")
    st.sidebar.markdown(f"[Descargar Excel]({meta['url_descarga']})")

    # Cargar todas las hojas (mercados)
    dataframes = []
    for hoja in hojas:
        try:
            df_temp = leer_hoja(meta["url_descarga"], hoja)
            dataframes.append(df_temp)
        except Exception:
            continue

    if not dataframes:
        st.error("No se pudieron leer los mercados del archivo.")
    else:
        df = pd.concat(dataframes, ignore_index=True)

        # --- SELECCIÓN DE PRODUCTO ---
        col_producto = [c for c in df.columns if "producto" in c or "especie" in c]
        col_precio = [c for c in df.columns if "precio" in c.lower()]
        col_variedad = [c for c in df.columns if "variedad" in c.lower()]
        col_origen = [c for c in df.columns if "origen" in c.lower()]
        col_volumen = [c for c in df.columns if "volumen" in c.lower()]

        if not col_producto or not col_precio:
            st.error("No se encontraron columnas de producto o precio.")
        else:
            col_producto, col_precio = col_producto[0], col_precio[0]

            productos = sorted(df[col_producto].dropna().unique())
            producto_sel = st.sidebar.selectbox("Selecciona un producto", productos)

            df_filtrado = df[df[col_producto].str.contains(producto_sel, case=False, na=False)]

            # --- MÉTRICAS COMPARATIVAS ---
            st.subheader(f"📊 Comparación de precios de **{producto_sel}** ({fecha_seleccionada})")

            df_comp = (
                df_filtrado.groupby("mercado")[col_precio]
                .mean()
                .reset_index()
                .sort_values(col_precio, ascending=False)
            )

            fig_comp = px.bar(
                df_comp,
                x="mercado",
                y=col_precio,
                color="mercado",
                text_auto=".2s",
                title=f"Precio promedio por mercado - {producto_sel}"
            )
            st.plotly_chart(fig_comp, use_container_width=True)

            # --- DETALLE INDIVIDUAL (seleccionable) ---
            mercado_sel = st.sidebar.selectbox("Ver detalle de un mercado específico", hojas)
            df_mercado = df_filtrado[df_filtrado["mercado"] == mercado_sel]

            if not df_mercado.empty:
                st.markdown(f"### 🏬 Detalle del mercado: {mercado_sel}")

                if col_variedad:
                    df_var = (
                        df_mercado.groupby(col_variedad[0])[col_precio].mean().reset_index()
                        .sort_values(col_precio, ascending=False)
                    )
                    fig1 = px.bar(
                        df_var,
                        x=col_variedad[0],
                        y=col_precio,
                        text_auto=".2s",
                        color=col_variedad[0],
                        title=f"Precio promedio por variedad ({mercado_sel})"
                    )
                    st.plotly_chart(fig1, use_container_width=True)

                if col_origen:
                    df_ori = (
                        df_mercado.groupby(col_origen[0])[col_precio].mean().reset_index()
                        .sort_values(col_precio, ascending=False)
                    )
                    fig2 = px.bar(
                        df_ori,
                        x=col_origen[0],
                        y=col_precio,
                        text_auto=".2s",
                        color=col_origen[0],
                        title=f"Precio promedio por origen ({mercado_sel})"
                    )
                    st.plotly_chart(fig2, use_container_width=True)

except Exception as e:
    st.error(f"❌ Error al procesar los archivos: {e}")