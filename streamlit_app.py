import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Tomate ODEPA", layout="wide")

st.title("🍅 Dashboard de precios ODEPA")

uploaded_file = st.file_uploader("📤 Sube el archivo Excel diario de ODEPA", type=["xlsx", "xls", "csv"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.write("✅ Archivo cargado correctamente.")
    st.dataframe(df.head())

    # Filtrar tomates (si existe la columna)
    columnas = [c.lower() for c in df.columns]
    if any("especie" in c or "producto" in c for c in columnas):
        col_especie = [c for c in df.columns if "especie" in c or "producto" in c][0]
        df_tomate = df[df[col_especie].str.contains("tomate", case=False, na=False)]
        st.subheader("📈 Datos de tomate")
        st.dataframe(df_tomate)

        # Graficar precios promedio
        if "precio" in " ".join(columnas):
            col_precio = [c for c in df.columns if "precio" in c][0]
            precio_prom = df_tomate[col_precio].mean()
            st.metric("Precio promedio tomate", f"${precio_prom:,.0f}")
    else:
        st.warning("⚠️ No se encontró columna con 'producto' o 'especie'.")
else:
    st.info("📥 Sube el boletín diario para comenzar.")