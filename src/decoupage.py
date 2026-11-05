"""Socle commun de la modélisation : mêmes données, même découpage, même évaluation pour tout le groupe.

Test.csv n'a pas de cible : on ne peut pas s'en servir pour évaluer. Le train est donc découpé en trois :
- entraînement (70 %) : pour apprendre ;
- validation (15 %) : pour comparer les modèles, régler les paramètres et choisir le seuil ;
- test final (15 %) : à n'utiliser qu'une fois, à la fin, pour le chiffre du rapport.

Les données sont préparées par preparer(), donc avec la Tanzanie corrigée en supposant notre hypothèse vraie.
"""

from pathlib import Path

import pandas as pd
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split

from src.preparation import preparer

GRAINE = 42
CIBLE = "bank_account"
RACINE = Path(__file__).resolve().parents[1]
TRAIN = RACINE / "data" / "original" / "Train.csv"


def charger():
    """Lit Train.csv et applique la préparation commune."""
    return preparer(pd.read_csv(TRAIN))


def separer_cible(donnees):
    """Sépare les descripteurs X de la cible y, codée 1 pour Yes et 0 pour No."""
    return donnees.drop(columns=CIBLE), (donnees[CIBLE] == "Yes").astype(int)


def decouper(donnees=None):
    """Découpe 70/15/15, stratifié sur le pays et la cible, toujours identique grâce à la graine.

    Renvoie X_entrainement, X_validation, X_test, y_entrainement, y_validation, y_test.
    """
    donnees = charger() if donnees is None else donnees
    strates = donnees["country"] + "_" + donnees[CIBLE]
    entrainement, reste = train_test_split(donnees, test_size=0.3, stratify=strates, random_state=GRAINE)
    validation, test = train_test_split(reste, test_size=0.5, stratify=strates.loc[reste.index], random_state=GRAINE)
    X_ent, y_ent = separer_cible(entrainement)
    X_val, y_val = separer_cible(validation)
    X_test, y_test = separer_cible(test)
    return X_ent, X_val, X_test, y_ent, y_val, y_test


def evaluer(X, y_vrai, y_predit):
    """F1 macro au global, par pays et par genre : la mesure commune à tous les modèles."""
    y_vrai, y_predit = pd.Series(y_vrai, index=X.index), pd.Series(y_predit, index=X.index)
    lignes = [{"groupe": "Global", "effectif": len(X), "f1_macro": f1_score(y_vrai, y_predit, average="macro", labels=[0, 1], zero_division=0)}]
    for variable in ["country", "gender_of_respondent"]:
        for modalite, index in X.groupby(variable).groups.items():
            lignes.append({
                "groupe": f"{variable} = {modalite}", "effectif": len(index),
                "f1_macro": f1_score(y_vrai[index], y_predit[index], average="macro", labels=[0, 1], zero_division=0),
            })
    return pd.DataFrame(lignes).set_index("groupe").round(4)
