# State of VD — Sunnyside

Fork **pixel art** de *State of* (simulation institutionnelle vaudoise), rendu **Sunnyside World** (CC0).

**Jouer** : [https://ami2bal.github.io/stateofvd-sunnyside/](https://ami2bal.github.io/stateofvd-sunnyside/)

Fork conceptuel du projet principal (`state-of-vd`) :
- mêmes parcours / Mode Parcours / RBAC / fil d'Ariane
- DA : prefabs Sunnyside + signatures custom (TASK-117/119)
- plan de masse : `world.json` (9 sites Place du Château)

## Local

```bash
python serve.py 8771
```

→ http://127.0.0.1:8771/pixel/

## Structure

| Dossier | Rôle |
|---------|------|
| `pixel/` | Runtime + carte composée dual-LOD |
| `main/` | Modules métier (flows, inspector, flow-engine) |

## Crédits

- Sunnyside World V2.1 (CC0)
- Custom civic/UX (CC0-project, TASK-119)
- Layout & scénarios : State of VD
