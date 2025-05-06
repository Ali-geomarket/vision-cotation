import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import geopandas as gpd
from shapely.geometry import Point
from pathlib import Path
import zipfile
import tempfile
import os

# --- Configuration initiale ---
st.set_page_config(page_title="Vision Cotation", layout="centered")

# --- Données utilisateurs pour connexion ---
USERS = {"sg": "dri", "ps": "dri", "equipe.cotation": "Covage.2025&"}

# --- Initialisation des états ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "main_page" not in st.session_state:
    st.session_state["main_page"] = "login"
if "upload_key" not in st.session_state:
    st.session_state["upload_key"] = "file_uploader_0"

# --- PAGE : Connexion ---
if not st.session_state["authenticated"]:
    st.title("Connexion")
    with st.form("login_form"):
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        if st.form_submit_button("Se connecter"):
            if USERS.get(username) == password:
                st.session_state["authenticated"] = True
                st.session_state["main_page"] = "home"
                st.rerun()
            else:
                st.error("Identifiants incorrects")
    st.stop()

# --- PAGE : Accueil ---
if st.session_state["main_page"] == "home":
    st.title("Bienvenue - Vision cotation")
    st.write("Que souhaitez-vous faire ?")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Récupérer le MA regroupé"):
            st.session_state["main_page"] = "ma_regroupe"
            st.session_state["ma_regroupe_result"] = None
            st.session_state["upload_key"] = "file_uploader_0"
            st.rerun()
    with col2:
        if st.button("Transformer GeoJSON en KMZ"):
            st.session_state["main_page"] = "geojson_to_kmz"
            st.session_state["kmz_result"] = None
            st.session_state["kmz_filename"] = None
            st.session_state["upload_key"] = "file_uploader_geojson_0"
            st.rerun()

# --- PAGE : MA regroupé ---
elif st.session_state["main_page"] == "ma_regroupe":
    st.title("Marché Adressable regroupé")

    if st.button("Retour"):
        st.session_state["main_page"] = "home"
        st.rerun()

    uploaded_file = st.file_uploader("Déposez un fichier CSV ou Excel", type=["csv", "xlsx"], key=st.session_state["upload_key"])

    if uploaded_file:
        try:
            if uploaded_file.name.endswith(".xlsx"):
                df = pd.read_excel(uploaded_file, dtype=str)
            else:
                raw_data = uploaded_file.read()
                try:
                    content = raw_data.decode("utf-8")
                except UnicodeDecodeError:
                    content = raw_data.decode("latin1")
                sep = ";" if content.count(";") > content.count(",") else ","
                df = pd.read_csv(BytesIO(raw_data), sep=sep, dtype=str)

            def regrouper_tranches(val):
                if isinstance(val, str):
                    if any(val.startswith(code) for code in ["02", "03"]):
                        return "1 A 5 SALARIES"
                    elif any(val.startswith(code) for code in ["04", "05", "06"]):
                        return "6 A 49 SALARIES"
                    elif val.startswith(("07", "08", "09", "10", "11", "12", "13", "14", "15")):
                        return "49 ET PLUS SALARIES"
                return None

            df["TRANCHE_REGROUPÉE"] = df["NB_SALARIE_FIN"].apply(regrouper_tranches)

            if st.button("Afficher le MA regroupé"):
                df["SIRET_BOA"] = df["SIRET_BOA"].astype(str)
                regroupement = pd.pivot_table(
                    df[df["TRANCHE_REGROUPÉE"].notnull()],
                    index="TRANCHE_REGROUPÉE",
                    values="SIRET_BOA",
                    aggfunc="count",
                    margins=True,
                    margins_name="Total général"
                ).rename(columns={"SIRET_BOA": "NOMBRE ENTREPRISES"})

                ordered_index = ["1 A 5 SALARIES", "6 A 49 SALARIES", "49 ET PLUS SALARIES", "Total général"]
                regroupement = regroupement.reindex(ordered_index)
                st.session_state["ma_regroupe_result"] = regroupement
                st.rerun()

        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier : {e}")

    if st.session_state.get("ma_regroupe_result") is not None:
        st.subheader("Résultat – Marché Adressable regroupé")
        st.dataframe(st.session_state["ma_regroupe_result"])

        buf = BytesIO()
        fig, ax = plt.subplots(figsize=(10, 3))
        ax.axis('off')
        table_data = [[idx] + list(row) for idx, row in st.session_state["ma_regroupe_result"].iterrows()]
        col_labels = ["TRANCHE"] + st.session_state["ma_regroupe_result"].columns.to_list()
        table = ax.table(cellText=table_data, colLabels=col_labels, loc='center')
        table.scale(1, 2)
        plt.savefig(buf, format="png", bbox_inches="tight", dpi=300)
        buf.seek(0)

        st.download_button(
            label="Télécharger l'image du MA regroupé",
            data=buf,
            file_name="MA_regroupe.png",
            mime="image/png"
        )

        if st.button("Renouveler l'opération"):
            st.session_state["ma_regroupe_result"] = None
            current_key = int(st.session_state["upload_key"].split("_")[-1])
            st.session_state["upload_key"] = f"file_uploader_{current_key + 1}"
            st.rerun()

# --- PAGE : GEOJSON ➜ KMZ ---
elif st.session_state["main_page"] == "geojson_to_kmz":
    st.title("Transformation GeoJSON ➜ KMZ")

    if st.button("Retour"):
        st.session_state["main_page"] = "home"
        st.rerun()

    uploaded_file = st.file_uploader("Déposez un fichier GeoJSON", type=["geojson"], key=st.session_state["upload_key"])

    if uploaded_file:
        st.success("Fichier chargé. Cliquez ci-dessous pour lancer la conversion.")

        filename_stem = Path(uploaded_file.name).stem

        if st.button("Transformer le fichier en KMZ"):
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    temp_geojson = Path(tmpdir) / "input.geojson"
                    temp_kml = Path(tmpdir) / "output.kml"
                    temp_kmz = Path(tmpdir) / f"{filename_stem}.kmz"

                    with open(temp_geojson, "wb") as f:
                        f.write(uploaded_file.read())

                    gdf = gpd.read_file(temp_geojson)

                    geom_type = gdf.geometry.geom_type.unique()
                    if len(geom_type) > 1:
                        st.error("Mélange de géométries détecté (Points et Lignes). Utilisez un fichier homogène.")
                        st.stop()
                    geom_type = geom_type[0]

                    if geom_type == "Point":
                        if "laty" in gdf.columns and "longx" in gdf.columns:
                            gdf['geometry'] = gdf.apply(lambda row: Point(float(row['longx']), float(row['laty'])), axis=1)
                            gdf.set_crs("EPSG:4326", inplace=True)
                        else:
                            gdf.set_crs("EPSG:2154", allow_override=True, inplace=True)
                            gdf = gdf.to_crs("EPSG:4326")
                        gdf["Name"] = gdf.get("siret_boa", "")
                        gdf["Description"] = gdf.get("dénomination_de_l_unité_légale", "")

                    elif geom_type == "LineString":
                        gdf.set_crs("EPSG:2154", allow_override=True, inplace=True)
                        gdf = gdf.to_crs("EPSG:4326")
                        gdf["Name"] = gdf.get("id_cotation", "")
                        gdf["Description"] = gdf.get("nom_lien", "")

                    else:
                        st.error(f"Géométrie non prise en charge : {geom_type}")
                        st.stop()

                    for col in gdf.columns:
                        if col != "geometry":
                            gdf[col] = gdf[col].astype(str)

                    cols = ["Name", "Description"] + [col for col in gdf.columns if col not in ("Name", "Description", "geometry")] + ["geometry"]
                    gdf = gdf[cols]

                    gdf.to_file(temp_kml, driver="KML")

                    with zipfile.ZipFile(temp_kmz, 'w', zipfile.ZIP_DEFLATED) as kmz:
                        kmz.write(temp_kml, arcname="doc.kml")

                    with open(temp_kmz, "rb") as f:
                        kmz_bytes = f.read()

                    st.session_state["kmz_result"] = kmz_bytes
                    st.session_state["kmz_filename"] = f"{filename_stem}.kmz"

            except Exception as e:
                st.error(f"Erreur lors de la conversion : {e}")

    if st.session_state.get("kmz_result"):
        st.download_button(
            label="Télécharger le fichier KMZ",
            data=st.session_state["kmz_result"],
            file_name=st.session_state["kmz_filename"],
            mime="application/vnd.google-earth.kmz"
        )

        if st.button("Renouveler l'opération"):
            st.session_state["kmz_result"] = None
            st.session_state["kmz_filename"] = None
            current_key = int(st.session_state["upload_key"].split("_")[-1])
            st.session_state["upload_key"] = f"file_uploader_geojson_{current_key + 1}"
            st.rerun()
