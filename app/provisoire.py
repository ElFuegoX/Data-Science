"""Fonctions provisoires, en attendant les vrais modèles.

Elles ont exactement les noms et les sorties prévus dans instructions/ : l'interface peut donc être construite avant les modèles.
Aucun modèle n'est entraîné ici : chaque valeur est un simple taux observé dans un groupe des données d'entraînement.
Dès qu'un vrai fichier (src/modele_principal.py, src/voisins.py, src/modele_court.py) existe, app.py l'utilise à sa place.
"""

from functools import lru_cache

import pandas as pd

from src.decoupage import decouper

VARIABLES_COURTES = ["education_level", "job_type", "location_type", "cellphone_access", "country"]
VARIABLES = [
    "country", "location_type", "cellphone_access", "household_size", "age_of_respondent",
    "gender_of_respondent", "relationship_with_head", "marital_status", "education_level", "job_type",
]


@lru_cache
def _entrainement():
    X_ent, _, _, y_ent, _, _ = decouper()
    return X_ent.assign(compte=y_ent)


def _taux(filtres):
    """Taux de comptes chez les personnes qui partagent ces réponses ; taux global si le groupe est trop petit."""
    donnees = _entrainement()
    groupe = donnees
    for variable, valeur in filtres.items():
        groupe = groupe[groupe[variable] == valeur]
    return (groupe["compte"].mean() if len(groupe) >= 20 else donnees["compte"].mean()), len(groupe)


def predire(profil):
    ligne = profil.iloc[0]
    return float(_taux({v: ligne[v] for v in ["country", "education_level", "cellphone_access"]})[0])


def expliquer(profil):
    ligne = profil.iloc[0]
    globale = _entrainement()["compte"].mean()
    lignes = [
        {"variable": v, "contribution": _taux({v: ligne[v]})[0] - globale}
        for v in VARIABLES if v not in ("age_of_respondent", "household_size")
    ]
    tableau = pd.DataFrame(lignes)
    return tableau.reindex(tableau["contribution"].abs().sort_values(ascending=False).index).reset_index(drop=True)


def voisins(profil, k=None):
    ligne = profil.iloc[0]
    taux, nombre = _taux({v: ligne[v] for v in ["education_level", "job_type", "location_type"]})
    taux_pays, _ = _taux({v: ligne[v] for v in ["education_level", "job_type", "location_type", "country"]})
    return {"k": min(nombre, 50), "taux": float(taux), "taux_meme_pays": float(taux_pays)}


def predire_court(profil):
    ligne = profil.iloc[0]
    return float(_taux({v: ligne[v] for v in ["education_level", "job_type"]})[0])
