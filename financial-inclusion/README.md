# Inclusion financière en Afrique : prédire la possession d'un compte bancaire

Projet intégrateur de Science des Données : de la donnée brute au déploiement.

## Problématique
Prédire si une personne possède un compte bancaire à partir de son profil socio-démographique,
au Kenya, au Rwanda, en Tanzanie et en Ouganda (classification binaire, cible `bank_account`).

## Données
Compétition [Financial Inclusion in Africa](https://zindi.africa/competitions/financial-inclusion-in-africa) (Zindi).
Les fichiers d'origine sont dans `data/original/` et ne sont jamais modifiés.

## Structure du projet (Proposition)
```
financial-inclusion/
├── data/original/   données d'origine
├── data/clean/      données nettoyées générées par le code
├── notebooks/       eda.ipynb
├── src/             code réutilisable (à venir)
├── api/             application de déploiement (à venir)
├── models/          modèle sauvegardé (à venir)
└── docs/            énoncé du TP et documents de référence
```

## Installation
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Utilisation
Ouvrir `notebooks/eda.ipynb` dans VS Code ou Jupyter et exécuter les cellules dans l'ordre.

## Avancement
- [x] Analyse exploratoire : qualité des données et analyse univariée
- [ ] Analyse bivariée et multivariée
- [ ] Modélisation
- [ ] Déploiement et réentraînement automatique
