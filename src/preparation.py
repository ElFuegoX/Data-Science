"""Prétraitement unique du train, du test et de l'application.

La correction de la Tanzanie suppose vraie notre hypothèse d'inversion des libellés.
Cette hypothèse vient de l'EDA : aucune documentation du jeu de données ne la confirme.
"""

COLONNES_RETIREES = ["uniqueid", "year"]

LIEU_TANZANIE = {"Rural": "Urban", "Urban": "Rural"}
STATUT_TANZANIE = {
    "Single/Never Married": "Married/Living together",
    "Divorced/Seperated": "Single/Never Married",
    "Married/Living together": "Divorced/Seperated",
}

MODALITES_RARES = {
    "marital_status": {"Dont know": "Single/Never Married"},
    "education_level": {"Other/Dont know/RTA": "No formal education"},
    "relationship_with_head": {"Other non-relatives": "Other relative"},
}


def corriger_tanzanie(donnees):
    """Inverse le lieu et permute le statut marital en Tanzanie, sous notre hypothèse.

    À n'appliquer qu'une fois : un second passage modifierait à nouveau les libellés.
    """
    copie = donnees.copy()
    tanzanie = copie["country"] == "Tanzania"
    copie.loc[tanzanie, "location_type"] = copie.loc[tanzanie, "location_type"].replace(LIEU_TANZANIE)
    copie.loc[tanzanie, "marital_status"] = copie.loc[tanzanie, "marital_status"].replace(STATUT_TANZANIE)
    return copie


def regrouper_rares(donnees):
    """Regroupe les trois modalités trop rares pour être estimées seules. Ignore les colonnes absentes (formulaire court)."""
    copie = donnees.copy()
    for variable, regroupement in MODALITES_RARES.items():
        if variable in copie:
            copie[variable] = copie[variable].replace(regroupement)
    return copie


def preparer(donnees, corriger=True):
    """Applique les décisions de préparation.

    Laisser corriger=True pour Train.csv et Test.csv, dont les libellés sont visés par notre hypothèse.
    Passer corriger=False pour le formulaire : la personne y déclare elle-même son lieu et son statut.
    """
    corrigees = corriger_tanzanie(donnees) if corriger else donnees
    return regrouper_rares(corrigees).drop(columns=COLONNES_RETIREES, errors="ignore")
