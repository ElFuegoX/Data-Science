import os
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.neighbors import NearestNeighbors


# ---------------------------------------------------------------------------
# Colonnes (vérifie les noms contre X_ent.columns)
# ---------------------------------------------------------------------------
COLONNE_PAYS = "country"
COLONNES_NUM = ["age_of_respondent", "household_size"]
COLONNES_CAT = [
    c for c in [
        "gender_of_respondent",
        "cellphone_access",
        "relationship_with_head",
        "marital_status",
        "education_level",
        "job_type",
        "location_type",
    ]
    if c not in COLONNES_NUM and c != COLONNE_PAYS
]

CHEMIN_MODELE = os.path.join(
    os.path.dirname(__file__), "..", "models", "voisins.joblib"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _construire_encodeur():
    """One-hot pour les catégorielles, standardisation pour les numériques."""
    return ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), COLONNES_CAT),
            ("num", StandardScaler(), COLONNES_NUM),
        ]
    )


def _index_par_pays(X_enc, y, pays_serie):
    """Construit un NearestNeighbors par pays sur les données déjà encodées."""
    index = {}
    for pays in pays_serie.unique():
        masque = (pays_serie == pays).to_numpy()
        if masque.sum() == 0:
            continue
        nn = NearestNeighbors(n_neighbors=min(masque.sum(), 100))
        nn.fit(X_enc[masque])
        index[pays] = {
            "nn": nn,
            "indices": np.where(masque)[0],
            "y": y[masque],
        }
    return index


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
def entrainer(X, y, k=25, seuil=0.5):
    """Prépare l'encodage et l'index des voisins sur X, y.

    Renvoie l'objet à enregistrer avec joblib.dump.
    """
    X = X.reset_index(drop=True)
    y = np.asarray(y)

    # Vérification utile : toutes les colonnes attendues existent
    manquantes = set(COLONNES_CAT + COLONNES_NUM + [COLONNE_PAYS]) - set(X.columns)
    if manquantes:
        raise ValueError(f"Colonnes absentes de X : {sorted(manquantes)}")

    encodeur = _construire_encodeur()
    X_enc = encodeur.fit_transform(X)
    if hasattr(X_enc, "toarray"):
        X_enc = X_enc.toarray()

    pays = X[COLONNE_PAYS].reset_index(drop=True)

    nn_global = NearestNeighbors(n_neighbors=k)
    nn_global.fit(X_enc)

    index_pays = _index_par_pays(X_enc, y, pays)

    return {
        "encodeur": encodeur,
        "X_enc": X_enc,
        "y": y,
        "pays": pays.to_numpy(dtype=object),  # tableau simple : un Series pandas exigerait pyarrow pour être relu
        "nn_global": nn_global,
        "index_pays": index_pays,
        "k": k,
        "seuil": seuil,
        "colonnes": list(X.columns),
        "colonnes_cat": COLONNES_CAT,
        "colonnes_num": COLONNES_NUM,
        "colonne_pays": COLONNE_PAYS,
    }


@lru_cache(maxsize=1)
def charger_modele():
    """Lit models/voisins.joblib une seule fois, puis le garde en mémoire.

    Après avoir réenregistré le fichier dans le même processus, appeler charger_modele.cache_clear().
    """
    return joblib.load(CHEMIN_MODELE)


def voisins(profil, k=None, objet=None):
    """profil : DataFrame d'une ligne, mêmes colonnes que X.

    k=None utilise le k retenu à l'entraînement.
    objet=None charge models/voisins.joblib (comportement de prod).
    En exploration, on passe objet=objet_explo pour éviter le disque.
    Renvoie {"k": ..., "taux": ..., "taux_meme_pays": ...}.
    """
    obj = objet
    if obj is None:
        obj = charger_modele()

    k = int(k) if k is not None else int(obj["k"])

    # même préprocessing que l'entraînement
    profil = profil[obj["colonnes"]]
    profil_enc = obj["encodeur"].transform(profil)
    if hasattr(profil_enc, "toarray"):
        profil_enc = profil_enc.toarray()

    # --- taux tous pays ---
    _, indices = obj["nn_global"].kneighbors(profil_enc, n_neighbors=k)
    taux = float(np.mean(obj["y"][indices[0]]))

    # --- taux même pays ---
    col_pays = obj["colonne_pays"]
    pays_profil = profil[col_pays].iloc[0]
    if pays_profil in obj["index_pays"]:
        idx_pays = obj["index_pays"][pays_profil]
        k_pays = min(k, len(idx_pays["y"]))
        _, ind_pays = idx_pays["nn"].kneighbors(profil_enc, n_neighbors=k_pays)
        taux_meme_pays = float(np.mean(idx_pays["y"][ind_pays[0]]))
    else:
        taux_meme_pays = taux

    return {"k": k, "taux": taux, "taux_meme_pays": taux_meme_pays}