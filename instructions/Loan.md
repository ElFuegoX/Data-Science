# Loan : modèle court (moins de questions)

Dans l'application, l'usage « moins de questions » donne une prédiction à partir de quelques réponses seulement, comparée au formulaire complet. Ta question est : combien de questions suffisent pour une estimation presque aussi bonne ?

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

Dans `notebooks/06_modele_court.ipynb` :

1. **Point de départ.** Pars des cinq variables prioritaires de l'EDA (décision 8) : `education_level`, `job_type`, `location_type`, `cellphone_access` et `country`.
2. **Courbe du nombre de questions.** Commence avec la meilleure variable seule. Ajoute ensuite, une à une, celle qui fait le plus monter le F1 macro de validation, jusqu'à toutes les variables. Trace le F1 macro selon le nombre de questions. C'est le graphique clé de ta partie.
3. **Choix du nombre de questions.** Retiens le plus petit ensemble qui reste proche du modèle complet. Fixe ta règle avant de regarder la courbe, par exemple « à moins de 0,02 du modèle complet ».
4. **Même type de modèle qu'Oscar.** Pour que la comparaison soit juste, utilise le type de modèle qu'Oscar retient, et vois avec lui. En attendant, commence avec une régression logistique.
5. **Seuil.** Choisis-le sur la validation pour maximiser le F1 macro. Ne garde pas 0,5 par défaut.
6. **Écarts selon les groupes.** Avec `evaluer()`, regarde si le modèle court perd plus dans un pays ou pour un genre que dans les autres.
7. **Évaluation finale.** Évalue une seule fois sur le test final, avec le modèle court retenu.

## Ce que tu livres pour l'interface

Joanès branche l'interface sur ces fonctions. Respecte exactement les noms.

Fichier `src/modele_court.py` :

```python
VARIABLES_COURTES = [...]  # les questions retenues, dans l'ordre où le formulaire les pose

def entrainer(X, y):
    """Entraîne le modèle court sur X[VARIABLES_COURTES] et choisit son seuil. Renvoie l'objet à enregistrer."""

def predire_court(profil):
    """profil : DataFrame d'une ligne qui contient au moins VARIABLES_COURTES. Renvoie la probabilité (float)."""
```

Fichier `models/modele_court.joblib` : l'objet produit par `entrainer`, enregistré avec `joblib.dump`. `predire_court` le charge.

`entrainer` est indispensable : le réentraînement automatique l'appellera plus tard.

## Ce qu'il faut écrire dans le notebook

- Le nombre de questions retenu et la perte de F1 macro par rapport au modèle complet.
- Si une enquête plus courte coûterait moins cher, cela reste une hypothèse du cadrage.
- Les résultats supposent vraie notre hypothèse sur la Tanzanie.

## Pour envoyer

`git add` tes fichiers, `git commit`, `git pull --rebase`, puis `git push`.
