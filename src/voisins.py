"""Personnes similaires (KNN) — code de production (v2).

API imposée (inchangée) :
    entrainer(X, y, k=..., seuil=..., weights="uniform") -> objet à joblib.dump
    voisins(profil, k=None, objet=None)                  -> {"k", "taux", "taux_meme_pays"}

Options ajoutées à entrainer() (toutes facultatives, défauts = comportement v1) :
    weights        "uniform" | "distance"   moyenne simple ou pondérée par 1/(distance+eps)
    eps            décalage de 1/(d+eps) (évite qu'un voisin à distance 0 écrase les autres)
    metric         "euclidean" | "manhattan" | "cosine" | "gower"
    poids_vars     None | dict {colonne: poids} | "mi" | "logit"
                   "mi"   : information mutuelle avec la cible (calculée sur X, y fournis)
                   "logit": plus forte |coefficient| de la régression logistique par variable
    puissance      exposant appliqué aux poids "mi"/"logit" (0 = tous égaux, 1 = brut, 2 = accentué)
    poids_pays     None = pays hors distance (v1) ; sinon poids (> 0) de `country` dans la distance
    age_mode       "standard" (v1) | "tranches" (âge découpé en tranches, encodé one-hot)
    seuils_pays    {pays: seuil}  seuil de décision par pays (repli : `seuil`)
    k_pays         {pays: k}      k par pays (repli : `k`)

L'objet retourné reste un dict de types standards + objets scikit-learn
(aucune classe maison dans le pickle : le joblib se recharge quel que soit
le nom d'import du module).
"""

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import (
    OneHotEncoder, StandardScaler, OrdinalEncoder, MinMaxScaler,
)
from sklearn.neighbors import NearestNeighbors

COLONNE_PAYS = "country"
COLONNE_AGE = "age_of_respondent"
COLONNE_AGE_TR = "age_tranche"
COLONNES_NUM = ["age_of_respondent", "household_size"]
COLONNES_CAT = [
    "location_type", "cellphone_access", "gender_of_respondent",
    "relationship_with_head", "marital_status", "education_level", "job_type",
]

# Tranches d'âge : <25, 25-34, 35-44, 45-54, 55-64, 65+
# (si src/encodage.py fournit déjà un découpage, remplacer BORNES_AGE_INTERNES par ses bornes)
BORNES_AGE_INTERNES = [25, 35, 45, 55, 65]

METRIQUES = ("euclidean", "manhattan", "cosine", "gower")
PONDERATIONS = ("uniform", "distance")
MODES_AGE = ("standard", "tranches")

CHEMIN_MODELE = os.path.join(os.path.dirname(__file__), "..", "models", "voisins.joblib")


# ----------------------------------------------------------------------
# Encodage
# ----------------------------------------------------------------------
def _preparer(X, age_mode, metric):
    """Ajoute la colonne de tranche d'âge si demandée (sans objet pour Gower)."""
    if age_mode == "tranches" and metric != "gower":
        X = X.copy()
        tr = np.digitize(X[COLONNE_AGE].to_numpy(dtype=float), BORNES_AGE_INTERNES)
        X[COLONNE_AGE_TR] = pd.Series(tr, index=X.index).astype(str)
    return X


def _colonnes(metric, age_mode, pays_dans_dist):
    cat, num = list(COLONNES_CAT), list(COLONNES_NUM)
    if pays_dans_dist:
        cat.append(COLONNE_PAYS)
    if age_mode == "tranches" and metric != "gower":
        num.remove(COLONNE_AGE)
        cat.append(COLONNE_AGE_TR)
    return cat, num


def _construire_encodeur(cat, num, metric):
    if metric == "gower":
        t_cat = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
        t_num = MinMaxScaler(clip=True)          # plages [0, 1] -> |a-b| <= 1
    else:
        t_cat = OneHotEncoder(handle_unknown="ignore")
        t_num = StandardScaler()
    return ColumnTransformer(
        transformers=[("cat", t_cat, cat), ("num", t_num, num)],
        sparse_threshold=0.0,                    # sortie toujours dense
    )


def _sources(encodeur):
    """Pour chaque colonne encodée, nom de la variable d'origine."""
    src = []
    for nom, trans, cols in encodeur.transformers_:
        if nom == "remainder":
            continue
        if isinstance(trans, OneHotEncoder):
            for c, cats in zip(cols, trans.categories_):
                src += [c] * len(cats)
        else:
            src += list(cols)
    return [COLONNE_AGE if s == COLONNE_AGE_TR else s for s in src]


def _vers_dense(M):
    if hasattr(M, "toarray"):
        M = M.toarray()
    return np.asarray(M, dtype=np.float64)


def _encoder(obj, X):
    """Encode (et pondère, sauf Gower où les poids entrent dans la distance)."""
    X = _preparer(X[obj["colonnes"]], obj["age_mode"], obj["metric"])
    M = _vers_dense(obj["encodeur"].transform(X))
    if obj["metric"] != "gower":
        M = M * obj["w_enc"]
    return M


# ----------------------------------------------------------------------
# Poids des variables
# ----------------------------------------------------------------------
def poids_information_mutuelle(X, y):
    """Information mutuelle (variable, cible), normalisée à moyenne 1. Hors pays."""
    from sklearn.metrics import mutual_info_score
    y = np.asarray(y)
    mi = {}
    for c in COLONNES_CAT + COLONNES_NUM:
        v = X[c]
        if c in COLONNES_NUM:
            v = pd.qcut(v, q=10, duplicates="drop")
        mi[c] = mutual_info_score(v.astype(str).to_numpy(), y)
    m = np.mean(list(mi.values()))
    return {c: max(val / m, 1e-3) for c, val in mi.items()}


def poids_logistique(X, y):
    """Plus forte |coefficient| de la logistique par variable, normalisée à moyenne 1. Hors pays."""
    from sklearn.linear_model import LogisticRegression
    enc = _construire_encodeur(COLONNES_CAT, COLONNES_NUM, "euclidean")
    M = _vers_dense(enc.fit_transform(X[COLONNES_CAT + COLONNES_NUM]))
    lr = LogisticRegression(max_iter=2000).fit(M, np.asarray(y))
    brut = {}
    for s, coef in zip(_sources(enc), np.abs(lr.coef_[0])):
        brut[s] = max(brut.get(s, 0.0), float(coef))
    m = np.mean(list(brut.values()))
    return {c: max(val / m, 1e-3) for c, val in brut.items()}


def _resoudre_poids(X, y, poids_vars, puissance):
    if poids_vars is None:
        return {}
    if isinstance(poids_vars, dict):
        return {c: float(w) for c, w in poids_vars.items()}
    if poids_vars == "mi":
        base = poids_information_mutuelle(X, y)
    elif poids_vars == "logit":
        base = poids_logistique(X, y)
    else:
        raise ValueError("poids_vars doit être None, un dict, 'mi' ou 'logit'")
    return {c: w ** float(puissance) for c, w in base.items()}


# ----------------------------------------------------------------------
# Recherche des voisins
# ----------------------------------------------------------------------
def _gower_knn(X_ref, Q, k, is_cat, w, bloc=256):
    """k plus proches voisins en distance de Gower pondérée. Retourne (distances, indices) triés."""
    n = len(X_ref)
    k = min(k, n)
    wsum = float(np.sum(w))
    d_out = np.empty((len(Q), k))
    i_out = np.empty((len(Q), k), dtype=np.int64)
    for debut in range(0, len(Q), bloc):
        Qb = Q[debut:debut + bloc]
        D = np.zeros((len(Qb), n))
        for j in range(Q.shape[1]):
            if is_cat[j]:
                dj = (Qb[:, j][:, None] != X_ref[:, j][None, :]).astype(np.float64)
            else:
                dj = np.abs(Qb[:, j][:, None] - X_ref[:, j][None, :])
            D += w[j] * dj
        D /= wsum
        if k < n:
            part = np.argpartition(D, k - 1, axis=1)[:, :k]
        else:
            part = np.tile(np.arange(n), (len(Qb), 1))
        dp = np.take_along_axis(D, part, axis=1)
        ordre = np.argsort(dp, axis=1)
        i_out[debut:debut + len(Qb)] = np.take_along_axis(part, ordre, axis=1)
        d_out[debut:debut + len(Qb)] = np.take_along_axis(dp, ordre, axis=1)
    return d_out, i_out


def _construire_index(X_enc, k, metric):
    if metric == "gower":
        return None                                  # Gower : calcul direct sur X_enc
    nn = NearestNeighbors(n_neighbors=min(k, len(X_enc)), metric=metric, algorithm="brute")
    nn.fit(X_enc)
    return nn


def _index_par_pays(X_enc, y, pays_serie, k_max, metric):
    index = {}
    for pays in pays_serie.unique():
        masque = (pays_serie == pays).to_numpy()
        n = int(masque.sum())
        if n == 0:
            continue
        sous = X_enc[masque]
        index[pays] = {
            "nn": _construire_index(sous, k_max, metric),
            "X": sous if metric == "gower" else None,
            "indices": np.where(masque)[0],
            "y": y[masque],
        }
    return index


def _kneighbors(obj, entree, Q, k):
    """entree = None -> index global ; sinon entrée de index_pays."""
    if obj["metric"] == "gower":
        X_ref = obj["X_enc"] if entree is None else entree["X"]
        return _gower_knn(X_ref, Q, k, obj["is_cat"], obj["w_enc"])
    nn = obj["nn_global"] if entree is None else entree["nn"]
    return nn.kneighbors(Q, n_neighbors=min(k, nn.n_samples_fit_))


def calculer_voisinage(obj, X, k_max=None, variante="global"):
    """Distances et cibles des k_max plus proches voisins de chaque ligne de X.

    Retourne (d, y_voisins), tableaux (n, k_max), triés par distance croissante.
    Si moins de k_max voisins existent (petit pays), le reste est NaN.
    variante : "global" (tous pays) ou "meme_pays".
    """
    k_max = int(k_max) if k_max is not None else int(obj["k_max"])
    Q = _encoder(obj, X)
    n = len(Q)
    d = np.full((n, k_max), np.nan)
    yv = np.full((n, k_max), np.nan)

    def remplir(masque, entree):
        dd, ii = _kneighbors(obj, entree, Q[masque], k_max)
        y_ref = obj["y"] if entree is None else entree["y"]
        d[masque, :dd.shape[1]] = dd
        yv[masque, :dd.shape[1]] = y_ref[ii]

    tous = np.ones(n, dtype=bool)
    if variante == "global":
        remplir(tous, None)
        return d, yv

    pays_x = X[COLONNE_PAYS].to_numpy()
    connus = np.zeros(n, dtype=bool)
    for pays, entree in obj["index_pays"].items():
        m = pays_x == pays
        if m.any():
            remplir(m, entree)
            connus |= m
    if (~connus).any():                              # pays inconnu : repli global (comme v1)
        remplir(~connus, None)
    return d, yv


def taux_par_k(d, y_voisins, ks, weights="uniform", eps=1e-6):
    """Taux estimé pour chaque k de `ks`, en un seul passage. Retourne (n, len(ks))."""
    valide = ~np.isnan(y_voisins)
    y0 = np.where(valide, y_voisins, 0.0)
    if weights == "distance":
        w = np.where(valide, 1.0 / (np.nan_to_num(d) + eps), 0.0)
    else:
        w = valide.astype(np.float64)
    cs_wy = np.cumsum(w * y0, axis=1)
    cs_w = np.cumsum(w, axis=1)
    cols = [min(int(k), d.shape[1]) - 1 for k in ks]
    return cs_wy[:, cols] / np.maximum(cs_w[:, cols], 1e-12)


# ----------------------------------------------------------------------
# API
# ----------------------------------------------------------------------
def entrainer(X, y, k=100, seuil=0.30, weights="uniform", metric="euclidean",
              poids_vars=None, puissance=1.0, poids_pays=None, age_mode="standard",
              eps=1e-6, seuils_pays=None, k_pays=None, k_max=300):
    if metric not in METRIQUES:
        raise ValueError(f"metric doit être dans {METRIQUES}")
    if weights not in PONDERATIONS:
        raise ValueError(f"weights doit être dans {PONDERATIONS}")
    if age_mode not in MODES_AGE:
        raise ValueError(f"age_mode doit être dans {MODES_AGE}")

    X = X.reset_index(drop=True)
    y = np.asarray(y)

    manquantes = set(COLONNES_CAT + COLONNES_NUM + [COLONNE_PAYS]) - set(X.columns)
    if manquantes:
        raise ValueError(f"Colonnes absentes de X : {sorted(manquantes)}")

    pays_dans_dist = poids_pays is not None and float(poids_pays) > 0
    poids = _resoudre_poids(X, y, poids_vars, puissance)
    if pays_dans_dist:
        poids[COLONNE_PAYS] = float(poids_pays)

    cat, num = _colonnes(metric, age_mode, pays_dans_dist)
    encodeur = _construire_encodeur(cat, num, metric)
    X_enc = _vers_dense(encodeur.fit_transform(_preparer(X, age_mode, metric)))
    sources = _sources(encodeur)
    w_enc = np.array([poids.get(s, 1.0) for s in sources], dtype=np.float64)
    is_cat = np.array([s in set(cat) for s in sources])
    if metric != "gower":
        X_enc = X_enc * w_enc

    pays = X[COLONNE_PAYS].reset_index(drop=True)
    k_max = max(int(k_max), int(k), *(int(v) for v in (k_pays or {}).values()))
    nn_global = _construire_index(X_enc, k_max, metric)
    index_pays = _index_par_pays(X_enc, y, pays, k_max, metric)

    return {
        "encodeur": encodeur,
        "X_enc": X_enc,
        "y": y,
        "pays": pays,
        "nn_global": nn_global,
        "index_pays": index_pays,
        "k": int(k),
        "k_max": int(k_max),
        "seuil": float(seuil),
        "weights": weights,
        "eps": float(eps),
        "metric": metric,
        "poids": poids,
        "w_enc": w_enc,
        "is_cat": is_cat,
        "age_mode": age_mode,
        "pays_dans_dist": bool(pays_dans_dist),
        "seuils_pays": {p: float(s) for p, s in (seuils_pays or {}).items()},
        "k_pays": {p: int(v) for p, v in (k_pays or {}).items()},
        "colonnes": list(X.columns),
        "colonne_pays": COLONNE_PAYS,
    }


def _charger(objet):
    return objet if objet is not None else joblib.load(CHEMIN_MODELE)


def voisins(profil, k=None, objet=None):
    obj = _charger(objet)
    profil = profil.iloc[[0]]
    pays = profil[COLONNE_PAYS].iloc[0]
    if k is None:
        k = obj.get("k_pays", {}).get(pays, obj["k"])
    k = int(k)

    d, yv = calculer_voisinage(obj, profil, k_max=k, variante="global")
    taux = float(taux_par_k(d, yv, [k], obj["weights"], obj["eps"])[0, 0])

    d, yv = calculer_voisinage(obj, profil, k_max=k, variante="meme_pays")
    taux_meme_pays = float(taux_par_k(d, yv, [k], obj["weights"], obj["eps"])[0, 0])

    return {"k": k, "taux": taux, "taux_meme_pays": taux_meme_pays}


def predire(X, objet=None, variante=None, k=None, seuil=None):
    """Décision 0/1 pour toutes les lignes de X (batch).

    Applique k_pays et seuils_pays de l'objet, sauf si k / seuil sont imposés.
    variante : "global" | "meme_pays" ; par défaut celle enregistrée dans l'objet (sinon "global").
    Retourne (y_pred, taux).
    """
    obj = _charger(objet)
    variante = variante or obj.get("variante", "global")
    kd = int(k) if k is not None else int(obj["k"])
    sd = float(seuil) if seuil is not None else float(obj["seuil"])
    pays = X[COLONNE_PAYS].to_numpy()

    if k is None and obj.get("k_pays"):
        k_ligne = np.array([obj["k_pays"].get(p, kd) for p in pays])
    else:
        k_ligne = np.full(len(X), kd)
    ks = sorted(set(int(v) for v in k_ligne))

    d, yv = calculer_voisinage(obj, X, k_max=max(ks), variante=variante)
    T = taux_par_k(d, yv, ks, obj["weights"], obj["eps"])
    col = np.array([ks.index(int(v)) for v in k_ligne])
    taux = T[np.arange(len(X)), col]

    if seuil is None and obj.get("seuils_pays"):
        thr = np.array([obj["seuils_pays"].get(p, sd) for p in pays])
    else:
        thr = np.full(len(X), sd)
    return (taux >= thr).astype(int), taux
