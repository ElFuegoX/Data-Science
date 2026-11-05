"""Questions et réponses en français, affichées par la page web."""

QUESTIONS = {
    "country": "Pays",
    "location_type": "Lieu de vie",
    "age_of_respondent": "Âge",
    "gender_of_respondent": "Genre",
    "education_level": "Niveau d'éducation",
    "job_type": "Emploi",
    "cellphone_access": "Accès à un téléphone portable",
    "marital_status": "Statut marital",
    "relationship_with_head": "Lien avec le chef de ménage",
    "household_size": "Personnes dans le ménage",
}

REPONSES = {
    "Rural": "Rural", "Urban": "Urbain", "Yes": "Oui", "No": "Non", "Female": "Femme", "Male": "Homme",
    "Kenya": "Kenya", "Rwanda": "Rwanda", "Tanzania": "Tanzanie", "Uganda": "Ouganda",
    "Child": "Enfant", "Head of Household": "Chef de ménage", "Other relative": "Autre membre",
    "Parent": "Parent", "Spouse": "Conjoint ou conjointe",
    "Divorced/Seperated": "Divorcé ou séparé", "Married/Living together": "Marié ou en couple",
    "Single/Never Married": "Célibataire", "Widowed": "Veuf ou veuve",
    "No formal education": "Aucune éducation formelle", "Primary education": "Primaire",
    "Secondary education": "Secondaire", "Tertiary education": "Supérieur",
    "Vocational/Specialised training": "Formation professionnelle",
    "Dont Know/Refuse to answer": "Ne sait pas ou refuse", "Farming and Fishing": "Agriculture et pêche",
    "Formally employed Government": "Salarié du public", "Formally employed Private": "Salarié du privé",
    "Government Dependent": "Aides de l'État", "Informally employed": "Emploi informel", "No Income": "Sans revenu",
    "Other Income": "Autre revenu", "Remittance Dependent": "Argent envoyé par des proches",
    "Self employed": "Indépendant",
}


def libelle(valeur):
    return REPONSES.get(valeur, valeur)
