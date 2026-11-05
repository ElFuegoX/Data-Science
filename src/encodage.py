"""Encodages partagés par les modèles du groupe.

Une fonction utilisée dans un modèle enregistré doit rester importable au même endroit :
ne pas la renommer ni la déplacer sans réenregistrer les modèles qui l'utilisent.
"""

import numpy as np

BORNES_AGE = [25, 35, 45, 55, 65]  # tranches : moins de 25, 25-34, 35-44, 45-54, 55-64, 65 et plus


def decouper_age(colonne):
    """Remplace chaque âge par le numéro de sa tranche (0 à 5)."""
    return np.digitize(colonne, BORNES_AGE)
