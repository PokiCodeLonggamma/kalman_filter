# EXP-D05.1 — Profil des actifs pour RE-1 hors crypto (note de cadrage, sans calcul)

*Demande du porteur du 2026-10-05 : profil théorique et cinématique des actifs idéaux pour RE-1, avant toute donnée
nouvelle. Aucun calcul nouveau : les chiffres viennent des expériences citées et de `RESEARCH_INSIGHTS.md`. Les seules
opérations faites sur ces chiffres (repère gaussien, §2 ; points morts, §4.1) sont signalées. Grille de lecture sans
seuil (PHILOSOPHY §3.1) : les ancres sont des valeurs mesurées, pas des critères. Le porteur choisit les candidats ; le
backtest de RE-1 gelée juge.*

*Addendum du 2026-10-05 : la mesure de la grille (`narratif_grille_D05_1.md`) corrige quatre points de cette note ;
voir §10.*

## 0. En bref

- **RE-1 ne suit pas une tendance : elle prend la cassure d'une compression courte et la tient 13 h.** Jambe de moins
  de 2,82 ATR, retracée d'au moins 50 %, vitesse du Kalman déjà retournée, barre de signal sans choc ; sortie après 26
  barres de 30 min.
- **Son avantage est une queue droite.** Environ 1 % des trades, deux grands gagnants par an, fait l'essentiel du
  résultat : des expansions de volatilité qui durent des heures, dans les deux sens. Le trade médian perd.
- **Le signal se transpose partout ; la rente non.** Sur les 13 séries hors crypto déjà testées (D01, D01.7), le
  déclencheur trouve la même population de signaux que sur BTC. Mais le brut va de −0,17 à +0,42 ATR (médiane +0,15),
  sans IC > 0, et les frais coûtent de 0,24 à 0,42 ATR sur les indices, l'argent et GBPJPY.
- **L'actif idéal pour RE-1 :**
  1. des expansions de 15 à 30 ATR de 30 min en 13 h, plusieurs fois par an et des deux côtés ;
  2. une cotation continue pendant ces 13 h, pour que le mouvement se déroule en barres et non en gap ;
  3. un coût aller-retour petit devant l'ATR de 30 min : BTC supporterait environ 18 bps, les indices 2 à 5 bps ;
  4. des stops exécutés près de leur niveau ;
  5. des expansions et des stops qui ne tombent pas les mêmes jours que ceux des cryptos.
- **US100 et GBPJPY ont déjà été testés** (D01.7, Saxo, 2020-2025) :
  - US100 : −0,10 ATR net, une année positive sur six ;
  - GBPJPY : brut nul, aucune année positive.
- **GLE n'a pas été testée.** Ses plus proches parents sont les ETF de séance (D01 bis à D01.7), dont le brut vient
  des gaps de nuit.

## 1. L'ADN mesuré des gains de RE-1

| Trait | Mesure | Source |
|---|---|---|
| Mécanique `[CODE]` | Signal à la clôture : jambe < 2,82 ATR, retracement ≥ 50 %, vitesse x1 retournée, `nis_z_100` ≤ P75 de BTC. Entrée à l'ouverture suivante, sortie 26 barres plus tard ; stop à l'extremum pour F3, stop catastrophe à 4 ATR pour tous. Taille : r % du capital par ATR14, plafonnée à 1x | livre blanc §1 |
| Profil `[OBS]` | BTC 2020-2025 : WR 44,3 %, PF 1,20, +0,369 ATR [+0,098 ; +0,645] (+12,3 bps), 15 trades par mois ; brut +0,50 ATR, frais 0,14 ATR (29 % du brut) | C02bis, D01.7 |
| Concentration `[OBS]` | BTC 2015-2025 : les 21 meilleurs trades (1 %) font 84 % de la somme nette en ATR ; sans eux, +0,035 ATR [−0,128 ; +0,199]. Trade médian : −0,43 ATR | K14 |
| Gagnants `[OBS]` | +196 à +961 bps en 13 h, ouverts à ATR bas (32 bps en moyenne, contre 57), sans stop touché, sur 10 années sur 11 ; soit environ 6 à 30 ATR(t) (ordre de grandeur, avec l'ATR moyen) | K14, I-M20 |
| Deux sens `[OBS]` | Trades contre la tendance aussi bons que les alignés (+0,39 à +0,43 ATR). Pires journées : chocs communs aux cryptos, à la hausse (2022-11-04) comme à la baisse (2025-11-06) | C04, D04.1 |
| Hors échantillon `[OBS]` | ETH +0,18 et XRP +0,26 ATR, même profil de queue ; un trade de nouvelle (XRP, 2023-07-13) fait 56 % de la somme de XRP | K17 |
| Époque `[OBS]` | BTC 2013-2019 : −0,045 ATR, brut +0,06. L'avantage dépend de l'époque du marché | K12, K13 |
| Exécution `[OBS]` | Une barre de retard ne coûte rien. 23 % des trades sortent sur stop : 0,5 ATR de glissement y coûte 0,115 ATR par trade, la moitié de l'espérance | K16 |
| Creux `[OBS]` | MDD du portefeuille des six : du 2023-07-13 au 2024-01-27 | D04.1 |

- `[HYP]` **RE-1 récolte des déséquilibres de flux qui se déroulent sur des heures** après un état calme : liquidations
  en cascade, couvertures forcées. C'est ce mécanisme qu'il faut chercher hors crypto, pas une classe d'actifs.
- `[HYP]` **Un « hiver » pour RE-1 est un marché sans expansion, pas un marché baissier :** RE-1 joue les deux sens.

**Le net d'un trade, en ATR, sert de fil à toute la note :**

net = B − C − F − G

- B : brut du signal, connu seulement par le backtest ;
- C : coût d'exécution, soit (écart + commission) / ATR14 de 30 min ;
- F : financement de nuit (swap) par trade ; absent de tous nos tests, cryptos comprises ;
- G : glissement des stops au-delà du niveau modélisé.

C et F se mesurent avant tout backtest, G en partie. Le « ratio vital » est B / (C + F + G) : le net est positif si et
seulement s'il dépasse 1.

## 2. Empreinte mathématique

**La bonne variable n'est pas le rendement de 30 min.** RE-1 place ses stops et sa taille en ATR14(t), puis tient 26
barres. Ce qui compte est z26 = (close[t+26] − open[t+1]) / ATR14(t) : le mouvement sur l'horizon du trade, en unités
du bruit récent.

**Repère analytique** (marche aléatoire gaussienne, volatilité constante, cotation continue) :
- l'ATR vaut environ 1,6 écart-type d'une barre ; z26 a donc un écart-type d'environ √26 / 1,6 ≈ 3,2 ATR ;
- un mouvement de 10 ATR en 13 h arrive alors environ une fois par an sur un actif coté 24 h sur 24, 7 jours sur 7 ;
- un mouvement de 15 ATR, une fois en plusieurs siècles.
- Les gagnants de RE-1 (environ 6 à 30 ATR) n'existent donc que par des expansions de volatilité.

### 2.1 Kurtosis : deux sources opposées

- **Les sauts** (une barre : gap, nouvelle) : RE-1 n'y entre pas, et les subit en position.
  - `[OBS]` Le veto `nis_z_100` écarte 64 à 74 % des signaux R2 nés d'un gap (K8).
  - `[OBS]` Les stops percés par un gap dépassent leur niveau de +0,7 à +2,6 ATR en moyenne (K8, D01.7).
- **Les expansions** (une volatilité qui se multiplie sur des heures après un calme) : c'est la queue que RE-1 récolte
  (K14).
- **Une forte kurtosis à 30 min peut donc signaler un mauvais actif (sauts) autant qu'un bon (expansions).**
  - Mesure : comparer la queue des rendements de 30 min à celle de z26.
  - Queue épaisse à 30 min et mince à 26 barres : actif à sauts. Queue épaisse à 26 barres : actif à expansions.
- **La kurtosis d'échantillon ne mesure rien ici.** Si l'indice de queue α est inférieur ou égal à 4, la kurtosis de la
  loi est infinie, et celle de l'échantillon croît avec sa taille.
  - `[HYP]` La littérature place α vers 3 pour la plupart des rendements financiers ; à vérifier sur nos séries
    (estimateur de Hill).
  - On lira donc des fréquences et des quantiles, pas des moments.

### 2.2 Épaisseur des queues

- Mesures :
  - fréquence par an de |z26| ≥ 5, 10, 15 et 20, dans chaque sens, sur fenêtres disjointes ;
  - facteur d'expansion ATR14(t + 26) / ATR14(t) ;
  - part des grands |z26| nés sous la médiane d'ATR de l'actif.
- Ancres : BTC et SOL, mesurés en même temps que les candidats ; repère gaussien ci-dessus.
- `[OBS]` À lire aussi en bps : classés en bps, les grands gains de BTC naissent à ATR haut (I-M20).

### 2.3 Asymétrie

- **La dérive ne fait pas de rente : elle joue des deux côtés** (K9).
  - `[OBS]` GER40 : Longs +0,77, Shorts −0,31 ATR en brut (dérive du DAX).
  - `[OBS]` Or : dérive de +0,38 ATR à H = 26.
- **Ce qui compte : des queues d'expansion des deux côtés.** Cryptos : krachs et rachats forcés, pires journées dans les
  deux sens.
  - `[HYP]` Indices d'actions : baisses rapides, souvent en gap ; hausses lentes.
  - `[HYP]` Change de portage : krach rare, du côté du portage.
- Mesures : quantiles hauts et bas de z26 (P0,1, P1, P99, P99,9) ; fréquence de |z26| ≥ 10 par sens ; dérive moyenne de
  z26. Pas de coefficient d'asymétrie : le 3e moment est instable si α est proche de 3.

## 3. Structure du marché

### 3.1 Range ou tendance

- `[OBS]` **Le déclencheur trouve partout la même population de compressions** (K7, K11). Sur les 13 séries hors
  crypto, `leg_atr` médian de 2,85 à 3,43 (BTC 2,82), P75 de `nis_z_100` de 1,03 à 1,46 (BTC 1,22). La fréquence des
  ranges ne distingue donc pas les actifs.
- **Ce qui les distingue est la suite : la cassure se prolonge-t-elle des heures ?** `[OBS]` GBPJPY : même géométrie,
  brut nul (K7 bis).
- Mesures (B est la part directionnelle du mouvement après le signal ; ces deux mesures en sont les témoins avant
  backtest) :
  - ratio de variance VR(q) = Var(r sur q barres) / (q · Var(r sur 1 barre)), q de 2 à 26 : au-dessus de 1, les
    mouvements se prolongent ; en dessous, ils reviennent ;
  - ratio d'efficacité sur 26 barres : |déplacement net| / somme des |déplacements| de chaque barre.
- `[HYP]` **RE-1 demande une alternance : calme, puis expansion directionnelle de quelques heures.**
  - Une tendance lente et régulière n'apporte que de la dérive (K9).
  - Un marché qui revient à la moyenne à l'heure n'apporte rien : change à 30 min, indices en séance (K10).

### 3.2 Persistance des chocs (« cygnes noirs »)

- `[CODE]` **RE-1 n'entre pas sur le choc.** Elle écarte la barre d'innovation forte et attend une jambe retracée d'au
  moins 50 %, vitesse retournée : elle prend la reprise après une pause.
- **Chocs utiles :** ceux qui se déroulent en continu sur des heures. `[HYP]` Cascades de liquidations crypto,
  débouclage de portage, choc d'offre pétrolier.
- **Chocs nuisibles :** ceux qui arrivent d'un bloc : gap de week-end, résultats d'une société, devise qui décroche.
  Pas d'entrée, et un stop percé si une position est ouverte.
- Mesures :
  - après chaque barre de choc (|r| ≥ k · ATR14), mouvement cumulé sur 26 barres dans le sens du choc : suite ou
    retour ;
  - part du mouvement de 26 barres faite en une seule barre ou en un gap.

### 3.3 Corrélation temporelle

- **Autocorrélation des rendements :** proche de 0 au pas d'une barre sur les marchés liquides. Seule compte sa somme
  jusqu'à 26 barres, que mesure VR.
- **Grappes de volatilité (autocorrélation de |r|) : nécessaires, présentes partout, mais une saisonnalité horaire
  forte les imite.**
  - `[HYP]` Sur un indice, l'ouverture de la séance au comptant multiplie la volatilité chaque jour à heure fixe.
    L'ATR14 (7 h) mesuré la nuit est petit : l'ouverture ressemble à une expansion, sans direction propre.
  - `[OBS]` GBPJPY : 53 % des signaux en session asiatique ; aucune session positive à 4 bps (D01.7).
  - Mesures : TR moyen par heure de la semaine (rapport max / min) ; part des signaux nés dans l'heure qui suit une
    ouverture.
- **Corrélation avec les cryptos :**
  - `[OBS]` L'or est le seul actif dont le retrait aggrave le portefeuille (pire journée −5,71 % au lieu de −5,20 %). Il
    a gagné +0,51 % le jour où quatre stops crypto sautaient (D04.1, D04.2).
  - `[HYP]` Pour la prop firm, un candidat vaut surtout par des expansions et des stops à d'autres dates que ceux des
    cryptos, et par des gains pendant les creux de RE-1.
  - Mesures : corrélation des |rendements| quotidiens avec le panier crypto ; jours à |z26| extrême communs ;
    comportement pendant le creux de 2023-07 à 2024-01.

## 4. Viabilité opérationnelle

### 4.1 Le ratio vital, déjà mesuré

| Actif (coût du test) | Brut B (ATR) | Frais C (ATR) | B / C | Point mort du coût (bps aller-retour) |
|---|---|---|---|---|
| SOL (5 bps) | +0,25 | 0,06 | 4,2 | ≈ 21 |
| BTC (5 bps) | +0,50 | 0,14 | 3,6 | ≈ 18 |
| US30 (4 bps) | +0,33 | 0,33 | 1,0 | ≈ 4,0 (écart médian chez Saxo : 1,4) |
| GER40 (4 bps) | +0,24 | 0,24 | 1,0 | ≈ 4,0 |
| Or (4 bps) | +0,24 | 0,26 | 0,9 | ≈ 3,7 |
| HK50 (8 bps) | +0,19 | 0,30 | 0,6 | ≈ 5,1 |
| US100 (4 bps) | +0,14 | 0,24 | 0,6 | ≈ 2,3 |
| GBPJPY (4 bps) | +0,10 | 0,40 | 0,2 | ≈ 1,0 |
| XAGUSD (11 bps) | +0,06 | 0,37 | 0,2 | ≈ 1,8 |
| EU50 (7 bps) | −0,17 | 0,42 | — | aucun |

- Sources : D01 (BTC, SOL, or ; 2020-2025) ; D01.7 (Saxo, 2020-2025, RE-1 avant le stop catastrophe ; le coût en ATR
  n'en dépend pas).
- Point mort du coût = B × coût du test / C : le coût aller-retour (écart, commission, glissement) qui annulerait le
  brut mesuré. Opération sur les chiffres publiés ; incertaine, car le brut a un IC d'environ ±0,3 ATR.
- `[OBS]` Dans ce tableau, seules les cryptos sont nettes positives, avec un rapport de 3,6 à 4,2 ; tous les autres
  actifs sont vers 1 ou en dessous.
- `[OBS]` Hors tableau, les ETF de séance USO, URA et GDX ont un rapport de 2,6 à 6,0. Mais leur brut vient des nuits,
  sur environ 140 trades chacun (K8 à K10) ; TLT et SMH ont un brut négatif.
- `[HYP]` Hors crypto, le levier est le coût réel chez la firme, pas le signal (K11). Première mesure utile de
  l'extracteur cTrader : écart par heure, commission et swap, contre ces points morts.

### 4.2 Les coûts que nos tests n'ont pas

- **Écart à l'heure réelle des entrées.** RE-1 entre et sort à toute heure. L'écart s'élargit au roulement quotidien,
  aux ouvertures et sur les nouvelles : il faut le mesurer aux heures des entrées, pas en médiane.
- **Financement de nuit (F).** Absent de tous nos tests, cryptos comprises.
  - Sur un marché 24/5, un trade de 13 h traverse le roulement quotidien environ une fois sur deux (13 h sur 24).
  - Le porteur a décrit le swap crypto de FTMO comme faible (décision du 2026-10-05). L'extracteur peut le relever,
    comme celui des candidats.
- **Glissement des stops (G).** Le moteur sort au niveau, ou à l'ouverture qui suit un gap. Sur un CFD, la reprise
  après un week-end peut être pire.

### 4.3 Continuité, séances et cadence

- `[CODE]` H et le verrou se comptent en barres de la série : 26 barres font 13 h sur un marché continu, et 1,5 séance
  sur une action de Paris (17 barres par jour).
- `[OBS]` En séance seule (ETF américains) :
  - 91 à 94 % des trades traversent une nuit (D01.7), et les gaps font 35 à 47 % de leur amplitude (K8) ;
  - le brut vient des nuits ; en séance seule, aucune valeur nette (K10).
- `[OBS]` La cadence suit le nombre de barres par mois : 15 trades par mois sur BTC (24/7), 6 à 10 sur les indices, le
  change et l'argent (24/5), environ 2 sur les ETF de séance (D01.7). Un actif de séance apporte peu de trades à un
  challenge.
- Sur un marché 24/5, un trade ouvert le vendredi après-midi traverse le week-end : les barres absentes ne comptent pas.

### 4.4 Taille, plafond et marge

- `[CODE]` Poids = min(1, r / ATR_bps). Sous 20 bps d'ATR (challenge de la piste 1) ou 25 bps (compte financé), la
  position est plafonnée à 1x et porte moins que r.
  - `[OBS]` GBPJPY : 98 % des trades plafonnés ; l'or presque toujours.
  - `[HYP]` Un actif calme pèse donc peu dans le compte, dans les deux sens : c'est le rôle d'amortisseur de l'or. Lever
    ce plafond serait un autre facteur, à tester seul.
- Marge : le moteur la plafonne avec le levier de chaque actif (`LEVIER_FTMO_SWING` : cryptos 1:2, or 1:30). Les
  leviers des autres classes sont à relever chez la firme.

### 4.5 Données

- **CFD adossés à des futures (pétrole, cuivre, gaz).** Chez Saxo, les séries continues changent de contrat au milieu
  d'une barre, sans ajustement ; elles ont été abandonnées en D01.7. Un rétro-ajustement par ratio est neutre pour le
  moteur (I-M17) : à faire roulement par roulement.
- **Fuseau et séances :** à vérifier par la structure des séries (I-M13). Actions : calendrier de la place, dividendes
  et opérations sur titres (I-M15).

## 5. Grille de lecture (sans seuil)

| Axe | Mesure, avant tout backtest | Ancre mesurée | Sens favorable à RE-1 | Lien au moteur |
|---|---|---|---|---|
| Coût | C = (écart aux heures des entrées + commission) / ATR14 ; médiane et P90 | SOL 0,06 ; BTC 0,14 ; or 0,26 ; indices 0,24 à 0,42 ; GBPJPY 0,40 | bas | net = B − C (K11) |
| Financement | swap par nuit, en ATR, × nuits traversées par trade | non mesuré, cryptos comprises | bas | coût hors modèle |
| Échelle | ATR14 de 30 min, en bps | BTC 34 à 80 selon l'année ; SOL 95 ; or 17 ; indices et argent 11 à 34 ; GBPJPY 10 à 11 | haut | C, plafond 1x |
| Queue d'expansion | fréquence par an de \|z26\| ≥ 5, 10, 15, 20, par sens | BTC et SOL, à mesurer ; repère gaussien : 10 ATR ≈ 1 fois par an, 15 ATR jamais | haute, des deux côtés | K14, K17 |
| Naissance au calme | ATR14(t+26) / ATR14(t) ; part des grands \|z26\| nés sous la médiane d'ATR | gagnants de BTC ouverts à 32 bps d'ATR, contre 57 | expansions fréquentes | K14, I-M20 |
| Sauts ou expansions | queue des rendements de 30 min contre queue de z26 ; part du mouvement faite en une barre ou un gap | ETF : gaps = 35 à 47 % de l'amplitude | expansions | K8, K16 |
| Persistance | VR(q), q = 2 à 26 ; ratio d'efficacité sur 26 barres | BTC, à mesurer | VR au-dessus de 1 | R2, K3 |
| Symétrie | dérive moyenne de z26 ; quantiles hauts contre bas | GER40 : Longs +0,77, Shorts −0,31 ; or : dérive +0,38 | queues des deux côtés | K9, C04 |
| Saisonnalité | TR moyen par heure de la semaine, rapport max / min ; signaux dans l'heure d'une ouverture | GBPJPY : 53 % des signaux en session asiatique | faible | ATR14 = 7 h |
| Continuité | heures cotées par semaine ; nuits et week-ends traversés par trade | ETF de séance : 91 à 94 % des trades traversent une nuit | continue | K8 à K10 |
| Gaps et stops | probabilité qu'un gap dépasse la distance du stop ; dépassement moyen | ETF : +0,7 à +2,6 ATR | faible | K16 |
| Indépendance | corrélation des \|r\| quotidiens avec le panier crypto ; jours d'expansion communs | or : seul retrait qui aggrave le portefeuille | faible | K18, livre blanc §2.2 |
| Plafond et marge | part des trades plafonnés à 1x pour r = 0,20 et 0,25 ; levier de la firme | GBPJPY : 98 % plafonnés | à lire | livre blanc §1.7 |

## 6. Lecture par classe, avant toute donnée nouvelle

- **Indices (CFD 24/5 : US100, US30, GER40…)**
  - `[OBS]` Brut de +0,14 (US100) à +0,33 ATR (US30) ; EU50 −0,17 ; frais de 0,24 à 0,42 ATR (D01.7). US30 à son écart
    médian chez Saxo : +0,211 ATR [−0,136 ; +0,556].
  - `[HYP]` Seule inconnue qui puisse changer la lecture : le coût réel chez la firme, face à des points morts de 2 à
    5 bps. Contre : baisses en gap, ouverture au comptant à heure fixe.
  - 2026 n'a jamais été lue sur ces actifs : c'est leur hors échantillon.
- **Change (GBPJPY…)**
  - `[OBS]` Brut nul (HistData −0,035, Saxo +0,095 ATR), ATR de 10 à 11 bps, aucune année positive à 4 bps.
  - `[HYP]` Pas de queue d'expansion à 30 min ; un coût plus bas ne crée pas de brut. Le retester revient à remesurer un
    brut connu.
- **Métaux**
  - `[OBS]` Or : brut +0,24 (2020-2025) et +0,30 ATR (2009-2019), absorbé par 0,26 ATR de frais ; amortisseur du
    portefeuille ; 2026 : +0,987 ATR. Argent : brut +0,06, frais 0,37 ATR à 11 bps.
- **Énergie (WTI, Brent, gaz naturel, en CFD continus)**
  - `[OBS]` Jamais testée en continu (séries brutes, D01.7). L'ETF USO, en séance : brut +0,22 ATR, net +0,148
    [−0,553 ; +0,813] sur 140 trades.
  - `[HYP]` Sur le papier, la classe la plus proche du profil : volatilité élevée (donc C bas), cotation 23 h sur 24,
    chocs d'offre qui se déroulent sur des heures dans les deux sens, moteurs étrangers aux cryptos.
  - `[HYP]` Contre : roulements à ajuster, statistiques de stocks publiées chaque semaine à heure fixe, swaps.
- **Actions (GLE…)**
  - `[OBS]` Aucune testée. Plus proches parents : les ETF de séance. Leur brut vient des nuits ; environ 2 trades par
    mois ; stops percés de +0,7 à +2,6 ATR.
  - `[HYP]` Une action ajoute ses propres sauts (résultats, notations) : une queue droite faite de nouvelles, non
    reproductible (cas de XRP, K17).
  - `[HYP]` Pour : un ATR élevé, donc un coût bas en ATR. Contre : 26 barres font 1,5 séance, donc au moins une nuit
    par trade.
- **Autres :** cuivre et US2000 (séries Saxo téléchargées en D01.7, jamais testées).

## 7. Ce que la grille demande à l'extracteur cTrader

- **Barres de 30 min de 2020-01 à aujourd'hui :** préchauffage, fenêtre des simulations de prop firm (2021-10 →
  2026-09), et 2026 lue à part.
- **Écarts, par heure de la semaine.** `[HYP]` Les barres de cTrader seraient construites sur le seul prix vendeur.
  L'écart demanderait alors les ticks acheteur et vendeur, au moins par échantillon. À vérifier dans la documentation de
  l'Open API.
- **Fiche de chaque symbole :** commission, swaps acheteur et vendeur, horaires de cotation, levier, taille de contrat,
  volume minimal. Pour les candidats et pour les six actifs actuels.
- **Roulements** des CFD adossés à des futures : leurs dates, pour le rétro-ajustement par ratio.
- **Volume :** volume de ticks seulement. RE-1 ne l'utilise pas ; il sert au contrôle de qualité.
- **Accès :** OAuth ; identifiants dans des variables d'environnement, jamais dans le chat ni dans le dépôt, comme pour
  Saxo (`src/marketdata/saxo.py`). Tests pytest pour le module.

## 8. Suite proposée (chaque étape après GO)

1. Le porteur valide la grille et arrête la liste des candidats.
2. Extracteur cTrader (Open API, OAuth configurée avec le porteur), avec ses tests.
3. Phase descriptive : la grille mesurée sur les candidats et sur BTC et SOL (ancres), sans RE-1. Le porteur retient
   les candidats.
4. RE-1 gelée sur les candidats retenus, aux coûts réels de la firme (écart, commission, swap) ; 8 métriques ; 2026 lue
   à part.
5. Entrée dans le moteur de prop firm (piste 1), en écart apparié contre le portefeuille des six.

## 9. Limites

- **Chiffres hors crypto :** D01 et D01.7, une source par actif (Saxo ou HistData), 2020-2025, RE-1 avant le stop
  catastrophe.
- **Biais de sélection :** les classes déjà lues (D01.7) le sont avec leur résultat. Choisir sur le coût et la
  structure, avant le P&L de RE-1, le limite sans l'annuler.
- **La référence crypto est elle-même haute :** l'histoire réelle se place entre les 78e et 96e centiles des histoires
  recomposées (D05.7).
- **Repère gaussien :** un ordre de grandeur, pas un modèle des données.

## 10. Addendum : ce que la mesure de la grille a corrigé (2026-10-05)

*Source : `narratif_grille_D05_1.md` (BTC, SOL, or, US100, US30, GER40, GBPJPY ; 2020-2025 ; sans RE-1 ni coût).*

- **VR au-dessus de 1 (§3.1, §5) n'est pas un marqueur des marchés de RE-1 :** VR(26) de 0,89 à 0,98 partout, BTC le
  plus bas.
- **« Un hiver de RE-1 est un marché sans expansion » (§1) n'est pas soutenu :** pendant le creux du portefeuille
  (2023-07 → 2024-01), BTC a eu 1,6 fois plus de fenêtres à 10 ATR ou plus qu'en moyenne.
- **« Change : pas de queue d'expansion à 30 min » (§6) est trop fort :** GBPJPY a une queue (19 fenêtres à 10 ATR ou
  plus pour 1 000, 11 fois le repère gaussien), la plus mince de l'échantillon.
- **La naissance au calme (§2.2, §5), telle que définie, ne distingue rien :** 77 à 81 % des grandes fenêtres naissent
  sous la médiane d'ATR, sur chaque série (effet de la division par ATR14(t), I-M20).
- **Nouveau point :** en ATR de 30 min, US100 et US30 ont une queue de 13 h aussi épaisse que BTC. Leur saison horaire,
  2,4 à 2,6 fois plus marquée, peut en expliquer une part : une mesure corrigée de la saison est proposée.
- **Correction horaire (2026-10-06) :** une fois la saison retirée, la queue de US100 et US30 perd deux tiers ; celle
  de BTC (35 ‰) vaut 2,1 à 2,7 fois celle de chaque candidat (13 à 17 ‰). Les expansions de 13 h hors heure fixe sont
  deux à trois fois plus rares sur les candidats que sur BTC.

