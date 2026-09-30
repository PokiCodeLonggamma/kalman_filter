# EXP-D01.7 — Audit du dépôt GitHub axb0306/cme-futures-ohlc (source candidate des futures NQ, RTY, CL, HG)

- **Date :** 2026-10-01. **Objet :** décider si le dépôt https://github.com/axb0306/cme-futures-ohlc peut servir de source de données pour D01.7. Étape DATA / SECURITY / PROVENANCE seulement : aucun backtest, RE-1 inchangée.
- **Méthode :** inspection statique par l'API GitHub (compte authentifié du porteur, lecture seule).
  - Aucun clonage, aucune exécution de script du dépôt, aucune dépendance installée.
  - Lecture intégrale des 4 fichiers non-données ; inventaire des 463 entrées de l'arbre ; parcours des arbres des 27 commits.
  - Lecture des seuls premiers octets de deux fichiers de données commençant en 2025. **Aucune donnée de 2026 n'a été lue ni téléchargée** (réserve scellée).

## [SECURITY] — aucun problème critique

- **Contenu du dépôt :**
  - 408 CSV de données et 4 autres fichiers : `README.md`, `update_data.py` (300 lignes), `config.example.json`, `.gitignore` ;
  - aucun lien symbolique, fichier exécutable, sous-module, binaire, pickle ou joblib ; aucun `.gitattributes` ni Git LFS ;
  - aucun `.github/` (pas de GitHub Actions), aucun `requirements.txt`, `setup.py` ou hook d'installation ;
  - un seul fichier caché : `.gitignore`, qui exclut `config.json`, `.DS_Store` et `update.log`.
- **`update_data.py`, lu en entier :**
  - Imports : `requests`, `time`, `os`, `glob`, `re`, `subprocess`, `datetime`, `json`. Aucun `eval`, `exec`, `base64`, `pickle`, `marshal` ni code obfusqué.
  - Réseau : uniquement l'API TopstepX (`API_BASE`, par défaut `https://api.topstepx.com/api`), sur deux points d'accès : `Auth/loginKey` (identifiants lus dans `config.json`) et `History/retrieveBars`. Aucune autre URL, aucun envoi ailleurs, aucun téléchargement de code distant.
  - Secrets : il lit seulement son propre `config.json`, jamais l'environnement ni d'autres fichiers. `API_BASE` est paramétrable dans `config.json` : un fichier modifié pourrait envoyer les identifiants ailleurs, mais ce fichier appartient à l'utilisateur.
  - Système : `subprocess.run` limité à `git add -A`, `git commit -m …` et `git push`, dans le dossier du script. Pas de shell, pas de suppression (aucun `os.remove` ni `rmtree`), pas de modification de l'environnement. Les écritures se limitent à ajouter des lignes aux CSV du dépôt et à les renommer (`os.rename`).
  - Point d'attention, non malveillant : `git add -A` publierait tout fichier présent dans le dossier. Nous n'avons de toute façon aucune raison d'exécuter ce script (il exige des identifiants TopstepX et pousse vers le dépôt).
  - Données : il déduplique sur l'horodatage et écrit `volume = 0` si l'API n'en renvoie pas. Aucune transformation silencieuse des prix.
- **Verdict sécurité :** code bénin, lisible, conforme au README. Rien à exécuter de notre côté.

## [DATA] — structure vérifiée ; contenu 2026 non lu

- **Inventaire :** 51 symboles, 8 fichiers par symbole (tick, 1, 5, 15, 30 min, 1 h, 4 h, journalier), nommés `SYMBOL_TF_DEBUT_FIN.csv` ; 867,5 Mo.
- **Format :** `datetime,open,high,low,close,volume`, horodatage naïf en UTC, début de barre.
  - Vérifié sur les premières lignes de `NQ_1h` : première barre le 2025-03-21 17:00 ; dernière barre du vendredi à 20:00 UTC ; reprise du dimanche 2025-03-23 22:00 UTC, soit 18:00 heure de New York, l'ouverture de CME Globex.
  - Même contrôle sur `CL_1h` (reprise du 2025-06-01 à 22:00 UTC).
  - Prix et volumes plausibles pour un contrat du mois (NQ ≈ 19 900, 48 904 lots la première heure ; CL ≈ 61,1).
- **Dates** (noms de fichiers, écrits par le script depuis la première et la dernière barre ; convention vérifiée empiriquement sur les deux fichiers ci-dessus) :

| Actif | Fichiers | 30 min | 1 h et 4 h | Journalier | Taille du 30 min |
|---|---|---|---|---|---|
| NQ | 8 | 2026-01-20 → 2026-04-15 | 2025-03-21 → 2026-04-15 | 2025-03-24 → 2026-04-14 | 0,17 Mo |
| RTY | 8 | 2026-01-20 → 2026-04-15 | 2025-03-21 → 2026-04-15 | 2025-03-24 → 2026-04-14 | 0,15 Mo |
| CL | 8 | 2026-01-20 → 2026-04-15 | 2025-06-01 → 2026-04-15 | 2025-06-02 → 2026-04-14 | 0,14 Mo |
| HG | 8 | 2026-02-15 → 2026-04-15 | 2026-02-15 → 2026-04-15 | 2026-02-17 → 2026-04-14 | 0,10 Mo |

- **Nombre de barres, trous, doublons, incohérences OHLC, volumes :** non mesurés.
  - Les fichiers de 30 min sont entièrement en 2026, dans la réserve scellée. Ceux de 1 h à journalier y sont pour 27 à 33 % de leur durée (NQ, RTY, CL), et en totalité pour HG.
  - Les télécharger aurait exposé des données de 2026, alors que la couverture échoue déjà.
  - Estimation d'après la taille, à titre indicatif : environ 2 800 barres de 30 min pour NQ (≈ 60 séances × 46 barres).
- **Nature des séries :** contrats individuels, pas de série continue construite (voir [PROVENANCE]).

## [PROVENANCE] — TopstepX via ProjectX, contrats bruts, redistribution contraire aux conditions de la source

- **Origine déclarée et cohérente avec le code :** TopstepX, via l'API ProjectX Gateway (hôte `api.topstepx.com`, identifiants de contrats au format ProjectX `CON.F.US.<racine>.<échéance>`). Rien ne permet de le certifier indépendamment : aucune signature, aucune empreinte publiée.
- **Collecte :** un script nocturne sur un VPS de l'auteur ajoute les nouvelles barres, renomme les fichiers et pousse le dépôt. Dernière mise à jour : 2026-04-15 (27 commits, du 2026-03-21 au 2026-04-15) ; le flux semble arrêté depuis.
- **Assemblage des contrats :**
  - un seul contrat codé en dur par actif (NQ `ENQ.M26`, RTY `RTY.M26`, CL `CLE.K26`, HG `CPE.K26`), à changer à la main « when contracts roll » ;
  - `update_data.py` n'a été modifié que le 2026-03-21, et ces identifiants n'ont jamais changé depuis : aucun roulement pendant la vie du script ;
  - l'historique antérieur au 2026-03-21 (1 h depuis 2025-03-21, par exemple) vient d'une amorce **non publiée**, dont les contrats et la règle de roulement sont inconnus.
- **Ajustement des roulements :** aucun. Les barres sont brutes et mises bout à bout dans le même fichier ; un roulement laisserait l'écart entre échéances comme un faux gap.
- **Look-ahead :** l'absence d'ajustement n'en introduit pas, mais une date de roulement choisie à la main après coup en introduirait un, et elle n'est pas documentée.
- **Droits :**
  - le dépôt n'a aucune licence (tous droits réservés par défaut) ;
  - les conditions d'utilisation de ProjectX stipulent : « The Services are only for personal use » et « You agree not to sell, share, redistribute, or reproduce the ProjectX Materials » ;
  - la publication de ces données sur GitHub paraît donc contraire aux conditions de la source, et leur usage par un tiers n'est couvert par aucun droit.

## [COVERAGE] — 2020-2025 impossible

- **Période demandée : 01/01/2020 → 31/12/2025.**
  - **30 min :** aucune barre avant 2026-01-20 (NQ, RTY, CL) ou 2026-02-15 (HG). Couverture de 2020-2025 nulle, et tout le contenu est dans la réserve 2026.
  - **Meilleur cas, toutes résolutions confondues :** 1 h de NQ et RTY du 2025-03-21 au 2025-12-31 (9 mois sur 72) ; CL depuis 2025-06-01 (7 mois) ; HG rien avant 2026.
- **Historique Git :**
  - 27 commits sur une seule branche (`main`), sans tag ni release ;
  - sur les 9 877 versions de fichiers de l'historique, la date de début la plus ancienne est le 2025-03-21 ;
  - aucun fichier supprimé ou remplacé ne couvrait 2020-2024 ;
  - les 2 forks sont des copies identiques (même taille, même date de push).
- Aucune autre source n'a été mélangée.

## [DECISION]

**FAIL.** Raison principale : le dépôt ne couvre pas 2020-2025. Ses barres de 30 min commencent le 2026-01-20, dans la réserve scellée, et rien dans tout l'historique Git ne remonte avant le 2025-03-21.

Raisons secondaires, chacune suffisante à elle seule pour une source de recherche :
- redistribution contraire aux conditions de ProjectX, dépôt sans licence ;
- contrats bruts mis bout à bout à la main, amorce historique non publiée ;
- flux arrêté depuis le 2026-04-15.

La sécurité n'est pas en cause : code bénin, jamais exécuté.

Conformément à la règle de décision : aucun téléchargement de données, aucune exécution, aucun backtest. Les futures NQ, RTY, CL et HG restent bloqués ; bascule vers QuantConnect (ou autre accès décidé par le porteur).

Sources : [dépôt](https://github.com/axb0306/cme-futures-ohlc) · [API ProjectX Gateway](https://gateway.docs.projectx.com/) · [conditions d'utilisation de ProjectX](https://www.projectx.com/terms) · [accès API TopstepX](https://help.topstep.com/en/articles/11187768-topstepx-api-access)
