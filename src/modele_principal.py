"""Modèle principal : probabilité de possession d'un compte bancaire."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from src.modele_court import decouper_age

RACINE = Path(__file__).resolve().parents[1]
CHEMIN_MODELE = RACINE / "models" / "modele_principal.joblib"
VARIABLES = [
    "country",
    "location_type",
    "cellphone_access",
    "household_size",
    "age_of_respondent",
    "gender_of_respondent",
    "relationship_with_head",
    "marital_status",
    "education_level",
    "job_type",
]
VARIABLES_CATEGORIELLES = [
    "country",
    "location_type",
    "cellphone_access",
    "gender_of_respondent",
    "relationship_with_head",
    "marital_status",
    "education_level",
    "job_type",
]


def construire_modele(C: float = 3.0) -> Pipeline:
    """Construit la logistique retenue avec catégories one-hot et âge non linéaire."""
    age = Pipeline(
        [
            (
                "tranches",
                FunctionTransformer(decouper_age, feature_names_out="one-to-one"),
            ),
            ("indicatrices", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preparation = ColumnTransformer(
        [
            (
                "categories",
                OneHotEncoder(handle_unknown="ignore"),
                VARIABLES_CATEGORIELLES,
            ),
            ("age", age, ["age_of_respondent"]),
            ("menage", StandardScaler(), ["household_size"]),
        ],
        verbose_feature_names_out=False,
    )
    return Pipeline(
        [
            ("preparation", preparation),
            ("modele", LogisticRegression(C=C, max_iter=1500, random_state=42)),
        ]
    )


def meilleur_seuil(y_vrai: pd.Series, probabilites: np.ndarray) -> tuple[float, float]:
    """Choisit le seuil maximisant le F1 macro sur une grille de 0,05 à 0,95."""
    seuils = np.round(np.arange(0.05, 0.951, 0.01), 2)
    scores = [
        f1_score(
            y_vrai,
            probabilites >= seuil,
            average="macro",
            labels=[0, 1],
            zero_division=0,
        )
        for seuil in seuils
    ]
    meilleur = int(np.argmax(scores))
    return float(seuils[meilleur]), float(scores[meilleur])


def entrainer(X: pd.DataFrame, y: pd.Series) -> dict[str, Any]:
    """Entraîne la logistique et choisit un seuil par validation croisée sur X, y."""
    if not isinstance(X, pd.DataFrame):
        raise TypeError("X doit être un DataFrame pandas.")
    if len(X) != len(y):
        raise ValueError("X et y doivent contenir le même nombre de lignes.")
    colonnes_manquantes = [variable for variable in VARIABLES if variable not in X]
    if colonnes_manquantes:
        raise ValueError(f"Colonnes manquantes : {colonnes_manquantes}")

    cible = pd.Series(y, index=X.index)
    if cible.isna().any() or set(cible.unique()) != {0, 1}:
        raise ValueError("y doit contenir les deux classes codées 0 et 1, sans valeur manquante.")
    plus_petite_classe = int(cible.value_counts().min())
    if plus_petite_classe < 2:
        raise ValueError("Il faut au moins deux exemples de chaque classe pour entraîner le modèle.")

    modele = construire_modele()
    plis = StratifiedKFold(
        n_splits=min(5, plus_petite_classe),
        shuffle=True,
        random_state=42,
    )
    probabilites_cv = cross_val_predict(
        modele,
        X[VARIABLES],
        cible,
        cv=plis,
        method="predict_proba",
    )[:, 1]
    seuil, _ = meilleur_seuil(cible, probabilites_cv)
    modele.fit(X[VARIABLES], cible)
    return {
        "modele": modele,
        "seuil": seuil,
        "variables": list(VARIABLES),
        "moyenne_encodee": moyenne_encodee(modele, X[VARIABLES]),
    }


def moyenne_encodee(modele: Pipeline, X: pd.DataFrame) -> np.ndarray:
    """Profil moyen des données d'entraînement, une fois encodé : la référence des facteurs du score."""
    encodees = modele.named_steps["preparation"].transform(X)
    return np.asarray(encodees.mean(axis=0)).ravel()


@lru_cache(maxsize=1)
def _charger_modele() -> dict[str, Any]:
    """Lit le modèle enregistré une seule fois, puis le garde en mémoire.

    Après un réentraînement dans le même processus, appeler _charger_modele.cache_clear() pour relire le fichier.
    """
    return joblib.load(CHEMIN_MODELE)


def _profil_valide(profil: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    if not isinstance(profil, pd.DataFrame):
        raise TypeError("profil doit être un DataFrame pandas.")
    if len(profil) != 1:
        raise ValueError("profil doit contenir exactement une ligne.")
    colonnes_manquantes = [variable for variable in variables if variable not in profil]
    if colonnes_manquantes:
        raise ValueError(f"Colonnes manquantes dans le profil : {colonnes_manquantes}")
    return profil[variables]


def predire(profil: pd.DataFrame) -> float:
    """Renvoie la probabilité d'avoir un compte pour un profil d'une ligne."""
    objet = _charger_modele()
    valeurs = _profil_valide(profil, objet["variables"])
    return float(objet["modele"].predict_proba(valeurs)[0, 1])


def expliquer(profil: pd.DataFrame) -> pd.DataFrame:
    """Effet de chaque réponse sur la probabilité, en points (0,05 = 5 points), trié par effet absolu.

    Pour chaque variable, on compare la probabilité du profil à celle obtenue en ramenant cette seule variable
    au profil moyen de l'entraînement. Un effet positif fait monter le score par rapport à une personne moyenne
    sur cette variable ; un effet négatif le fait baisser. Ce sont des appuis du modèle, pas des causes.
    """
    objet = _charger_modele()
    if "moyenne_encodee" not in objet:
        raise ValueError("Modèle enregistré sans 'moyenne_encodee' : le réenregistrer avec entrainer().")
    valeurs = _profil_valide(profil, objet["variables"])
    modele = objet["modele"]
    preparation = modele.named_steps["preparation"]
    regression = modele.named_steps["modele"]
    variables_encodees = preparation.transform(valeurs)
    if sparse.issparse(variables_encodees):
        variables_encodees = variables_encodees.toarray()

    noms_encodees = preparation.get_feature_names_out()
    logit = float(regression.decision_function(variables_encodees)[0])
    probabilite = 1 / (1 + np.exp(-logit))
    ecarts = (variables_encodees[0] - objet["moyenne_encodee"]) * regression.coef_[0]
    lignes = []
    for variable in objet["variables"]:
        positions = [
            position
            for position, nom in enumerate(noms_encodees)
            if nom == variable or nom.startswith(f"{variable}_")
        ]
        if not positions:
            raise ValueError(f"Aucune caractéristique encodée ne correspond à {variable}.")
        logit_moyen = logit - ecarts[positions].sum()  # même profil, cette variable ramenée à la moyenne
        lignes.append(
            {
                "variable": variable,
                "contribution": float(probabilite - 1 / (1 + np.exp(-logit_moyen))),
            }
        )

    return (
        pd.DataFrame(lignes)
        .assign(effet_absolu=lambda tableau: tableau["contribution"].abs())
        .sort_values("effet_absolu", ascending=False)
        .drop(columns="effet_absolu")
        .reset_index(drop=True)
    )
