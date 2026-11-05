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

BLEU, BLEU_PALE, ORANGE, TEXTE_2, GRILLE = "#2a78d6", "#b9d3f2", "#eb6834", "#5f5e5a", "#e4e3df"


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
    "age_of_respondent": "Âge",
    "gender_of_respondent": "Genre",
    "education_level": "Niveau d'éducation",
    "job_type": "Emploi",
    "cellphone_access": "Accès à un téléphone portable",
    "marital_status": "Statut marital",
    "relationship_with_head": "Lien avec le chef de ménage",
    "household_size": "Personnes dans le ménage",
}
NUMERIQUES = ("age_of_respondent", "household_size")
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
    "Dont Know/Refuse to answer": "Ne sait pas ou refuse", "Farming and Fishing": "Agriculture et pêche",
    "Formally employed Government": "Salarié du public", "Formally employed Private": "Salarié du privé",
    "Government Dependent": "Aides de l'État", "Informally employed": "Emploi informel", "No Income": "Sans revenu",
    "Other Income": "Autre revenu", "Remittance Dependent": "Argent envoyé par des proches",
    "Self employed": "Indépendant",
}


def libelle(valeur):
    return REPONSES.get(valeur, valeur)


@st.cache_data
def referentiel():
    """Choix possibles, réponses par défaut, emplois présents dans chaque pays et taux global, tirés des données préparées."""
    donnees = charger()
    choix = {v: sorted(donnees[v].unique()) for v in QUESTIONS if v not in NUMERIQUES}
    defauts = {v: donnees[v].mode()[0] for v in choix} | {v: int(donnees[v].median()) for v in NUMERIQUES}
    emplois = {pays: set(g["job_type"]) for pays, g in donnees.groupby("country")}
    return choix, defauts, emplois, (donnees["bank_account"] == "Yes").mean()


CHOIX, DEFAUTS, EMPLOIS_PAR_PAYS, TAUX_GLOBAL = referentiel()


def champ(variable, cle):
    if variable == "age_of_respondent":
        return st.slider(QUESTIONS[variable], 16, 100, DEFAUTS[variable], key=cle)
    if variable == "household_size":
        return st.number_input(QUESTIONS[variable], 1, 21, DEFAUTS[variable], key=cle)
    options = CHOIX[variable]
    if len(options) == 2:
        return st.segmented_control(QUESTIONS[variable], options, default=DEFAUTS[variable], format_func=libelle,
                                    key=cle, width="stretch") or DEFAUTS[variable]
    return st.selectbox(QUESTIONS[variable], options, index=options.index(DEFAUTS[variable]), format_func=libelle, key=cle)


def formulaire(variables, prefixe):
    return {v: champ(v, f"{prefixe}_{v}") for v in variables}


def profil_prepare(reponses):
    """Même préparation que les données, sans corriger la Tanzanie : la personne déclare elle-même son lieu et son statut."""
    return preparer(pd.DataFrame([reponses]), corriger=False)


def pourcentage(valeur):
    return f"{valeur:.0%}".replace("%", " %")


def jauge(titre, valeur, sous_titre):
    """Grand chiffre, barre de 0 à 100 % et repère de la moyenne de l'échantillon."""
    st.markdown(f"""
<div style="font-size:0.9rem;color:{TEXTE_2}">{titre}</div>
<div style="font-size:3rem;font-weight:700;line-height:1.1;color:{BLEU}">{pourcentage(valeur)}</div>
<div style="position:relative;height:10px;background:{GRILLE};border-radius:5px;margin:0.6rem 0 0.3rem">
  <div style="width:{valeur * 100:.1f}%;height:100%;background:{BLEU};border-radius:5px"></div>
  <div style="position:absolute;left:{TAUX_GLOBAL * 100:.1f}%;top:-4px;width:2px;height:18px;background:#1d1d1b"></div>
</div>
<div style="font-size:0.8rem;color:{TEXTE_2}">{sous_titre}</div>
""", unsafe_allow_html=True)


def barres(tableau, etiquette, valeur, couleur, format_valeur=".0%", hauteur_ligne=34):
    """Barres horizontales avec la valeur écrite au bout, sans axe ni légende."""
    maximum = max(tableau[valeur].abs().max(), 0.01)
    minimum = min(tableau[valeur].min(), 0)
    base = alt.Chart(tableau).encode(
        y=alt.Y(f"{etiquette}:N", sort=None, title=None,
                axis=alt.Axis(labelLimit=260, labelFontSize=13, labelColor="#1d1d1b", ticks=False, domain=False, labelPadding=8)),
        x=alt.X(f"{valeur}:Q", axis=None, scale=alt.Scale(domain=[minimum * 1.35, maximum * 1.3])),
    )
    graphique = base.mark_bar(cornerRadiusEnd=4, size=hauteur_ligne * 0.6).encode(color=alt.Color(f"{couleur}:N", scale=None))
    texte_positif = base.transform_filter(f"datum.{valeur} >= 0").mark_text(align="left", dx=6, fontSize=12, color=TEXTE_2)
    texte_negatif = base.transform_filter(f"datum.{valeur} < 0").mark_text(align="right", dx=-6, fontSize=12, color=TEXTE_2)
    texte = alt.Text(f"{valeur}:Q", format=format_valeur)
    st.altair_chart(
        (graphique + texte_positif.encode(text=texte) + texte_negatif.encode(text=texte))
        .properties(height=len(tableau) * hauteur_ligne).configure_view(stroke=None),
        width="stretch",
    )


def note(texte):
    st.caption(texte)


st.set_page_config(page_title="Mtaa · Inclusion financière", page_icon="🏦", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root {{
    --ink: #17212b;
    --muted: #66737f;
    --blue: {BLEU};
    --orange: {ORANGE};
    --line: #e8edf2;
    --surface: #ffffff;
}}
.stApp {{ background: #f5f8fb; color: var(--ink); }}
.block-container {{ padding: 1.8rem 3rem 4rem; max-width: 1440px; }}
html, body, [class*="css"] {{ font-family: 'DM Sans', sans-serif; }}
h1, h2, h3 {{ font-family: 'Space Grotesk', sans-serif !important; color: var(--ink); }}
h1 {{ font-size: clamp(2rem, 3.8vw, 3.35rem) !important; letter-spacing: -0.055em; line-height: 1.05 !important; }}
h2 {{ letter-spacing: -0.03em; }}
h3 {{ font-size: 1.05rem !important; margin-top: 0.4rem; }}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stToolbar"] {{ visibility: hidden; }}
[data-testid="stVerticalBlockBorderWrapper"] {{
    background: var(--surface); border: 1px solid var(--line); border-radius: 18px;
    box-shadow: 0 8px 30px rgba(28, 54, 80, 0.045);
}}
[data-testid="stMetric"] {{ background: #f8fafc; border-radius: 14px; padding: 1rem; }}
[data-testid="stTabs"] button {{ font-weight: 600; color: var(--muted); }}
[data-testid="stTabs"] button[aria-selected="true"] {{ color: var(--blue); }}
[data-testid="stSegmentedControl"] {{ background: #f2f5f8; border-radius: 10px; padding: 3px; }}
.eyebrow {{ color: var(--blue); font-size: .75rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; margin-bottom: .8rem; }}
.hero {{ padding: .5rem 0 1.6rem; }}
.hero-copy {{ max-width: 770px; color: var(--muted); font-size: 1.05rem; line-height: 1.65; }}
.hero-badge {{ display: inline-flex; gap: .45rem; align-items: center; padding: .5rem .75rem; border-radius: 999px;
    background: #e9f2ff; color: #2364ae; font-size: .78rem; font-weight: 700; margin-bottom: 1rem; }}
.section-kicker {{ color: var(--muted); font-size: .82rem; font-weight: 600; text-transform: uppercase; letter-spacing: .08em; }}
.hero-stat {{ background: var(--ink); color: white; border-radius: 20px; padding: 1.4rem 1.5rem; min-height: 150px;
    display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 14px 28px rgba(23, 33, 43, .14); }}
.hero-stat-label {{ color: #b7c5d2; font-size: .76rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }}
.hero-stat-value {{ font-family: 'Space Grotesk', sans-serif; font-size: 2.7rem; font-weight: 700; letter-spacing: -.06em; }}
.hero-stat-note {{ color: #b7c5d2; font-size: .78rem; }}
[data-testid="stAlert"] {{ border-radius: 12px; padding: .65rem 1rem; margin-bottom: 1.25rem; }}
[data-testid="stAlert"] p {{ font-size: .82rem; }}
@media (max-width: 800px) {{
    .block-container {{ padding: 1.25rem 1rem 3rem; }}
    .hero {{ padding-bottom: 1.25rem; }}
}}
</style>""", unsafe_allow_html=True)

st.markdown("""<div class="hero">
<div class="hero-badge">🏦  DATA STORY · AFRIQUE DE L'EST</div>
</div>""", unsafe_allow_html=True)
intro, reference = st.columns([0.72, 0.28], gap="large", vertical_alignment="center")
with intro:
    st.markdown("""<div class="eyebrow">Mtaa / Inclusion financière</div>
<h1>Comprendre l'accès<br>au compte bancaire.</h1>
<p class="hero-copy">Décrivez un profil pour obtenir une estimation transparente, fondée sur
23&nbsp;524 personnes enquêtées au Kenya, au Rwanda, en Tanzanie et en Ouganda.</p>""",
                unsafe_allow_html=True)
with reference:
    st.markdown(f"""<div class="hero-stat">
<div class="hero-stat-label">Dans l'échantillon</div>
<div class="hero-stat-value">{pourcentage(TAUX_GLOBAL)}</div>
<div class="hero-stat-note">des personnes ont un compte bancaire</div>
</div>""", unsafe_allow_html=True)

provisoires = [nom for nom, vrai in [("modèle principal", vrai_principal), ("KNN", vrai_knn), ("modèle court", vrai_court)] if not vrai]
if provisoires:
    st.warning(f"Version de démonstration : résultats provisoires pour {', '.join(provisoires)}. "
               "Ce sont de simples taux observés par groupe, en attendant les vrais modèles.", icon="🚧")

onglet_complet, onglet_court, onglet_propos = st.tabs(["✦  Profil complet", "⚡  Estimation rapide", "ⓘ  À propos"])

with onglet_complet:
    gauche, droite = st.columns([0.36, 0.64], gap="large")

    with gauche:
        with st.container(border=True):
            st.markdown('<div class="section-kicker">Étape 01 · Votre profil</div>', unsafe_allow_html=True)
            st.subheader("Quelques questions")
            st.caption("Les réponses servent uniquement à calculer l'estimation ci-contre.")
            reponses = formulaire(QUESTIONS, "complet")

    profil = profil_prepare(reponses)
    probabilite = predire(profil)
    st.session_state["complet"] = (reponses, probabilite)

    with droite:
        if reponses["country"] == "Tanzania":
            st.info("Le modèle a appris sur des données de Tanzanie corrigées **en supposant vraie notre hypothèse** "
                    "d'inversion des libellés de lieu et de statut marital. Vos réponses ne sont pas modifiées.", icon="ℹ️")
        if reponses["job_type"] not in EMPLOIS_PAR_PAYS[reponses["country"]]:
            st.warning(f"Personne en {libelle(reponses['country'])} n'a déclaré « {libelle(reponses['job_type'])} » "
                       "dans les données : l'estimation s'appuie sur d'autres pays.")

        carte_1, carte_2 = st.columns(2)
        with carte_1, st.container(border=True):
            jauge("Probabilité d'avoir un compte", probabilite,
                  f"Le trait noir marque la moyenne de l'échantillon ({pourcentage(TAUX_GLOBAL)}).")
        resultat_voisins = voisins(profil)
        with carte_2, st.container(border=True):
            jauge("Parmi les personnes similaires", resultat_voisins["taux"],
                  f"{pourcentage(resultat_voisins['taux_meme_pays'])} dans le même pays · "
                  f"taux réel observé chez {resultat_voisins['k']} personnes proches.")

        with st.container(border=True):
            st.subheader("Ce qui fait monter ou baisser le score")
            facteurs = expliquer(profil).head(6)
            facteurs["question"] = facteurs["variable"].map(QUESTIONS) + " : " + facteurs["variable"].map(
                lambda v: libelle(reponses[v]) if v not in NUMERIQUES else str(reponses[v]))
            facteurs["couleur"] = facteurs["contribution"].map(lambda c: BLEU if c > 0 else ORANGE)
            barres(facteurs, "question", "contribution", "couleur", format_valeur="+.0%")
            note("En bleu, ce qui fait monter le score ; en orange, ce qui le fait baisser. Ce sont des appuis du modèle, pas des causes.")

        pays_col, genre_col = st.columns([0.6, 0.4])
        with pays_col, st.container(border=True):
            st.subheader("Même profil, autres pays")
            pays = pd.DataFrame([
                {"pays": libelle(p) + (" (saisi)" if p == reponses["country"] else "") + (" ⚠" if reponses["job_type"] not in EMPLOIS_PAR_PAYS[p] else ""),
                 "probabilité": predire(profil.assign(country=p)),
                 "couleur": BLEU if p == reponses["country"] else BLEU_PALE}
                for p in CHOIX["country"]
            ])
            barres(pays, "pays", "probabilité", "couleur")
            note("⚠ : emploi absent des données de ce pays. Le pays se confond avec l'année d'enquête : "
                 "l'écart montre la réaction du modèle, pas l'effet d'un déménagement.")
        with genre_col, st.container(border=True):
            st.subheader("Même profil, autre genre")
            genres = pd.DataFrame([
                {"genre": libelle(g) + (" (saisi)" if g == reponses["gender_of_respondent"] else ""),
                 "probabilité": predire(profil.assign(gender_of_respondent=g)),
                 "couleur": BLEU if g == reponses["gender_of_respondent"] else BLEU_PALE}
                for g in CHOIX["gender_of_respondent"]
            ])
            barres(genres, "genre", "probabilité", "couleur")
            note("Réaction du modèle, pas un effet causal. Le lien au chef de ménage relaie en partie le genre : "
                 "98,6 % des conjoints sont des femmes.")

with onglet_court:
    gauche, droite = st.columns([0.36, 0.64], gap="large")
    with gauche, st.container(border=True):
        st.markdown('<div class="section-kicker">Mode express</div>', unsafe_allow_html=True)
        st.subheader(f"{len(VARIABLES_COURTES)} questions")
        st.caption(f"Une estimation plus rapide, avec {len(QUESTIONS) - len(VARIABLES_COURTES)} réponses en moins.")
        reponses_courtes = formulaire(VARIABLES_COURTES, "court")
    probabilite_courte = predire_court(profil_prepare(reponses_courtes))
    with droite:
        reponses_completes, probabilite_complete = st.session_state["complet"]
        carte_1, carte_2 = st.columns(2)
        with carte_1, st.container(border=True):
            jauge("Avec moins de questions", probabilite_courte, f"Moyenne de l'échantillon : {pourcentage(TAUX_GLOBAL)}.")
        with carte_2, st.container(border=True):
            jauge("Avec le profil complet", probabilite_complete, "Profil saisi dans l'onglet « Profil complet ».")
        differentes = [QUESTIONS[v] for v in VARIABLES_COURTES if reponses_courtes[v] != reponses_completes[v]]
        if differentes:
            note(f"Réponses différentes entre les deux onglets : {', '.join(differentes)}. La comparaison n'est juste que si elles sont identiques.")
        else:
            note("Les réponses communes sont identiques : l'écart vient seulement des questions retirées.")

with onglet_propos:
    st.markdown("""
- **Données :** enquêtes Zindi « Financial Inclusion in Africa », 23 524 personnes, dont 14,08 % avec un compte.
- **Tanzanie :** les données d'entraînement sont corrigées **en supposant vraie notre hypothèse** d'inversion des libellés de lieu et de statut marital. Aucune documentation ne la confirme.
- **Échantillon :** sans poids d'enquête, les résultats décrivent les personnes interrogées, pas la population de chaque pays.
- **Limites :** le modèle apprend des associations. Il ne dit pas ce qui arriverait si le profil d'une personne changeait.
""")
