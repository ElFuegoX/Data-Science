// Page de l'application : le portrait est une phrase à trous, l'estimation se lit comme un article.

const etat = { ref: null, complet: {}, court: {}, dernierComplet: null, minuteurs: {} };

const pourcent = (valeur) => `${Math.round(valeur * 100)} %`;
const signe = (valeur) => `${valeur > 0 ? "+" : valeur < 0 ? "−" : ""}${Math.abs(Math.round(valeur * 100))} pt`;
const echapper = (texte) => String(texte).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// Accord selon le genre saisi : masculin, féminin, ou forme neutre si le genre n'est pas demandé.
const accord = (genre, masculin, feminin, neutre) => (genre === "Male" ? masculin : genre === "Female" ? feminin : neutre);

// Comment chaque réponse s'écrit dans la phrase.
const MOTS = {
  gender_of_respondent: { Female: "une femme", Male: "un homme" },
  country: { Kenya: "au Kenya", Rwanda: "au Rwanda", Tanzania: "en Tanzanie", Uganda: "en Ouganda" },
  location_type: { Rural: "rurale", Urban: "urbaine" },
  cellphone_access: { Yes: "J'ai", No: "Je n'ai pas" },
  marital_status: {
    "Single/Never Married": () => "célibataire",
    "Married/Living together": (g) => `${accord(g, "marié", "mariée", "marié·e")} ou en couple`,
    "Divorced/Seperated": (g) => accord(g, "divorcé ou séparé", "divorcée ou séparée", "divorcé·e ou séparé·e"),
    Widowed: (g) => accord(g, "veuf", "veuve", "veuf ou veuve"),
  },
  relationship_with_head: {
    "Head of Household": (g) => accord(g, "le chef du ménage", "la cheffe du ménage", "à la tête du ménage"),
    Spouse: (g) => accord(g, "le conjoint de la cheffe", "la conjointe du chef", "en couple avec la personne à la tête du ménage"),
    Child: () => "l'enfant du chef de ménage",
    Parent: (g) => accord(g, "le père du chef de ménage", "la mère du chef de ménage", "un parent du chef de ménage"),
    "Other relative": () => "un autre membre de la famille",
  },
  education_level: {
    "No formal education": "aucune éducation formelle",
    "Primary education": "l'école primaire",
    "Secondary education": "le secondaire",
    "Tertiary education": "le supérieur",
    "Vocational/Specialised training": "une formation professionnelle",
  },
  job_type: {
    "Farming and Fishing": "de l'agriculture ou de la pêche",
    "Self employed": "de mon travail, à mon compte",
    "Informally employed": "d'un emploi informel",
    "Formally employed Private": "d'un salaire dans le privé",
    "Formally employed Government": "d'un salaire dans le public",
    "Remittance Dependent": "de l'argent envoyé par des proches",
    "Government Dependent": "des aides de l'État",
    "Other Income": "d'un autre revenu",
    "No Income": "sans aucun revenu",
    "Dont Know/Refuse to answer": "de ce que je préfère ne pas dire",
  },
};

const PHRASE_COMPLETE = "Je suis {gender_of_respondent}, j'ai {age_of_respondent} et je suis {marital_status}. "
  + "J'habite {country}, en zone {location_type}, dans un ménage de {household_size} où je suis {relationship_with_head}. "
  + "Mon parcours scolaire : {education_level}. Je vis surtout {job_type}. {cellphone_access} accès à un téléphone portable.";

// Pour la version courte, dont les questions peuvent changer : une petite phrase par question.
const MINI_PHRASES = {
  country: "J'habite {country}.", location_type: "Je vis en zone {location_type}.", gender_of_respondent: "Je suis {gender_of_respondent}.",
  age_of_respondent: "J'ai {age_of_respondent}.", marital_status: "Je suis {marital_status}.",
  relationship_with_head: "Dans mon ménage, je suis {relationship_with_head}.", household_size: "Mon ménage compte {household_size}.",
  education_level: "Mon parcours scolaire : {education_level}.", job_type: "Je vis surtout {job_type}.",
  cellphone_access: "{cellphone_access} accès à un téléphone portable.",
};

const SUFFIXES = {
  age_of_respondent: () => "ans",
  household_size: (n) => (n > 1 ? "personnes" : "personne"),
};

function mot(variable, valeur, genre) {
  const forme = MOTS[variable]?.[valeur];
  if (typeof forme === "function") return forme(genre);
  return forme ?? etat.ref.libelles[valeur] ?? valeur;
}

// Render endort le serveur gratuit après un moment sans visite : le premier appel peut prendre jusqu'à une minute.
async function reveiller() {
  const message = document.getElementById("provisoire");
  const debut = Date.now();
  const attente = setTimeout(() => {
    message.textContent = "Le serveur se réveille, cela peut prendre jusqu'à une minute…";
    message.hidden = false;
  }, 2500);
  try {
    while (true) {
      try {
        const reponse = await fetch("/api/sante", { cache: "no-store" });
        if (reponse.ok) return;
      } catch (erreur) { /* serveur encore endormi */ }
      if (Date.now() - debut > 120000) throw new Error("le serveur ne répond pas. Réessayez dans une minute.");
      await new Promise((fin) => setTimeout(fin, 4000));
    }
  } finally {
    clearTimeout(attente);
    message.hidden = true;
  }
}

async function appeler(chemin, corps) {
  const reponse = await fetch(chemin, corps ? {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps),
  } : undefined);
  const donnees = await reponse.json();
  if (!reponse.ok) throw new Error(donnees.detail ?? "Erreur du serveur.");
  return donnees;
}

// La phrase à trous

function ajusterLargeur(select) {
  const mesure = document.getElementById("mesure");
  mesure.textContent = select.options[select.selectedIndex].text;
  select.style.width = `${mesure.getBoundingClientRect().width + 6}px`;
}

function construirePhrase(conteneur, modele, reponses, quandChange) {
  const { numeriques, questions } = etat.ref;
  const genre = () => reponses.gender_of_respondent ?? null;
  const selects = [];

  const reecrire = () => selects.forEach(({ select, variable }) => {
    [...select.options].forEach((option) => { option.text = mot(variable, option.value, genre()); });
    ajusterLargeur(select);
  });

  modele.split(/(\{\w+\})/).forEach((morceau) => {
    const variable = morceau.match(/^\{(\w+)\}$/)?.[1];
    if (!variable) {
      conteneur.append(morceau);
      return;
    }
    if (!(variable in reponses)) reponses[variable] = etat.ref.defauts[variable];

    if (variable in numeriques) {
      const [bas, haut] = numeriques[variable];
      const champ = document.createElement("input");
      Object.assign(champ, { type: "number", min: bas, max: haut, value: reponses[variable], className: "trou", inputMode: "numeric" });
      champ.setAttribute("aria-label", questions[variable]);
      const suffixe = document.createElement("span");
      suffixe.textContent = ` ${SUFFIXES[variable](reponses[variable])}`;
      const largeur = () => { champ.style.width = `${String(champ.value || reponses[variable]).length + 0.7}ch`; };
      largeur();
      champ.addEventListener("input", () => {
        const valeur = Number(champ.value);
        largeur();
        if (Number.isInteger(valeur) && valeur >= bas && valeur <= haut) {
          reponses[variable] = valeur;
          suffixe.textContent = ` ${SUFFIXES[variable](valeur)}`;
          quandChange();
        }
      });
      champ.addEventListener("blur", () => { champ.value = reponses[variable]; largeur(); });
      const groupe = document.createElement("span");
      groupe.className = "insecable";
      groupe.append(champ, suffixe);
      conteneur.append(groupe);
      return;
    }

    const select = document.createElement("select");
    select.className = "trou";
    select.setAttribute("aria-label", questions[variable]);
    etat.ref.choix[variable].forEach((valeur) => {
      select.add(new Option(mot(variable, valeur, genre()), valeur, false, valeur === reponses[variable]));
    });
    select.addEventListener("change", () => {
      reponses[variable] = select.value;
      if (variable === "gender_of_respondent") reecrire();
      else ajusterLargeur(select);
      quandChange();
    });
    selects.push({ select, variable });
    conteneur.append(select);
  });

  reecrire();
  document.fonts?.ready.then(reecrire);
  window.addEventListener("resize", () => plusTard(`largeur-${conteneur.id}`, reecrire, 150));
}

function plusTard(nom, action, delai = 180) {
  clearTimeout(etat.minuteurs[nom]);
  etat.minuteurs[nom] = setTimeout(action, delai);
}

// L'article

function echelle(probabilite) {
  const moyenne = etat.ref.taux_global;
  const graduations = [0, 0.25, 0.5, 0.75, 1].map((g) => `<span class="graduation" style="left:${g * 100}%">${Math.round(g * 100)}</span>`).join("");
  return `<div class="ligne"></div>${graduations}
    <div class="marque-point moyenne" style="left:${moyenne * 100}%"><div class="rond"></div><div class="legende">moyenne ${pourcent(moyenne)}</div></div>
    <div class="marque-point personne" style="left:${probabilite * 100}%"><div class="legende">ce portrait</div><div class="rond"></div></div>`;
}

function phraseProbabilite(probabilite) {
  const ecart = Math.round((probabilite - etat.ref.taux_global) * 100);
  if (Math.abs(ecart) < 1) return `de chances d'avoir un compte, autant que la moyenne de l'échantillon (${pourcent(etat.ref.taux_global)}).`;
  return `de chances d'avoir un compte, soit ${Math.abs(ecart)} points de ${ecart > 0 ? "plus" : "moins"} que la moyenne de l'échantillon (${pourcent(etat.ref.taux_global)}).`;
}

function facteurs(lignes) {
  const maximum = Math.max(...lignes.map((l) => Math.abs(l.contribution)), 0.01);
  return lignes.map((l) => {
    const largeur = (Math.abs(l.contribution) / maximum * 38).toFixed(1);
    const barre = l.contribution >= 0
      ? `<div class="barre haut" style="width:${largeur}%"></div><div class="valeur" style="left:calc(50% + ${largeur}% + 8px)">${signe(l.contribution)}</div>`
      : `<div class="barre bas" style="left:${(50 - largeur).toFixed(1)}%;width:${largeur}%"></div><div class="valeur" style="right:calc(50% + ${largeur}% + 8px)">${signe(l.contribution)}</div>`;
    return `<div class="facteur"><div class="nom">${echapper(l.question)}&nbsp;: <em>${echapper(l.question === "Pays" ? l.reponse : l.reponse.toLowerCase())}</em></div><div class="axe">${barre}</div></div>`;
  }).join("");
}

function points(lignes) {
  const moyenne = etat.ref.taux_global;
  const maximum = Math.max(...lignes.map((l) => l.probabilite), moyenne) * 1.25;
  const position = (valeur) => (valeur / maximum * 100).toFixed(1);
  return lignes.map((l) => `<div class="point-ligne">
      <div class="nom ${l.saisi ? "saisi" : ""}">${echapper(l.nom)}${l.emploi_absent ? " *" : ""}</div>
      <div class="rail"><div class="reperes" style="left:${position(moyenne)}%" title="moyenne ${pourcent(moyenne)}"></div>
        <div class="rond ${l.saisi ? "saisi" : ""}" style="left:${position(l.probabilite)}%"></div></div>
      <div class="chiffre ${l.saisi ? "saisi" : ""}">${pourcent(l.probabilite)}</div>
    </div>`).join("");
}

function afficherComplet(resultat) {
  const r = etat.complet;
  const encarts = [];
  if (resultat.alertes.tanzanie) {
    encarts.push(`<div class="encart">Le modèle a appris sur des données de Tanzanie corrigées <strong>en supposant vraie notre hypothèse</strong>
      d'inversion des libellés de lieu et de statut marital. Le portrait saisi, lui, n'est pas modifié.</div>`);
  }
  if (resultat.alertes.emploi_absent) {
    encarts.push(`<div class="encart attention">Personne ${echapper(mot("country", r.country))} n'a déclaré vivre
      «&nbsp;${echapper(mot("job_type", r.job_type))}&nbsp;» dans l'enquête&nbsp;: l'estimation s'appuie sur les autres pays.</div>`);
  }
  document.getElementById("encarts").innerHTML = encarts.join("");

  document.getElementById("proba").textContent = pourcent(resultat.probabilite);
  document.getElementById("phrase-proba").textContent = phraseProbabilite(resultat.probabilite);
  const graphique = document.getElementById("echelle");
  graphique.innerHTML = echelle(resultat.probabilite);
  graphique.setAttribute("aria-label", `Ce portrait : ${pourcent(resultat.probabilite)}. Moyenne : ${pourcent(etat.ref.taux_global)}.`);

  const v = resultat.voisins;
  document.getElementById("texte-voisins").innerHTML = `Parmi les ${v.k} personnes de l'enquête qui ressemblent le plus à ce portrait,
    <strong>${pourcent(v.taux)}</strong> ont un compte. En ne gardant que les personnes interrogées ${echapper(mot("country", r.country))},
    la part est de <strong>${pourcent(v.taux_meme_pays)}</strong>. Ce sont des taux réellement observés, pas des estimations.`;

  document.getElementById("facteurs").innerHTML = facteurs(resultat.facteurs);
  document.getElementById("pays").innerHTML = points(resultat.pays);
  document.getElementById("genres").innerHTML = points(resultat.genres);
  const absent = resultat.pays.some((p) => p.emploi_absent);
  document.getElementById("note-pays").innerHTML = (absent
    ? `* Aucune personne de ce pays ne déclare vivre «&nbsp;${echapper(mot("job_type", r.job_type))}&nbsp;» dans l'enquête. ` : "")
    + "Le pointillé marque la moyenne de l'échantillon. Le pays se confond avec l'année de l'enquête et la façon de coder l'emploi&nbsp;: "
    + "l'écart montre la réaction du modèle, pas l'effet d'un déménagement.";
}

function afficherCourt(probabilite) {
  document.getElementById("proba-court").textContent = pourcent(probabilite);
  document.getElementById("proba-complet-rappel").textContent = etat.dernierComplet === null ? "–" : pourcent(etat.dernierComplet);
  const differentes = etat.ref.variables_courtes.filter((v) => etat.court[v] !== etat.complet[v]).map((v) => etat.ref.questions[v].toLowerCase());
  document.getElementById("note-court").textContent = differentes.length
    ? `Les deux portraits ne répondent pas pareil sur : ${differentes.join(", ")}. La comparaison n'est juste que si les réponses communes sont identiques.`
    : "Les réponses communes sont identiques : l'écart vient seulement des questions retirées.";
}

function afficherErreur(id, erreur) {
  document.getElementById(id).innerHTML = `<div class="erreur">${echapper(erreur.message)}</div>`;
}

async function estimerComplet() {
  const article = document.getElementById("article");
  article.classList.add("chargement");
  try {
    const resultat = await appeler("/api/estimer", etat.complet);
    etat.dernierComplet = resultat.probabilite;
    afficherComplet(resultat);
  } catch (erreur) {
    afficherErreur("encarts", erreur);
  } finally {
    article.classList.remove("chargement");
  }
}

async function estimerCourt() {
  try {
    const { probabilite } = await appeler("/api/estimer_court", etat.court);
    afficherCourt(probabilite);
  } catch (erreur) {
    afficherErreur("note-court", erreur);
  }
}

function brancherModes() {
  const boutons = document.querySelectorAll(".modes button");
  boutons.forEach((bouton) => bouton.addEventListener("click", () => {
    boutons.forEach((b) => b.setAttribute("aria-selected", b === bouton));
    document.querySelectorAll(".mode").forEach((m) => { m.hidden = m.id !== `mode-${bouton.dataset.mode}`; });
    if (bouton.dataset.mode === "court") {
      document.querySelectorAll("#phrase-court select").forEach(ajusterLargeur);
      estimerCourt();
    }
  }));
}

async function demarrer() {
  try {
    await reveiller();
    etat.ref = await appeler("/api/referentiel");
  } catch (erreur) {
    document.querySelector("main").innerHTML = `<div class="erreur">Impossible de joindre l'API : ${echapper(erreur.message)}</div>`;
    return;
  }
  const { ref } = etat;
  document.getElementById("taux-global").textContent = pourcent(ref.taux_global);
  document.getElementById("lignes").textContent = ref.lignes.toLocaleString("fr-FR");
  if (ref.provisoires.length) {
    const bandeau = document.getElementById("provisoire");
    bandeau.textContent = `Version de démonstration : les résultats du ${ref.provisoires.join(", du ")} sont provisoires. `
      + "Ce sont de simples taux observés par groupe, en attendant les vrais modèles.";
    bandeau.hidden = false;
  }

  construirePhrase(document.getElementById("phrase-complet"), PHRASE_COMPLETE, etat.complet, () => plusTard("complet", estimerComplet));
  const total = Object.keys(ref.questions).length;
  document.getElementById("consigne-court").textContent =
    `${ref.variables_courtes.length} questions au lieu de ${total}. Cliquez sur les mots soulignés pour changer le portrait.`;
  construirePhrase(document.getElementById("phrase-court"), ref.variables_courtes.map((v) => MINI_PHRASES[v]).join(" "),
    etat.court, () => plusTard("court", estimerCourt));
  brancherModes();
  estimerComplet();
}

demarrer();
