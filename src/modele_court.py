"""Modèle court : prédire la possession d'un compte bancaire avec peu de questions.

Les données d'entraînement sont préparées par src.preparation.preparer, donc avec la Tanzanie corrigée
en supposant notre hypothèse vraie. Un profil saisi dans le formulaire doit passer par
preparer(corriger=False) avant d'être donné à predire_court.
"""

from pathlib import Path

import joblib
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

RACINE = Path(__file__).resolve().parents[1]  # racine du dépôt, calculée comme dans decoupage.py
CHEMIN_MODELE = RACINE / "models" / "modele_court.joblib"

VARIABLES_COURTES = ["job_type", "education_level", "country"]  # à remettre dans l'ordre du formulaire (voir Joanès)

BORNES_AGE = [25, 35, 45, 55, 65]  # tranches : moins de 25, 25-34, 35-44, 45-54, 55-64, 65 et plus
NUMERIQUES = ["age_of_respondent", "household_size"]


def decouper_age(colonne):
    """Remplace chaque âge par le numéro de sa tranche (0 à 5)."""
    return np.digitize(colonne, BORNES_AGE)


def construire_modele(variables):
    """Construit la régression logistique pour la liste de variables (questions) donnée."""
    categorielles = [v for v in variables if v not in NUMERIQUES]
    transformations = []

    if categorielles:
        transformations.append(("categories", OneHotEncoder(handle_unknown="ignore"), categorielles))

    if "age_of_respondent" in variables:
        age_en_tranches = Pipeline([
            ("tranches", FunctionTransformer(decouper_age)),
            ("indicatrices", OneHotEncoder(handle_unknown="ignore")),
        ])
        transformations.append(("age", age_en_tranches, ["age_of_respondent"]))

    if "household_size" in variables:
        transformations.append(("menage", StandardScaler(), ["household_size"]))

    return Pipeline([
        ("preparation", ColumnTransformer(transformations)),
        ("modele", LogisticRegression(max_iter=1000, random_state=42)),
    ])


def meilleur_seuil(y_vrai, probabilites):
    """Cherche, entre 0,05 et 0,95, le seuil qui maximise le F1 macro."""
    seuils = np.arange(0.05, 0.96, 0.01)
    scores = []
    for seuil in seuils:
        predictions = (probabilites >= seuil).astype(int)
        scores.append(f1_score(y_vrai, predictions, average="macro", labels=[0, 1], zero_division=0))
    position = int(np.argmax(scores))
    return seuils[position], scores[position]


def entrainer(X, y):
    """Entraîne le modèle court sur X[VARIABLES_COURTES] et choisit son seuil. Renvoie l'objet à enregistrer."""
    donnees_courtes = X[VARIABLES_COURTES]  # on ne garde que les questions du modèle court
    modele = construire_modele(VARIABLES_COURTES)

    plis = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)  # 5 plis qui gardent la part de comptes
    probabilites = cross_val_predict(modele, donnees_courtes, y, cv=plis, method="predict_proba")[:, 1]  # chaque ligne est prédite sans avoir servi à l'apprentissage
    seuil, _ = meilleur_seuil(y, probabilites)  # seuil choisi sur ces prédictions

    modele.fit(donnees_courtes, y)  # modèle définitif, entraîné sur toutes les lignes reçues
    return {"modele": modele, "seuil": round(float(seuil), 2), "variables": list(VARIABLES_COURTES)}  # seuil arrondi à 2 décimales


def predire_court(profil):
    """profil : DataFrame d'une ligne qui contient au moins VARIABLES_COURTES. Renvoie la probabilité (float)."""
    objet = joblib.load(CHEMIN_MODELE)  # charge le modèle enregistré
    probabilite = objet["modele"].predict_proba(profil[objet["variables"]])[:, 1][0]
    return float(probabilite)