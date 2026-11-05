# Félicité : personnes similaires (KNN)

Dans l'application, l'usage « personnes similaires » affiche le taux réel de comptes chez les personnes du jeu de données les plus proches du profil saisi. C'est ta seule tâche.

## Avant de commencer

1. `git checkout main`, puis `git pull`.
2. `pip install -r requirements.txt`.
3. Lis `notebooks/03_decoupage.ipynb` : il montre le découpage commun et la référence à battre.

## Règles communes

- Charge les données avec le socle, jamais en relisant le CSV toi-même :
  ```python
  import sys
  sys.path.insert(0, "..")
  from src.decoupage import decouper, evaluer
  X_ent, X_val, X_test, y_ent, y_val, y_test = decouper()
  ```
  Les données sont déjà préparées : Tanzanie corrigée en supposant notre hypothèse vraie, modalités rares regroupées, `uniqueid` et `year` retirés.
- Les voisins sont cherchés uniquement dans `X_ent, y_ent` (70 %).
- Choisis tes réglages sur `X_val, y_val` (15 %).
- Évalue **une seule fois** sur `X_test, y_test` (15 %), à la fin.
- Mesure avec `evaluer(X, y_vrai, y_predit)` : F1 macro global, par pays et par genre.
- Référence à battre : F1 macro de **0,462** sur la validation.
- Ne modifie pas `src/preparation.py` ni `src/decoupage.py`. Si tu as besoin d'un changement, demande à Joanès.
- Ne modifie que tes propres fichiers.

## Ce que tu fais

Dans `notebooks/05_knn.ipynb` :

1. **Distance.** Le KNN compare des profils, il faut donc mettre les variables sur une même échelle. Mets les catégorielles en one-hot et standardise l'âge et la taille du ménage. Une autre option est la distance de Gower. Explique ton choix : sans mise à l'échelle, l'âge écraserait toutes les autres variables.
2. **Score.** Pour une personne de la validation, son score est la part de comptes parmi ses k voisins dans l'entraînement. Transforme ce score en prédiction Oui/Non avec un seuil choisi sur la validation.
3. **Choix de k.** Essaie plusieurs valeurs, par exemple 5, 10, 25, 50 et 100. Trace le F1 macro de validation selon k, puis retiens un k. Un k trop petit donne un taux instable, et un k trop grand ne décrit plus le profil.
4. **Variante dans le même pays.** Calcule aussi le taux en cherchant les voisins uniquement dans le pays du profil (décision 24), et compare les deux variantes.
5. **Évaluation finale.** Évalue une seule fois sur le test final, avec le k retenu.

## Ce que tu livres pour l'interface

Joanès branche l'interface sur ces fonctions. Respecte exactement les noms.

Fichier `src/voisins.py` :

```python
def entrainer(X, y):
    """Prépare l'encodage et l'index des voisins sur X, y. Renvoie l'objet à enregistrer."""

def voisins(profil, k=None):
    """profil : DataFrame d'une ligne, mêmes colonnes que X. k=None utilise le k retenu.
    Renvoie un dict : {"k": ..., "taux": ..., "taux_meme_pays": ...}."""
```

Fichier `models/voisins.joblib` : l'objet produit par `entrainer`, enregistré avec `joblib.dump`. `voisins` le charge.

`entrainer` est indispensable : le réentraînement automatique l'appellera plus tard.

## Ce qu'il faut écrire dans le notebook

- Le k retenu et pourquoi.
- La comparaison entre tous les pays et le même pays.
- Le taux affiché est un taux observé chez des personnes proches, pas une cause ni une promesse.
- Les résultats supposent vraie notre hypothèse sur la Tanzanie.

## Pour envoyer

`git add` tes fichiers, `git commit`, `git pull --rebase`, puis `git push`.
