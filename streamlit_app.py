import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Tomate ODEPA", layout="wide")
st.title("🍅 Dashboard de precios ODEPA")

# --- ID del archivo Excel en tu Google Drive ---
FILE_ID = "1Xsl4Y8sBNMZK4rJMrNSWNqcp6EiPDWFx"   # 👈 reemplaza con el tuyo
URL = f"https://drive.google.com/uc?id={FILE_ID}"

st.write("📥 Cargando datos desde Google Drive...")

try:
    # Lee hoja y parte desde la fila 9 (header=8 → fila 9)
    df = pd.read_excel(URL, sheet_name="Hortalizas_Lo Valledor", header=8)
    st.success("✅ Archivo cargado correctamente desde Drive.")
    st.dataframe(df.head())

    # Normaliza nombres de columnas
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    # Busca la columna de especie / producto
    col_especie = next((c for c in df.columns if "especie" in c or "producto" in c), None)

    if col_especie:
        df_tomate = df[df[col_especie].str.contains("tomate", case=False, na=False)].copy()
        st.subheader("📊 Registros de tomate")
        st.dataframe(df_tomate)

        # --- Graficar precios promedio por variedad y origen ---
        posibles_precio = [c for c in df_tomate.columns if "precio" in c]
        if posibles_precio:
            col_precio = posibles_precio[0]
            # Buscar columnas auxiliares
            col_variedad = next((c for c in df_tomate.columns if "variedad" in c), None)
            col_origen = next((c for c in df_tomate.columns if "origen" in c), None)

            # Precio promedio
            st.metric("💰 Precio promedio tomate", f"${df_tomate[col_precio].mean():,.0f}")

            # Gráfico por variedad
            if col_variedad:
                st.subheader("📈 Precio promedio por variedad")
                graf_var = df_tomate.groupby(col_variedad)[col_precio].mean().sort_values(ascending=False)
                st.bar_chart(graf_var)

            # Gráfico por origen
            if col_origen:
                st.subheader("📊 Precio promedio por origen")
                graf_ori = df_tomate.groupby(col_origen)[col_precio].mean().sort_values(ascending=False)
                st.bar_chart(graf_ori)
        else:
            st.warning("⚠️ No se encontró columna de precios.")
    else:
        st.warning("⚠️ No se encontró columna con 'producto' o 'especie'.")
except Exception as e:
    st.error(f"❌ Error al cargar el archivo: {e}")