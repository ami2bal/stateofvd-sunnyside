# State of VD — Sunnyside (pixel)

Fork **conceptuel** du simulateur `state-of-vd` : **mêmes** parcours, menus, zoom LOD, hotspots, tour dossier.  
Décor : **Sunnyside World V2.1** (CC0) + signatures custom civic/UX (TASK-119).

## Live

https://ami2bal.github.io/stateofvd-sunnyside/

## Dual LOD

| Zoom | Couche | Contenu |
|---|---|---|
| Éloigné | `ground` + `roofs` | prefabs Room1 natifs (toits / façades) |
| Proche | `ground` + `interiors` | plan ouvert + meubles signature |

Crossfade runtime : `engine/tiled.js` → `applyLod`.

## Règle d'or compose (v2)

- Prefabs tamponnés à **taille native** (pas d'étirement au footprint world)
- Ancres = centres d'emprise `world.json` (scale ×2)
- Allées **1 tuile** cobble (`floor_stone`) porte ↔ esplanade
- Kits couleur : GC vert · CE rouge · dépts blue/orange/purple

## Lancer

```bash
python serve.py 8771
```

| URL | Rôle |
|---|---|
| http://127.0.0.1:8771/sunnyside/ | **URL propre** (alias) |
| http://127.0.0.1:8771/state-of-vd-pixel/ | alias historique (dossier) |
| http://127.0.0.1:8771/state-of-vd/ | jeu vectoriel main |

Le serveur monte la racine `proto/` pour l'iso fonctionnel (modules métier `state-of-vd/`).

### Rebuild carte

```bash
python tools/compose_sunnyside_world.py
```

Sorties : `assets/composed/{ground,roofs,interiors,meta,path_graph}.png|json` · `assets/hotspots.json`.

## Crédits

- Sunnyside World V2.1 (CC0)
- Custom civic/UX TASK-119 (CC0-project)
- Layout & scénarios : State of VD (`world.json`)
