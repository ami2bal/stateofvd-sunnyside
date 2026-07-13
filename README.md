# State of VD — Sunnyside

Fork **pixel art** de *State of* (simulation institutionnelle vaudoise), rendu **Sunnyside World** (CC0).

**Jouer** : [https://ami2bal.github.io/stateofvd-sunnyside/](https://ami2bal.github.io/stateofvd-sunnyside/)

Compose **v2** : prefabs natifs (no-stretch) · chemins cobble · dual-LOD · path_graph BFS.

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
