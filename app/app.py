"""Interface : formulaire de profil et probabilité d'avoir un compte bancaire.

Lancer depuis la racine du dépôt : streamlit run app/app.py
"""

import importlib
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DOSSIER = Path(__file__).resolve().parent
sys.path.insert(0, str(DOSSIER.parent))
sys.path.insert(0, str(DOSSIER))

import provisoire  # noqa: E402
from src.decoupage import charger  # noqa: E402
from src.preparation import preparer  # noqa: E402


def fonction(module, nom):
    """Prend la vraie fonction si son fichier existe dans src/, sinon la version provisoire."""
    try:
        return getattr(importlib.import_module(f"src.{module}"), nom), True
    except (ImportError, AttributeError):
        return getattr(provisoire, nom), False


predire, vrai_principal = fonction("modele_principal", "predire")
expliquer, _ = fonction("modele_principal", "expliquer")
voisins, vrai_knn = fonction("voisins", "voisins")
predire_court, vrai_court = fonction("modele_court", "predire_court")
try:
    VARIABLES_COURTES = importlib.import_module("src.modele_court").VARIABLES_COURTES
except (ImportError, AttributeError):
    VARIABLES_COURTES = provisoire.VARIABLES_COURTES

QUESTIONS = {
    "country": "Pays",
    "location_type": "Lieu de vie",
    "cellphone_access": "Accès à un téléphone portable",
    "household_size": "Nombre de personnes dans le ménage",
    "age_of_respondent": "Âge",
    "gender_of_respondent": "Genre",
    "relationship_with_head": "Lien avec le chef de ménage",
    "marital_status": "Statut marital",
    "education_level": "Niveau d'éducation",
    "job_type": "Emploi",
}
REPONSES = {
    "Rural": "Rural", "Urban": "Urbain", "Yes": "Oui", "No": "Non", "Female": "Femme", "Male": "Homme",
    "Kenya": "Kenya", "Rwanda": "Rwanda", "Tanzania": "Tanzanie", "Uganda": "Ouganda",
    "Child": "Enfant", "Head of Household": "Chef de ménage", "Other relative": "Autre membre",
    "Parent": "Parent", "Spouse": "Conjoint ou conjointe",
    "Divorced/Seperated": "Divorcé ou séparé", "Married/Living together": "Marié ou en couple",
    "Single/Never Married": "Célibataire", "Widowed": "Veuf ou veuve",
    "No formal education": "Aucune éducation formelle", "Primary education": "Primaire",
    "Secondary education": "Secondaire", "Tertiary education": "Supérieur",
    "Vocational/Specialised training": "Formation professionnelle",
    "Dont Know/Refuse to answer": "Ne sait pas ou refuse de répondre", "Farming and Fishing": "Agriculture et pêche",
    "Formally employed Government": "Salarié du secteur public", "Formally employed Private": "Salarié du secteur privé",
    "Government Dependent": "Aides de l'État", "Informally employed": "Emploi informel", "No Income": "Sans revenu",
    "Other Income": "Autre revenu", "Remittance Dependent": "Argent envoyé par des proches",
    "Self employed": "Indépendant",
}


def libelle(valeur):
    return REPONSES.get(valeur, valeur)


@st.cache_data
def referentiel():
    """Choix possibles, emplois présents dans chaque pays et taux global, tirés des données préparées."""
    donnees = charger()
    choix = {v: sorted(donnees[v].unique()) for v in QUESTIONS if v not in ("age_of_respondent", "household_size")}
    emplois = {pays: set(g["job_type"]) for pays, g in donnees.groupby("country")}
    return choix, emplois, (donnees["bank_account"] == "Yes").mean()


CHOIX, EMPLOIS_PAR_PAYS, TAUX_GLOBAL = referentiel()


def champ(variable, cle):
    if variable == "age_of_respondent":
        return st.number_input(QUESTIONS[variable], 16, 100, 35, key=cle)
    if variable == "household_size":
        return st.number_input(QUESTIONS[variable], 1, 21, 4, key=cle)
    return st.selectbox(QUESTIONS[variable], CHOIX[variable], format_func=libelle, key=cle)


def profil_prepare(reponses):
    """Le formulaire passe par la même préparation que les données, sans corriger la Tanzanie :
    la personne déclare elle-même son lieu et son statut."""
    return preparer(pd.DataFrame([reponses]), corriger=False)


def pourcentage(valeur):
    return f"{valeur:.0%}".replace("%", " %")


def avertir_emploi(pays, emploi):
    if emploi not in EMPLOIS_PAR_PAYS[pays]:
        st.warning(f"Aucune personne de {libelle(pays)} n'a déclaré « {libelle(emploi)} » dans les données : "
                   "pour ce pays, la prédiction s'appuie sur des profils d'autres pays.")


def barres(tableau, x, y, titre, couleur=None, format_x=".0%"):
    encodage = {"x": alt.X(x, title=titre, axis=alt.Axis(format=format_x)), "y": alt.Y(y, title=None, sort=None)}
    if couleur:
        encodage["color"] = couleur
    return st.altair_chart(alt.Chart(tableau).mark_bar(cornerRadiusEnd=4, height=18).encode(**encodage,
                           tooltip=[y, alt.Tooltip(x, format=format_x)]), width="stretch")


st.set_page_config(page_title="Inclusion financière", page_icon="🏦", layout="wide")
st.title("Inclusion financière en Afrique de l'Est")
st.caption("Probabilité qu'une personne ait un compte bancaire, d'après les enquêtes Zindi au Kenya, au Rwanda, en Tanzanie et en Ouganda.")

provisoires = [nom for nom, vrai in [("modèle principal", vrai_principal), ("KNN", vrai_knn), ("modèle court", vrai_court)] if not vrai]
if provisoires:
    st.error(f"**Résultats provisoires** pour : {', '.join(provisoires)}. Ces chiffres sont de simples taux observés par groupe, "
             "en attendant les vrais modèles.")

onglet_complet, onglet_court, onglet_propos = st.tabs(["Formulaire complet", "Moins de questions", "À propos"])

with onglet_complet:
    with st.form("complet"):
        colonnes = st.columns(2)
        reponses = {}
        for position, variable in enumerate(QUESTIONS):
            with colonnes[position % 2]:
                reponses[variable] = champ(variable, f"complet_{variable}")
        envoye = st.form_submit_button("Estimer", type="primary")
    if envoye:
        st.session_state["reponses"] = reponses

    if "reponses" in st.session_state:
        reponses = st.session_state["reponses"]
        profil = profil_prepare(reponses)
        probabilite = predire(profil)
        st.session_state["probabilite_complete"] = probabilite

        if reponses["country"] == "Tanzania":
            st.info("Le modèle a appris sur des données de Tanzanie corrigées **en supposant vraie notre hypothèse** "
                    "d'inversion des libellés de lieu et de statut marital. Vos réponses, elles, ne sont pas modifiées.")
        avertir_emploi(reponses["country"], reponses["job_type"])

        gauche, droite = st.columns(2)
        gauche.metric("Probabilité d'avoir un compte", pourcentage(probabilite),
                      f"{(probabilite - TAUX_GLOBAL) * 100:+.0f} points par rapport à la moyenne ({pourcentage(TAUX_GLOBAL)})",
                      delta_color="off")

        resultat_voisins = voisins(profil)
        droite.metric("Personnes similaires ayant un compte", pourcentage(resultat_voisins["taux"]),
                      f"{pourcentage(resultat_voisins['taux_meme_pays'])} dans le même pays", delta_color="off")
        droite.caption(f"Taux réel observé chez les {resultat_voisins['k']} personnes les plus proches du profil.")

        st.subheader("Ce qui a fait monter ou baisser le score")
        facteurs = expliquer(profil).head(8)
        facteurs["question"] = facteurs["variable"].map(QUESTIONS)
        facteurs["sens"] = facteurs["contribution"].map(lambda c: "Vers le haut" if c > 0 else "Vers le bas")
        barres(facteurs, "contribution:Q", "question:N", "Effet sur le score",
               alt.Color("sens:N", title=None, scale=alt.Scale(domain=["Vers le haut", "Vers le bas"], range=["#2a78d6", "#eb6834"])),
               format_x="+.0%")
        st.caption("Ce sont les facteurs sur lesquels le modèle s'appuie, pas des causes : changer une réponse dans la vie réelle "
                   "ne changerait pas forcément la situation.")

        st.subheader("Le même profil dans les autres pays")
        pays = pd.DataFrame([
            {"pays": libelle(p), "probabilité": predire(profil.assign(country=p)), "profil saisi": p == reponses["country"]}
            for p in CHOIX["country"]
        ])
        barres(pays, "probabilité:Q", "pays:N", "Probabilité d'avoir un compte",
               alt.Color("profil saisi:N", title="Pays saisi", scale=alt.Scale(domain=[True, False], range=["#2a78d6", "#a9c6ea"])))
        absents = [libelle(p) for p in CHOIX["country"] if reponses["job_type"] not in EMPLOIS_PAR_PAYS[p]]
        if absents:
            st.caption(f"L'emploi « {libelle(reponses['job_type'])} » n'existe pas dans les données pour : {', '.join(absents)}.")
        st.caption("Le pays est confondu avec l'année d'enquête et la façon de coder l'emploi : ces écarts montrent la réaction du modèle, "
                   "pas l'effet d'un déménagement.")

        st.subheader("Le même profil avec l'autre genre")
        autre = "Male" if reponses["gender_of_respondent"] == "Female" else "Female"
        a, b = st.columns(2)
        a.metric(libelle(reponses["gender_of_respondent"]) + " (profil saisi)", pourcentage(probabilite))
        b.metric(libelle(autre), pourcentage(predire(profil.assign(gender_of_respondent=autre))))
        st.caption("Cet écart montre la réaction du modèle, pas un effet causal du genre. Le lien avec le chef de ménage "
                   "en est en partie un relais : 98,6 % des conjoints du jeu de données sont des femmes.")

with onglet_court:
    st.write(f"Une estimation avec **{len(VARIABLES_COURTES)} questions** seulement, au lieu de {len(QUESTIONS)}.")
    with st.form("court"):
        colonnes = st.columns(2)
        reponses_courtes = {}
        for position, variable in enumerate(VARIABLES_COURTES):
            with colonnes[position % 2]:
                reponses_courtes[variable] = champ(variable, f"court_{variable}")
        envoye_court = st.form_submit_button("Estimer", type="primary")
    if envoye_court:
        if "country" in reponses_courtes and "job_type" in reponses_courtes:
            avertir_emploi(reponses_courtes["country"], reponses_courtes["job_type"])
        probabilite_courte = predire_court(profil_prepare(reponses_courtes))
        gauche, droite = st.columns(2)
        gauche.metric("Probabilité avec moins de questions", pourcentage(probabilite_courte))
        if "probabilite_complete" in st.session_state:
            droite.metric("Avec le formulaire complet", pourcentage(st.session_state["probabilite_complete"]))
            droite.caption("Comparaison valable seulement si les réponses communes sont les mêmes dans les deux formulaires.")

with onglet_propos:
    st.markdown("""
- **Données :** enquêtes Zindi « Financial Inclusion in Africa », 23 524 personnes, 14,08 % avec un compte.
- **Tanzanie :** les données d'entraînement sont corrigées **en supposant vraie notre hypothèse** d'inversion des libellés de lieu et de statut marital. Aucune documentation ne la confirme.
- **Échantillon :** sans poids d'enquête, les résultats décrivent les personnes interrogées, pas la population de chaque pays.
- **Limites :** le modèle apprend des associations. Il ne dit pas ce qui arriverait si le profil d'une personne changeait.
""")
