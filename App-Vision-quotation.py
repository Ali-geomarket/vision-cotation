import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

# --- Configuration initiale ---
st.set_page_config(page_title="Vision Quotation", layout="centered")

# --- Données utilisateurs pour connexion ---
USERS = {"sg": "dri", "ps": "dri"}

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "main_page" not in st.session_state:
    st.session_state["main_page"] = "login"

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
    st.title("Bienvenue - Vision quotation")
    st.write("Que souhaitez-vous faire ?")
    if st.button("Récupérer le TCD MA"):
        st.session_state["main_page"] = "tcd_ma"
        st.rerun()

# --- PAGE : TCD MA ---
elif st.session_state["main_page"] == "tcd_ma":
    st.title("Analyse TCD - Marché Adressable")

    if st.button("Retour"):
        st.session_state["main_page"] = "home"
        st.rerun()

    uploaded_file = st.file_uploader("Déposez un fichier Excel", type=["xlsx"])

    if uploaded_file:
        df = pd.read_excel(uploaded_file)

        # Nettoyage + regroupement des tranches
        def regrouper_tranches(val):
            if isinstance(val, str):
                if any(val.startswith(code) for code in ["02", "03"]):
                    return "1 A 5 SALARIES"
                elif any(val.startswith(code) for code in ["04", "05", "06"]):
                    return "6 A 49 SALARIES"
                elif val.startswith(("07", "08", "09", "10", "11", "12", "13", "14", "15")):
                    return "49 ET PLUS SALARIES"
            return None  # ignore les autres cas

        df["TRANCHE_REGROUPÉE"] = df["NB_SALARIE_FIN"].apply(regrouper_tranches)

        if st.button("Récupérer le TCD"):
            pivot = pd.pivot_table(
                df[df["TRANCHE_REGROUPÉE"].notnull()],
                index="TRANCHE_REGROUPÉE",
                values="SIRET_BOA",
                aggfunc="count",
                margins=True,
                margins_name="Total général"
            ).rename(columns={"SIRET_BOA": "NOMBRE ENTREPRISES"})

            pivot = pivot.loc[["1 A 5 SALARIES", "6 A 49 SALARIES", "49 ET PLUS SALARIES", "Total général"]]
            st.session_state["pivot_result"] = pivot
            st.rerun()

    # Affichage du TCD
    if st.session_state.get("pivot_result") is not None:
        st.subheader("Tableau Croisé Dynamique – Marché Adressable")
        st.dataframe(st.session_state["pivot_result"])

        if st.button("Enregistrer l'image du TCD"):
            fig, ax = plt.subplots(figsize=(10, 3))
            ax.axis('off')
            table_data = [[idx] + list(row) for idx, row in st.session_state["pivot_result"].iterrows()]
            col_labels = ["TRANCHE"] + st.session_state["pivot_result"].columns.to_list()
            table = ax.table(cellText=table_data, colLabels=col_labels, loc='center')
            table.scale(1, 2)
            buf = BytesIO()
            plt.savefig(buf, format="png", bbox_inches="tight", dpi=300)
            buf.seek(0)
            st.download_button("Télécharger l'image du TCD", data=buf, file_name="TCD_MA.png", mime="image/png")

        if st.button("Renouveler l'opération"):
            del st.session_state["pivot_result"]
            st.rerun()
