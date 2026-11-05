# Oscar : modèle principal et facteurs du score

Ton modèle est le cœur de l'application. Il sert à quatre usages : la prédiction, les facteurs du score, « même profil, autres pays » et « même profil, autre genre ».

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
- Entraîne uniquement sur `X_ent, y_ent` (70 %).
- Compare, règle les paramètres et choisis le seuil sur `X_val, y_val` (15 %).
- Évalue **une seule fois** sur `X_test, y_test` (15 %), à la fin, avec le modèle retenu.
- Mesure avec `evaluer(X, y_vrai, y_predit)` : F1 macro global, par pays et par genre.
- Référence à battre : F1 macro de **0,462** sur la validation.
- Ne modifie pas `src/preparation.py` ni `src/decoupage.py`. Si tu as besoin d'un changement, demande à Joanès.
- Ne modifie que tes propres fichiers.

## Ce que tu fais

Dans `notebooks/04_modele_principal.ipynb` :

1. **Régression logistique.** Refais celle de ton EDA, mais sur les données du socle.
   - Encode les catégorielles en one-hot, éducation comprise (décision 9 : pas d'échelle ordonnée).
   - Donne à l'âge une forme qui permet une relation non linéaire, par exemple des tranches (décision 10).
2. **CatBoost.** C'est le meilleur des modèles à arbres testés (0,737 en validation croisée, contre 0,735 pour `HistGradientBoostingClassifier` et 0,731 pour LightGBM). Donne-lui les catégorielles avec `cat_features`. Il capte les interactions pays × téléphone et pays × lieu vues dans l'EDA (décision 14).
3. **Seuil.** Pour chaque modèle, choisis le seuil qui maximise le F1 macro. Ne garde pas 0,5 par défaut (décision 18). Dans `entrainer()`, choisis-le par validation croisée sur les données reçues, comme Loan dans `src/modele_court.py`.
4. **Comparaison.** Mets côte à côte les deux modèles et la référence naïve, avec `evaluer()`. Commente les écarts entre pays et entre genres (décisions 19 et 20).
5. **Vérification de `job_type`.** Vérifie que le modèle ne tire pas une fausse différence entre pays du codage de `job_type` (décision 15). Par exemple, compare la prédiction d'un même profil `Self employed` d'un pays à l'autre.
6. **Facteurs du score.** Pour un profil, donne les variables qui poussent le score vers le haut ou vers le bas. Utilise les coefficients pour la logistique, ou SHAP pour le boosting. Si tu utilises SHAP, ajoute-le à `requirements.txt` avec sa version.
7. **Évaluation finale.** Évalue le modèle retenu une seule fois sur le test final, et écris ce chiffre dans le notebook.

## Partage avec Loan

**Loan pousse la performance du modèle principal vers 0,80 de F1 macro** (voir `instructions/Loan.md`). Toi, tu construis le modèle de base, les facteurs du score et `src/modele_principal.py`.

- Livre d'abord ta version de `src/modele_principal.py`, qui respecte le contrat ci-dessous : Loan part de ton code.
- Loan cherche ensuite la meilleure configuration dans son propre notebook. Quand il la trouve, il modifie seulement `entrainer()` dans `src/modele_principal.py`, après accord avec toi.
- `expliquer()` doit continuer à fonctionner avec le modèle retenu : vérifiez-le ensemble.

## Modèle déployé (décision du groupe)

1. **Évaluer** comme décrit plus haut : apprendre sur `X_ent`, choisir sur `X_val`, puis passer une seule fois sur `X_test`. Ce chiffre va dans le rapport.
2. **Enregistrer le modèle déployé** en l'entraînant sur entraînement + validation (85 %) :
   ```python
   import pandas as pd
   objet = entrainer(pd.concat([X_ent, X_val]), pd.concat([y_ent, y_val]))
   ```
   Avec CatBoost ou la logistique, le seuil (ou les seuils par pays) est choisi par validation croisée dans `entrainer()`.
   Le test reste fermé : on n'apprend jamais dessus.
3. **Écrire dans le notebook** : « le modèle déployé apprend sur 85 % des données ; sa performance attendue est celle mesurée sur le test avec le modèle à 70 % ».

Le réentraînement automatique suivra la même règle : `entrainer()` recevra toutes les données disponibles, et la nouvelle version ne remplacera l'ancienne que si elle fait mieux sur le test.

## Ce que tu livres pour l'interface

Joanès branche l'interface sur ces fonctions. Respecte exactement les noms.

Fichier `src/modele_principal.py` :

```python
def entrainer(X, y):
    """Entraîne le modèle retenu et choisit son seuil. Renvoie un objet qui contient le pipeline et le seuil."""

def predire(profil):
    """profil : DataFrame d'une ligne, mêmes colonnes que X. Renvoie la probabilité d'avoir un compte (float)."""

def expliquer(profil):
    """Renvoie un DataFrame (variable, contribution), trié par effet absolu décroissant."""
```

Fichier `models/modele_principal.joblib` : le modèle retenu, enregistré avec `joblib.dump`. `predire` et `expliquer` le chargent.

`entrainer` est indispensable : le réentraînement automatique l'appellera plus tard.

Rien de plus n'est à faire pour « autres pays » et « autre genre ». L'interface change la colonne `country` ou `gender_of_respondent` du profil, puis rappelle `predire`. Vérifie seulement que `predire` fonctionne pour les quatre pays et les deux genres.

## Ce qu'il faut écrire dans le notebook

- Pourquoi tu retiens tel modèle, et avec quel seuil.
- Ses résultats par pays et par genre.
- Les facteurs du score sont des associations, pas des causes.
- Les résultats supposent vraie notre hypothèse sur la Tanzanie.

## Pour envoyer

`git add` tes fichiers, `git commit`, `git pull --rebase`, puis `git push`.
