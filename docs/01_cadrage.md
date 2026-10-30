# Cadrage du projet

*Brouillon. Tout ce qui est marqué « à sourcer » ou « hypothèse » reste à confirmer.*

## Contexte

Une partie importante des adultes d'Afrique de l'Est n'a pas de compte bancaire. Sans compte, il est plus difficile d'épargner en sécurité, d'emprunter et de recevoir un salaire ou des aides *(à sourcer)*.

Le projet s'appuie sur le jeu de données Zindi « Financial Inclusion in Africa », issu d'enquêtes menées en Afrique de l'Est. Sa description détaillée relève de l'EDA.

## Acteurs et enjeux

Ces utilisateurs sont des hypothèses : aucun d'eux n'a été interrogé.

| Acteur | Enjeu |
|---|---|
| Banques et institutions de microfinance | Comprendre quels profils sont déjà bancarisés et lesquels ne le sont pas |
| Régulateurs et ministères | Repérer les inégalités d'accès entre groupes et entre pays |
| ONG et programmes d'inclusion | Mieux connaître les profils les moins bancarisés |
| Personnes interrogées | Ne pas être pénalisées par un modèle utilisant leur genre ou leur pays |

## Problème Data Science

- **Tâche :** classification binaire supervisée.
- **Cible :** `bank_account` (Yes/No).
- **Entrées :** les caractéristiques du profil, comme le pays, l'âge, le genre, l'éducation et l'emploi.
- **Sortie :** la probabilité que la personne ait un compte.

## Application visée

La base est un formulaire de profil qui affiche la prédiction. S'y ajoutent :

1. Les facteurs qui expliquent le score.
2. La prédiction pour le même profil dans les autres pays.
3. La prédiction pour le même profil avec l'autre genre.
4. Le taux réel parmi les personnes similaires, avec un KNN.
5. La prédiction avec moins de questions.

Le réentraînement automatique et le suivi des versions sont exigés par le TP. L'analyse des erreurs ira dans le rapport. L'indication de fiabilité du score sera ajoutée si le temps le permet.

## Intérêt et impact

L'application doit montrer ce qu'un profil dit de l'accès au compte bancaire, à quel point le modèle s'appuie sur le genre et le pays, et combien de questions suffisent pour une estimation correcte. Une enquête plus courte coûterait moins cher *(hypothèse)*.

## Critère de succès

Le modèle doit faire mieux qu'une référence naïve qui prédit toujours la classe la plus fréquente. Les métriques seront choisies en phase de modélisation.

## Limites connues

- Le modèle apprend des corrélations. Il ne dit pas ce qui se passerait si le profil d'une personne changeait.
- Une prédiction individuelle a une utilité limitée, puisqu'on peut poser la question directement.
