
import streamlit as st
import pandas as pd
from openpyxl import load_workbook
from datetime import datetime
import os

# -------------------------------
# Authentification simple
# -------------------------------
USERS = {
    "sarah.gontran": "Geomarket123",
    "pauline.solari": "Geomarket123"
}

RESP_MAP = {
    "sarah.gontran": "Sarah",
    "pauline.solari": "Pauline"
}

st.set_page_config(page_title="Fiche DRI", layout="centered")
st.title("Connexion requise")

# Interface de connexion
with st.form("login_form"):
    username = st.text_input("Nom d'utilisateur")
    password = st.text_input("Mot de passe", type="password")
    login_button = st.form_submit_button("Se connecter")

if login_button:
    if username in USERS and USERS[username] == password:
        st.session_state["authenticated"] = True
        st.session_state["user"] = username
        st.experimental_rerun()
    else:
        st.error("Identifiants incorrects. Veuillez réessayer.")

# Si l'utilisateur est connecté, on affiche l'application
if st.session_state.get("authenticated", False):
    username = st.session_state.get("user")
    resp_geomarket = RESP_MAP.get(username, "Inconnu")

    st.title("Ajout automatique de Fiche DRI")
    st.markdown(f"Bonjour **{resp_geomarket}**, moi, c'est Ali, ton assistant préféré qui va t'aider à remplir le fichier de suivi des demandes des fiches DRI !")

    date_traitement_str = st.date_input("Date de traitement (jj/mm/aaaa)", format="DD/MM/YYYY")
    reseau = st.text_input("Donne-moi le Réseau :")
    etat_geomarketing = st.text_input("Donne-moi l'état géomarketing :")

    type_demande_input = st.radio("Type de demande :", ["1 - DEPASSEMENT DE COUT", "2 - DEMANDE DE MA"])
    demande_type = "DEPASSEMENT DE COUT" if type_demande_input.startswith("1") else "DEMANDE DE MA"

    fiche_dri_file = st.file_uploader("Charge le fichier Excel de la fiche DRI (.xlsx)", type="xlsx")

    if fiche_dri_file and st.button("Ajouter cette fiche au fichier suivi"):

        try:
            dri_wb = load_workbook(fiche_dri_file, data_only=True)
            dri_ws = dri_wb.active

            responsable_prod = dri_ws["C7"].value
            date_reception = dri_ws["G7"].value
            commercial = dri_ws["D16"].value
            projet = dri_ws["D9"].value
            cout_extension = dri_ws["D37"].value
            cout_global = dri_ws["D38"].value
            operateur = dri_ws["D11"].value
            gain_dri = dri_ws["G30"].value
            roi = round(dri_ws["G31"].value) if dri_ws["G31"].value else ""
            commande = dri_ws["D10"].value

            date_traitement = pd.to_datetime(date_traitement_str)
            nb_clients_amort = round((cout_global - gain_dri) / 4000, 2) if cout_global and gain_dri else ""
            delai_traitement = (date_traitement - pd.to_datetime(date_reception)).days if date_reception else ""

            # Fichier suivi
            FICHIER_A_COMPLETER = r"\\cov.dom\ComMkg\Geomarketing\Geomarketing_New\ETUDES_DIVERSES\01_ETUDES_RECURRENTES\01. FICHE_DRI\Suivi_demandes_AUTOMATISATION.xlsx"
            FEUILLE = "Suivi_commandes"

            wb_suivi = load_workbook(FICHIER_A_COMPLETER)
            ws_suivi = wb_suivi[FEUILLE]

            new_row = [
                date_reception.strftime("%d/%m/%Y") if date_reception else "",
                reseau,
                responsable_prod,
                commercial,
                projet,
                demande_type,
                cout_extension,
                cout_global,
                operateur,
                gain_dri,
                roi,
                nb_clients_amort,
                commande,
                date_traitement.strftime("%d/%m/%Y"),
                delai_traitement,
                etat_geomarketing,
                resp_geomarket
            ]

            ws_suivi.append(new_row)
            wb_suivi.save(FICHIER_A_COMPLETER)

            st.success("La fiche a bien été ajoutée au fichier de suivi.")
        except Exception as e:
            st.error(f"Une erreur est survenue : {e}")