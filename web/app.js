// Page de l'application : construit les formulaires depuis l'API et affiche les estimations.

const etat = { ref: null, complet: {}, court: {}, dernierComplet: null, minuteurs: {} };

const pourcent = (valeur) => `${Math.round(valeur * 100)} %`;
const signe = (valeur) => `${valeur > 0 ? "+" : valeur < 0 ? "−" : ""}${Math.abs(Math.round(valeur * 100))} %`;
const echapper = (texte) => String(texte).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const libelle = (valeur) => etat.ref.libelles[valeur] ?? valeur;

async function appeler(chemin, corps) {
  const reponse = await fetch(chemin, corps ? {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps),
  } : undefined);
  const donnees = await reponse.json();
  if (!reponse.ok) throw new Error(donnees.detail ?? "Erreur du serveur.");
  return donnees;
}

// Formulaires

function construireChamp(variable, reponses, quandChange) {
  const { questions, choix, numeriques } = etat.ref;
  const bloc = document.createElement("div");
  bloc.className = "champ";
  const id = `${variable}-${Math.random().toString(36).slice(2, 7)}`;

  if (variable in numeriques) {
    const [bas, haut] = numeriques[variable];
    if (variable === "age_of_respondent") {
      bloc.innerHTML = `<label for="${id}">${echapper(questions[variable])}</label>
        <div class="curseur"><input id="${id}" type="range" min="${bas}" max="${haut}" value="${reponses[variable]}"><output>${reponses[variable]} ans</output></div>`;
      const curseur = bloc.querySelector("input");
      curseur.addEventListener("input", () => {
        reponses[variable] = Number(curseur.value);
        bloc.querySelector("output").textContent = `${curseur.value} ans`;
        quandChange();
      });
    } else {
      bloc.innerHTML = `<label for="${id}">${echapper(questions[variable])}</label>
        <input id="${id}" type="number" min="${bas}" max="${haut}" value="${reponses[variable]}">`;
      const champ = bloc.querySelector("input");
      champ.addEventListener("input", () => {
        const valeur = Number(champ.value);
        if (Number.isInteger(valeur) && valeur >= bas && valeur <= haut) {
          reponses[variable] = valeur;
          quandChange();
        }
      });
    }
    return bloc;
  }

  const options = choix[variable];
  if (options.length === 2) {
    bloc.innerHTML = `<span class="titre" id="${id}">${echapper(questions[variable])}</span>
      <div class="segments" role="group" aria-labelledby="${id}">${options.map((o) =>
        `<button type="button" data-valeur="${echapper(o)}" aria-pressed="${o === reponses[variable]}">${echapper(libelle(o))}</button>`).join("")}</div>`;
    bloc.querySelectorAll("button").forEach((bouton) => bouton.addEventListener("click", () => {
      reponses[variable] = bouton.dataset.valeur;
      bloc.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", b === bouton));
      quandChange();
    }));
    return bloc;
  }

  bloc.innerHTML = `<label for="${id}">${echapper(questions[variable])}</label>
    <select id="${id}">${options.map((o) =>
      `<option value="${echapper(o)}" ${o === reponses[variable] ? "selected" : ""}>${echapper(libelle(o))}</option>`).join("")}</select>`;
  bloc.querySelector("select").addEventListener("change", (e) => {
    reponses[variable] = e.target.value;
    quandChange();
  });
  return bloc;
}

function construireFormulaire(selecteur, variables, reponses, quandChange) {
  const conteneur = document.querySelector(`${selecteur} .champs`);
  variables.forEach((v) => {
    reponses[v] = etat.ref.defauts[v];
    conteneur.appendChild(construireChamp(v, reponses, quandChange));
  });
}

// Attend une courte pause dans la saisie avant d'appeler l'API.
function plusTard(nom, action, delai = 180) {
  clearTimeout(etat.minuteurs[nom]);
  etat.minuteurs[nom] = setTimeout(action, delai);
}

// Affichage

function jauge(titre, valeur, legende) {
  return `<div class="jauge">
    <div class="titre">${echapper(titre)}</div>
    <div class="valeur">${pourcent(valeur)}</div>
    <div class="piste" role="img" aria-label="${pourcent(valeur)}, moyenne ${pourcent(etat.ref.taux_global)}">
      <div class="rempli" style="width:${(valeur * 100).toFixed(1)}%"></div>
      <div class="repere" style="left:${(etat.ref.taux_global * 100).toFixed(1)}%"></div>
    </div>
    <div class="legende">${legende}</div>
  </div>`;
}

function barres(lignes) {
  const maximum = Math.max(...lignes.map((l) => l.probabilite), 0.01);
  return lignes.map((l) => `<div class="ligne">
      <div class="nom ${l.saisi ? "saisi" : ""}">${echapper(l.nom)}${l.saisi ? " (saisi)" : ""}${l.emploi_absent ? " ⚠" : ""}</div>
      <div class="piste"><div class="barre ${l.saisi ? "saisi" : ""}" style="width:${(l.probabilite / maximum * 100).toFixed(1)}%"></div></div>
      <div class="chiffre">${pourcent(l.probabilite)}</div>
    </div>`).join("");
}

function facteurs(lignes) {
  const maximum = Math.max(...lignes.map((l) => Math.abs(l.contribution)), 0.01);
  return lignes.map((l) => {
    const largeur = (Math.abs(l.contribution) / maximum * 40).toFixed(1);
    const haut = l.contribution >= 0;
    const barre = haut
      ? `<div class="barre haut" style="width:${largeur}%"></div><div class="chiffre" style="left:calc(50% + ${largeur}% + 6px)">${signe(l.contribution)}</div>`
      : `<div class="barre bas" style="left:${(50 - largeur).toFixed(1)}%;width:${largeur}%"></div><div class="chiffre" style="right:calc(50% + ${largeur}% + 6px)">${signe(l.contribution)}</div>`;
    return `<div class="facteur"><div class="nom">${echapper(l.question)} <span>· ${echapper(l.reponse)}</span></div><div class="axe">${barre}</div></div>`;
  }).join("");
}

function afficherComplet(resultat) {
  const reponses = etat.complet;
  const alertes = [];
  if (resultat.alertes.tanzanie) {
    alertes.push(`<div class="alerte info">Le modèle a appris sur des données de Tanzanie corrigées <strong>en supposant vraie notre hypothèse</strong>
      d'inversion des libellés de lieu et de statut marital. Vos réponses ne sont pas modifiées.</div>`);
  }
  if (resultat.alertes.emploi_absent) {
    alertes.push(`<div class="alerte attention">Personne en ${echapper(libelle(reponses.country))} n'a déclaré
      « ${echapper(libelle(reponses.job_type))} » dans les données : l'estimation s'appuie sur d'autres pays.</div>`);
  }
  document.getElementById("alertes").innerHTML = alertes.join("");
  document.getElementById("carte-proba").innerHTML = jauge("Probabilité d'avoir un compte", resultat.probabilite,
    `Le trait noir marque la moyenne de l'échantillon (${pourcent(etat.ref.taux_global)}).`);
  document.getElementById("carte-voisins").innerHTML = jauge("Parmi les personnes similaires", resultat.voisins.taux,
    `${pourcent(resultat.voisins.taux_meme_pays)} dans le même pays · taux réel observé chez ${resultat.voisins.k} personnes proches.`);
  document.getElementById("facteurs").innerHTML = facteurs(resultat.facteurs);
  document.getElementById("pays").innerHTML = barres(resultat.pays);
  document.getElementById("genres").innerHTML = barres(resultat.genres);
}

function afficherCourt(probabilite) {
  document.getElementById("carte-court").innerHTML = jauge("Avec moins de questions", probabilite,
    `Moyenne de l'échantillon : ${pourcent(etat.ref.taux_global)}.`);
  const complet = etat.dernierComplet;
  document.getElementById("carte-complet-rappel").innerHTML = complet === null
    ? `<div class="jauge"><div class="titre">Avec le profil complet</div><p class="note">Remplissez d'abord l'onglet « Profil complet ».</p></div>`
    : jauge("Avec le profil complet", complet, "Profil saisi dans l'onglet « Profil complet ».");
  const differentes = etat.ref.variables_courtes.filter((v) => etat.court[v] !== etat.complet[v]).map((v) => etat.ref.questions[v]);
  document.getElementById("comparaison").textContent = differentes.length
    ? `Réponses différentes entre les deux onglets : ${differentes.join(", ")}. La comparaison n'est juste que si elles sont identiques.`
    : "Les réponses communes sont identiques : l'écart vient seulement des questions retirées.";
}

function afficherErreur(conteneur, erreur) {
  conteneur.innerHTML = `<div class="erreur">${echapper(erreur.message)}</div>`;
}

// Appels

async function estimerComplet() {
  const zone = document.getElementById("resultats");
  zone.classList.add("chargement");
  try {
    const resultat = await appeler("/api/estimer", etat.complet);
    etat.dernierComplet = resultat.probabilite;
    afficherComplet(resultat);
  } catch (erreur) {
    afficherErreur(document.getElementById("alertes"), erreur);
  } finally {
    zone.classList.remove("chargement");
  }
}

async function estimerCourt() {
  try {
    const { probabilite } = await appeler("/api/estimer_court", etat.court);
    afficherCourt(probabilite);
  } catch (erreur) {
    afficherErreur(document.getElementById("comparaison"), erreur);
  }
}

function brancherOnglets() {
  const boutons = document.querySelectorAll(".onglets button");
  boutons.forEach((bouton) => bouton.addEventListener("click", () => {
    boutons.forEach((b) => b.setAttribute("aria-selected", b === bouton));
    document.querySelectorAll(".vue").forEach((vue) => { vue.hidden = vue.id !== `vue-${bouton.dataset.onglet}`; });
    if (bouton.dataset.onglet === "court") estimerCourt();
  }));
}

async function demarrer() {
  try {
    etat.ref = await appeler("/api/referentiel");
  } catch (erreur) {
    afficherErreur(document.querySelector(".page"), new Error(`Impossible de joindre l'API : ${erreur.message}`));
    return;
  }
  const { ref } = etat;
  document.getElementById("taux-global").textContent = pourcent(ref.taux_global);
  document.getElementById("lignes").textContent = ref.lignes.toLocaleString("fr-FR");
  if (ref.provisoires.length) {
    const bandeau = document.getElementById("bandeau");
    bandeau.textContent = `🚧 Version de démonstration : résultats provisoires pour ${ref.provisoires.join(", ")}. `
      + "Ce sont de simples taux observés par groupe, en attendant les vrais modèles.";
    bandeau.hidden = false;
  }
  const nbQuestions = Object.keys(ref.questions).length;
  document.getElementById("titre-court").textContent = `${ref.variables_courtes.length} questions`;
  document.getElementById("sous-titre-court").textContent =
    `Une estimation plus rapide, avec ${nbQuestions - ref.variables_courtes.length} réponses en moins.`;

  construireFormulaire("#form-complet", Object.keys(ref.questions), etat.complet, () => plusTard("complet", estimerComplet));
  construireFormulaire("#form-court", ref.variables_courtes, etat.court, () => plusTard("court", estimerCourt));
  document.querySelectorAll("form").forEach((f) => f.addEventListener("submit", (e) => e.preventDefault()));
  brancherOnglets();
  estimerComplet();
}

demarrer();
