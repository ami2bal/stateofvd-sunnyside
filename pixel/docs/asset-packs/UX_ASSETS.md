# UX_ASSETS — assets custom UX / identité (TASK-119)

> **57 pièces originales** (CC0-project, palette Sunnyside) qui **complètent** le pack village là où il est muet : fil « dossier législatif », mobilier-signature institutionnel, symboles civiques vaudois, atlas HUD Mode Parcours.
> **Générateur** : `tools/build_custom_assets.py` (régénérable) → PNG sous `assets/sprite-library/custom/<famille>/` + `custom_entries.json` (fusionné dans `library.json` par `build_sprite_library.py`).
> **Preuves** : `assets/sprite-library/proofs/ux_1..5_*.png` · **planches** : `sheets/family_{dossier_props,furniture_signature,civic_symbols,ux_icons}.png`.
> **Gate** : `python tools/validate_sprite_library.py` → PASS (K8 couvre les customs).

## A — Fil conducteur « dossier législatif » (`dossier_props`, 13)

| id | taille | usage |
|---|---|---|
| `dossier_16` | 16×16 | prop sol/table — base du fil |
| `dossier_icon_24` / `_32` | 24 / 32 | icône HUD / step-card / pastille |
| `dossier_carry_overlay` | 96×64 | overlay aligné frame perso **CARRY** (le perso porte le dossier) |
| `dossier_{empd,empl,motion,postulat,petition,decret}` | 16×16 | 6 variantes type d'objet (onglet couleur + lettre) |
| `sceau` | 16×16 | étape adoption / promulgation |
| `plume` | 16×16 | étape collège CE / signature |
| `enveloppe` | 16×16 | pétitions / courriers / saisine tiers |

## B — Mobilier-signature institutionnel (`furniture_signature`, 6)

| id | taille | salle | usage |
|---|---|---|---|
| `hemicycle_arc` | 52×32 | `plenum-gc` | **bancs en arc du Grand Conseil** (cœur identité GC) |
| `tribune_president` | 16×16 | `plenum-gc` | perchoir / tribune du président |
| `tableau_vote` | 16×12 | `plenum-gc` | panneau résultats de votes (mural) |
| `urne` | 16×16 | `plenum-gc` | boîte de scrutin (branche rejet/adopt) |
| `table_college` | 12×8 | `college-ce` | table ovale du collège CE (7 places) |
| `presse_fao` | 16×16 | `chancellerie` | presse d'imprimerie FAO (publication) |

## C — Symboles civiques vaudois (`civic_symbols`, 6)

| id | taille | usage |
|---|---|---|
| `drapeau_vd` | 16×20 | drapeau Vaud (vert-blanc) — façades GC, esplanade |
| `drapeau_ch` | 16×20 | drapeau suisse (accent fédéral) |
| `blason_vd` | 16×16 | armoiries VD — chrome UI, esplanade, boot |
| `statue_or` | 16×22 | esplanade centrale — **statue grise + halo doré** (l'or plein reste réservé à la navette) |
| `lanterne_verte` | 12×16 | lanterne verte — signature façade parlement (DA) |
| `vigne_lavaux` | 16×16 | tuile rang de ceps — bande Est Lavaux |

## D — Atlas HUD Mode Parcours (`ux_icons`, 32)

- **Numéros** : `digits_0_9` (strip 0-9, cellule 10×14) — fil d'Ariane, pastilles.
- **Pastilles d'étape** : `badge_done` (✓ vert) · `badge_current` (or) · `badge_next` (contour) · `badge_branch` (losange orange).
- **Transport** : `tr_play` · `tr_pause` · `tr_stop` · `tr_speed_{slow,norm,fast}` (×0,6 / ×1 / ×1,6).
- **Issue de branche** : `issue_accept` (✓ vert) · `issue_reject` (✕ rouge).
- **Activités** (alignées `ACTIVITY_LABEL`) : `act_{instruction,transmission,decision,publication,coordination,controle,citoyen}`.
- **Flux RBAC** : `flow_perle_in` (vert) · `flow_perle_out` (orange) · `flow_arrowhead`.
- **Repères carte** : `selection_ring` (4 coins or) · `map_pin`.
- **Timer** : `timer_ring_{25,50,75,100}` (arcs de countdown).
- **Panneaux 9-slice teintés** : `panel_gc_green` · `panel_ce_gold` · `panel_neutral_blue` (coins 6 px).

## Conventions & intégration

- `source: "custom"`, `fine: true`, `license: "CC0-project"`, familles ci-dessus. Résolvent toutes dans `library.json` (2 148 entrées après fusion).
- **Rendu** : pixel natif, **zoom entier uniquement** (jamais d'étirement). Icônes HUD en screen-space ; props/mobilier en world-space (ancrage bas-centre).
- **Style** : teintes prélevées sur le tileset Sunnyside → cohérence palette maître. Ne pas mélanger avec Sprout dans un livrable publiable.

## Limites honnêtes (ce qui reste perfectible)

- `statue_or` et `presse_fao` sont des **silhouettes lisibles**, pas des pièces très détaillées — suffisantes pour la lecture, à polir si besoin DA.
- L'ancrage de `dossier_carry_overlay` sur le squelette d'animation Human est **approximatif** (posé au bas-centre du frame) — réglage fin = runtime (Grok, TASK-118).
- `hemicycle_arc` est dessiné à l'échelle ×4 interne pour un arc lisse ; bbox logique **13×8 tuiles** dans le footprint `plenum-gc`.
