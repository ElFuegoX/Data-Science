# Inclusion financière en Afrique de l'Est

Projet intégrateur de Science des Données : prédire si une personne possède un compte bancaire à partir de son profil, de l'analyse des données jusqu'au déploiement.

Les données viennent de la compétition [Financial Inclusion in Africa](https://zindi.africa/competitions/financial-inclusion-in-africa) (Zindi) : Kenya, Rwanda, Tanzanie et Ouganda, cible `bank_account`.

## Structure

```
data/original/   données d'origine, jamais modifiées
docs/            cadrage, énoncé du TP, notebook de départ Zindi
notebooks/       01_eda, 02_preparation, 03_decoupage, puis la modélisation
src/             code réutilisable : preparation.py, decoupage.py
instructions/    tâches de modélisation de chaque membre
models/          modèles sauvegardés (à venir)
api/             API FastAPI, qui sert aussi la page : uvicorn api.main:app --reload
web/             page HTML/CSS/JS de l'application
app/             première interface Streamlit et fonctions provisoires
```

Les données préparées ne sont pas écrites sur disque : chaque notebook appelle `src/preparation.py`.

## Installation

Python 3.11 ou plus récent.

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Utilisation

Ouvrir les notebooks de `notebooks/` et exécuter les cellules dans l'ordre.

**Hypothèse sur la Tanzanie :** `src/preparation.py` corrige `location_type` et `marital_status` en Tanzanie, en supposant vraie notre hypothèse d'inversion des libellés. Aucune documentation du jeu de données ne la confirme (voir l'EDA, sections 3.7 et 3.8).

## Avancement

- [x] Cadrage : [docs/01_cadrage.md](docs/01_cadrage.md)
- [x] Analyse exploratoire : [notebooks/01_eda.ipynb](notebooks/01_eda.ipynb)
- [x] Préparation des données : [notebooks/02_preparation.ipynb](notebooks/02_preparation.ipynb)
- [x] Découpage commun 70/15/15 et référence naïve : [notebooks/03_decoupage.ipynb](notebooks/03_decoupage.ipynb)
- [ ] Modélisation : modèle principal (Oscar), KNN (Félicité), modèle court (Loan). Voir [instructions/](instructions/)
- [ ] Interface : API FastAPI ([api/](api/)) et page web ([web/](web/)), encore branchées sur des fonctions provisoires. Image Docker prête pour un Space Hugging Face
- [ ] Déploiement et réentraînement automatique
