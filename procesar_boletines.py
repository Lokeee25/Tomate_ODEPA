import requests
import pandas as pd
import sqlite3
from io import BytesIO
import re
import os
import subprocess
from datetime import datetime

# ==============================
# CONFIG
# ==============================
DB_PATH = "boletines_odepa.db"
INDEX_URL = "https://drive.google.com/uc?export=download&id=19iTAfHR584pr63fECI1v0DjGgwRHh6pf"


# ==============================
# 1. Descargar índice JSON
# ==============================
def cargar_index():
    print("\n📥 Descargando índice de archivos desde Google Drive...")
    r = requests.get(INDEX_URL)

    try:
        data = r.json()
    except Exception:
        raise ValueError("❌ No se pudo leer el JSON del índice.")

    if isinstance(data, dict):
        data = [data]

    print(f"📑 {len(data)} boletines listados en el índice.")
    return data


# ==============================
# 2. Normalizar columnas
# ==============================
def normalizar_columnas(df):
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace(r"\n", "_", regex=True)
        .str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("utf-8")
    )
    return df


# ==============================
# 3. Adaptar columnas a formato estándar
# ==============================
def adaptar_columnas(df):
    mapa = {
        "producto": ["producto", "especie"],
        "variedad": ["variedad"],
        "calidad": ["calidad"],
        "volumen": ["volumen", "cantidad"],
        "precio_maximo": ["precio_maximo", "precio_max", "preciomaximo"],
        "precio_minimo": ["precio_minimo", "precio_min", "preciominimo"],
        "precio_promedio": ["precio_promedio", "precio_prom", "preciopromedio"],
        "unidad": ["unidad", "unidad_de_comercializacion"],
        "origen": ["origen"]
    }

    df_out = pd.DataFrame()

    for final_col, posibles in mapa.items():
        encontrada = next((p for p in posibles if p in df.columns), None)
        df_out[final_col] = df[encontrada] if encontrada else None

    return df_out


# ==============================
# 4. Descarga directa desde Google Drive
# ==============================
def descargar_excel(url):
    m = re.search(r"id=([^&]+)", url)
    if not m:
        print("❌ No se pudo extraer ID de Google Drive.")
        return None

    file_id = m.group(1)
    direct_url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"

    r = requests.get(direct_url)
    ctype = r.headers.get("Content-Type", "").lower()

    if "html" in ctype:
        print("❌ Google Drive bloqueó la descarga (archivo privado o token inválido).")
        return None

    return r.content


# ==============================
# 5. Procesar archivo Excel
# ==============================
def procesar_excel(url_excel, fecha):
    print(f"\n📄 Procesando boletín {fecha}...")

    raw = descargar_excel(url_excel)
    if raw is None:
        print(f"❌ No se pudo descargar el archivo del {fecha}.")
        return pd.DataFrame()

    try:
        xls = pd.ExcelFile(BytesIO(raw))
    except Exception:
        print(f"❌ ERROR: El archivo del {fecha} NO es un Excel válido.")
        return pd.DataFrame()

    hojas = [h for h in xls.sheet_names if "hortalizas" in h.lower()]

    if not hojas:
        print("⚠️ No se encontraron hojas 'hortalizas'.")
        return pd.DataFrame()

    registros = []

    for hoja in hojas:
        try:
            df = pd.read_excel(BytesIO(raw), sheet_name=hoja, skiprows=8, engine="openpyxl")
            df = normalizar_columnas(df)
            df = adaptar_columnas(df)

            df["mercado"] = hoja
            df["fecha_boletin"] = fecha

            registros.append(df)
            print(f"✔ {hoja}: {len(df)} filas procesadas")

        except Exception as e:
            print(f"⚠️ Error procesando hoja {hoja}: {e}")
            continue

    return pd.concat(registros, ignore_index=True) if registros else pd.DataFrame()


# ==============================
# 6. Guardar en SQLite con prevención de duplicados
# ==============================
def guardar_sqlite(df):
    if df.empty:
        print("⚠️ No se agregaron registros (dataframe vacío).")
        return

    conn = sqlite3.connect(DB_PATH)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS precios (
            producto TEXT,
            variedad TEXT,
            calidad TEXT,
            volumen REAL,
            precio_maximo REAL,
            precio_minimo REAL,
            precio_promedio REAL,
            unidad TEXT,
            origen TEXT,
            mercado TEXT,
            fecha_boletin TEXT
        )
    """)

    fecha = df["fecha_boletin"].iloc[0]
    cur = conn.execute("SELECT COUNT(*) FROM precios WHERE fecha_boletin = ?", (fecha,))
    exists = cur.fetchone()[0] > 0

    if exists:
        print(f"⛔ El boletín del {fecha} YA existe. No se inserta.")
        conn.close()
        return

    df.to_sql("precios", conn, if_exists="append", index=False)
    conn.close()
    print(f"✅ {len(df)} registros agregados a SQLite (fecha {fecha}).")


# ==============================
# 7. Script principal
# ==============================
def procesar_boletines():
    index = cargar_index()
    for meta in index:
        df = procesar_excel(meta["url_descarga"], meta["fecha"])
        guardar_sqlite(df)


# ==============================
# 8. Auto-commit para GitHub Actions
# ==============================
def git_push():
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"Actualización automática {now}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✔ Cambios enviados a GitHub")
    except Exception as e:
        print("❌ Error al hacer git push:", e)


# ==============================
# Ejecución
# ==============================
if __name__ == "__main__":
    procesar_boletines()

    # Solo hacer push si estamos en GitHub Actions
    if os.getenv("GITHUB_ACTIONS") == "true":
        git_push()
