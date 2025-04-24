import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

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
    if st.button("Récupérer le MA regroupé"):
        st.session_state["main_page"] = "ma_regroupe"
        st.session_state["ma_regroupe_result"] = None
        st.session_state["upload_key"] = "file_uploader_0"
        st.rerun()

# --- PAGE : MA regroupé ---
elif st.session_state["main_page"] == "ma_regroupe":
    st.title("Marché Adressable regroupé")

    if st.button("Retour"):
        st.session_state["main_page"] = "home"
        st.rerun()

    uploaded_file = st.file_uploader("Déposez un fichier CSV", type=["csv"], key=st.session_state["upload_key"])

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, sep=';', dtype=str)

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

        # Génération de l’image à télécharger
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
            # Incrémente la clé pour forcer le reset du file_uploader
            current_key = int(st.session_state["upload_key"].split("_")[-1])
            st.session_state["upload_key"] = f"file_uploader_{current_key + 1}"
            st.rerun()
