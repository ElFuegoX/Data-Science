"""API de l'application : reçoit un profil, renvoie l'estimation et ses compléments. Sert aussi la page web.

Lancer depuis la racine du dépôt : uvicorn api.main:app --reload
En ligne : l'API tourne sur Render (Dockerfile, render.yaml) et la page sur Vercel (web/vercel.json).
Documentation interactive : http://localhost:8000/docs
"""

import importlib
import os
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "app"))

import provisoire  # noqa: E402
from api.libelles import QUESTIONS, REPONSES, libelle  # noqa: E402
from src.decoupage import charger  # noqa: E402
from src.preparation import preparer  # noqa: E402

NUMERIQUES = {"age_of_respondent": (16, 100), "household_size": (1, 21)}
WEB = RACINE / "web"


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


@lru_cache
def referentiel():
    """Choix possibles, réponses par défaut, emplois présents dans chaque pays et taux global, tirés des données préparées."""
    donnees = charger()
    choix = {v: sorted(donnees[v].unique()) for v in QUESTIONS if v not in NUMERIQUES}
    defauts = {v: donnees[v].mode()[0] for v in choix} | {v: int(donnees[v].median()) for v in NUMERIQUES}
    emplois = {pays: sorted(set(g["job_type"])) for pays, g in donnees.groupby("country")}
    return {
        "choix": choix, "defauts": defauts, "emplois_par_pays": emplois,
        "taux_global": float((donnees["bank_account"] == "Yes").mean()), "lignes": len(donnees),
    }


def verifier(reponses, variables):
    """Refuse une réponse manquante, inconnue ou hors bornes, avec un message lisible."""
    ref = referentiel()
    for variable in variables:
        if variable not in reponses:
            raise HTTPException(422, f"Réponse manquante : {QUESTIONS[variable]}.")
        valeur = reponses[variable]
        if variable in NUMERIQUES:
            bas, haut = NUMERIQUES[variable]
            if not isinstance(valeur, int) or not bas <= valeur <= haut:
                raise HTTPException(422, f"{QUESTIONS[variable]} : nombre entier entre {bas} et {haut} attendu.")
        elif valeur not in ref["choix"][variable]:
            raise HTTPException(422, f"{QUESTIONS[variable]} : réponse inconnue « {valeur} ».")
    return {v: reponses[v] for v in variables}


def profil_prepare(reponses):
    """Même préparation que les données, sans corriger la Tanzanie : la personne déclare elle-même son lieu et son statut."""
    return preparer(pd.DataFrame([reponses]), corriger=False)


app = FastAPI(title="Inclusion financière en Afrique de l'Est", description="Probabilité d'avoir un compte bancaire en Afrique de l'Est.")

# La page peut être servie par un autre site (Vercel) : on autorise ses appels. L'API ne fait que lire, sans cookies.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ORIGINES_AUTORISEES", "*").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/sante")
def sante():
    """Répond dès que le serveur est prêt : sert au contrôle de Render et au réveil depuis la page."""
    return {"statut": "ok"}


@app.get("/api/referentiel")
def lire_referentiel():
    """Tout ce qu'il faut à la page pour construire les formulaires."""
    ref = referentiel()
    return {
        "questions": QUESTIONS, "libelles": REPONSES, "numeriques": NUMERIQUES,
        "variables_courtes": VARIABLES_COURTES, **ref,
        "provisoires": [nom for nom, vrai in [("modèle principal", vrai_principal), ("KNN", vrai_knn), ("modèle court", vrai_court)] if not vrai],
    }


@app.post("/api/estimer")
def estimer(reponses: dict):
    """Profil complet : probabilité, facteurs du score, personnes similaires, autres pays et autre genre."""
    reponses = verifier(reponses, QUESTIONS)
    ref = referentiel()
    profil = profil_prepare(reponses)
    probabilite = float(predire(profil))

    facteurs = expliquer(profil).head(6)
    proches = voisins(profil)
    pays, genre = reponses["country"], reponses["gender_of_respondent"]
    return {
        "probabilite": probabilite,
        "voisins": {"k": int(proches["k"]), "taux": float(proches["taux"]), "taux_meme_pays": float(proches["taux_meme_pays"])},
        "facteurs": [
            {"question": QUESTIONS[ligne.variable],
             "reponse": str(reponses[ligne.variable]) if ligne.variable in NUMERIQUES else libelle(reponses[ligne.variable]),
             "contribution": float(ligne.contribution)}
            for ligne in facteurs.itertuples()
        ],
        "pays": [
            {"nom": libelle(p), "probabilite": float(predire(profil.assign(country=p))), "saisi": p == pays,
             "emploi_absent": reponses["job_type"] not in ref["emplois_par_pays"][p]}
            for p in ref["choix"]["country"]
        ],
        "genres": [
            {"nom": libelle(g), "probabilite": float(predire(profil.assign(gender_of_respondent=g))), "saisi": g == genre}
            for g in ref["choix"]["gender_of_respondent"]
        ],
        "alertes": {
            "tanzanie": pays == "Tanzania",
            "emploi_absent": reponses["job_type"] not in ref["emplois_par_pays"][pays],
        },
    }


@app.post("/api/estimer_court")
def estimer_court(reponses: dict):
    """Formulaire court : probabilité avec les seules questions de VARIABLES_COURTES."""
    reponses = verifier(reponses, VARIABLES_COURTES)
    return {"probabilite": float(predire_court(profil_prepare(reponses)))}


# En dernier : la page et ses fichiers, servis à la racine. Les routes de l'API ci-dessus restent prioritaires.
app.mount("/", StaticFiles(directory=WEB, html=True), name="page")
