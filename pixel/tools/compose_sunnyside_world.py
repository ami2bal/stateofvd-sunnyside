#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""compose_sunnyside_world.py — Assemblage dual-LOD Sunnyside v2 (no-stretch).

Règle d'or (TASK-117) : tamponner les prefabs Room1 à **taille native**
+ transposition de bande couleur. Ne JAMAIS étirer un prefab au footprint world
(le stretch v1 cassait toits/pignons).

Layout :
  - world.json (LECTURE SEULE) donne les **ancres** (centres d'emprise) ;
  - le bâtiment affiché = prefab natif centré sur l'ancre ;
  - allées 1 tuile de large depuis la porte S vers l'esplanade ;
  - terrain : herbe / eau / pierre calibrés sur le tileset.

Usage (depuis proto/state-of-vd-pixel) :
  python tools/compose_sunnyside_world.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PROTO = ROOT.parent
WORLD_PATH = PROTO / "state-of-vd" / "data" / "world.json"
PACK = (
    ROOT
    / "assets/packs/sunnyside/Sunnyside_World_ASSET_PACK_V2.1"
    / "Sunnyside_World_Assets/Tileset/spr_tileset_sunnysideworld_16px.png"
)
LIB_DIR = ROOT / "assets/sprite-library"
GT_PATH = LIB_DIR / "room1_ground_truth.json"
MAP_PATH = LIB_DIR / "mapping.json"
CUSTOM = LIB_DIR / "custom"
OUT = ROOT / "assets/composed"
HOTSPOTS_OUT = ROOT / "assets/hotspots.json"

T = 16
COLS = 64
SCALE = 2  # world 38×24 → map 76×48 (même grille que le runtime historique)
BANDS = {"blue": 8, "green": 16, "orange": 24, "red": 32, "purple": 40}

# Prefabs natifs (pas de scale) — gabarits prouvés Room1
PREFAB_FOR = {
    "parlement": "prefab_03_16x9",  # grand multi-corps
    "chateau": "prefab_02_9x13",  # vertical + tour
    "dept": "prefab_09_7x5",  # échoppe
}
PREFAB_FALLBACK = "prefab_05_9x6"

KIT_FOR_SITE = {
    "parlement": "green",
    "chateau": "red",
    "dep-dits": "blue",
    "dep-deiep": "orange",
    "dep-def": "purple",
    "dep-dsas": "blue",
    "dep-dcirh": "orange",
    "dep-djes": "purple",
    "dep-dfa": "blue",
}

def _ix(col: int, row: int) -> int:
    return row * COLS + col


# Tuiles terrain — indices library.json (family + role), PAS moyenne RGB
# (v1 stone=662/663 tombait sur du wood_deck → allées « rails croisés »)
TILE = {
    "grass": _ix(2, 1),  # terrain_grass_autotile fill
    "grass2": _ix(2, 2),  # variation
    "water": _ix(32, 6),  # water_fill
    "water2": _ix(32, 7),
    "stone": _ix(1, 15),  # floor_stone cobble_dark (allée / esplanade)
    "stone2": _ix(9, 15),  # floor_stone fill alt
    "wood_floor": _ix(9, 8),  # floor_wood_deck wood_plain
    "stone_floor": _ix(10, 15),  # floor_stone bureaux
}


def load_sheet() -> Image.Image:
    if not PACK.exists():
        raise SystemExit(f"Sunnyside tileset missing: {PACK}")
    return Image.open(PACK).convert("RGBA")


def tile_px(sheet: Image.Image, ix: int) -> Image.Image:
    if ix is None or ix < 0:
        return Image.new("RGBA", (T, T), (0, 0, 0, 0))
    col, row = ix % COLS, ix // COLS
    if not (0 <= col < COLS and 0 <= row < 64):
        return Image.new("RGBA", (T, T), (0, 0, 0, 0))
    return sheet.crop((col * T, row * T, col * T + T, row * T + T))


def is_empty(im: Image.Image) -> bool:
    return im.getchannel("A").getbbox() is None


def transpose_ix(ix: int, band_dst: int, sheet: Image.Image) -> int:
    """Transpose kit band (cols 15-35, rows 8-48) → band_dst."""
    if ix is None or ix < 0:
        return -1
    col, row = ix % COLS, ix // COLS
    if not (15 <= col <= 35 and 8 <= row < 48):
        return ix
    src_band = None
    for b in (8, 16, 24, 32, 40):
        if b <= row < b + 8:
            src_band = b
            break
    if src_band is None:
        return ix
    rel = row - src_band
    new_row = band_dst + rel
    if not (0 <= new_row < 64):
        return ix
    new_ix = new_row * COLS + col
    if is_empty(tile_px(sheet, new_ix)):
        return ix
    return new_ix


def detect_prefab_band(prefab: dict) -> int:
    counts = {b: 0 for b in (8, 16, 24, 32, 40)}
    for ix in prefab.get("base", {}).values():
        if not isinstance(ix, int) or ix < 0:
            continue
        row = ix // COLS
        for b in counts:
            if b <= row < b + 8:
                counts[b] += 1
                break
    return max(counts, key=counts.get) or 8


def stamp_prefab_native(
    canvas: Image.Image,
    sheet: Image.Image,
    prefab: dict,
    ox: int,
    oy: int,
    kit: str,
) -> tuple[int, int, int, int]:
    """Stamp prefab at native size. Returns (ox, oy, pw, ph) in map tiles."""
    pw, ph = prefab["size"]
    band_dst = BANDS.get(kit, 8)
    # paste every base + overlay cell
    for key, ix in prefab.get("base", {}).items():
        if not isinstance(ix, int) or ix < 0:
            continue
        try:
            mx, my = map(int, key.split(","))
        except ValueError:
            continue
        ix2 = transpose_ix(ix, band_dst, sheet)
        canvas.alpha_composite(tile_px(sheet, ix2), ((ox + mx) * T, (oy + my) * T))
    for key, ov in prefab.get("overlays", {}).items():
        try:
            mx, my = map(int, key.split(","))
        except ValueError:
            continue
        for oix in ov if isinstance(ov, list) else [ov]:
            if not isinstance(oix, int) or oix < 0:
                continue
            oix2 = transpose_ix(oix, band_dst, sheet)
            canvas.alpha_composite(
                tile_px(sheet, oix2), ((ox + mx) * T, (oy + my) * T)
            )
    return ox, oy, pw, ph


def fill_rect(canvas, sheet, ix, x0, y0, x1, y1, checker=None):
    for y in range(y0, y1):
        for x in range(x0, x1):
            t = ix
            if checker is not None and (x + y) % 2:
                t = checker
            canvas.alpha_composite(tile_px(sheet, t), (x * T, y * T))


def hline(canvas, sheet, ix, x0, x1, y):
    if y < 0:
        return
    for x in range(min(x0, x1), max(x0, x1) + 1):
        canvas.alpha_composite(tile_px(sheet, ix), (x * T, y * T))


def vline(canvas, sheet, ix, x, y0, y1):
    if x < 0:
        return
    for y in range(min(y0, y1), max(y0, y1) + 1):
        canvas.alpha_composite(tile_px(sheet, ix), (x * T, y * T))


def paste_custom(canvas: Image.Image, name: str, px: int, py: int, center=True) -> bool:
    for fam in ("dossier_props", "furniture_signature", "civic_symbols", "ux_icons"):
        p = CUSTOM / fam / name
        if not p.exists():
            continue
        im = Image.open(p).convert("RGBA")
        x, y = px, py
        if center:
            x -= im.width // 2
            y -= im.height // 2
        canvas.alpha_composite(im, (max(0, x), max(0, y)))
        return True
    return False


def main():
    world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
    gt = json.loads(GT_PATH.read_text(encoding="utf-8"))
    mapping = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    prefabs = {p["name"]: p for p in gt["prefabs"]}
    sheet = load_sheet()

    gw, gh = world["grid"]["w"], world["grid"]["h"]
    mw, mh = gw * SCALE, gh * SCALE
    W, H = mw * T, mh * T

    ground = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    roofs = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    interiors = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # --- Terrain ---
    fill_rect(ground, sheet, TILE["grass"], 0, 0, mw, mh, checker=TILE["grass2"])

    # Léman (sud)
    lake_y0 = mh - 5
    fill_rect(ground, sheet, TILE["water"], 0, lake_y0, mw, mh, checker=TILE["water2"])
    hline(ground, sheet, TILE["stone"], 0, mw - 1, lake_y0 - 1)  # quai

    # Jura (nord) — rangs d'arbres / buissons (région trees cols 48-63 rows 0-8)
    tree_ixs = []
    for r in range(0, 6):
        for c in range(50, 62):
            ix = r * COLS + c
            if not is_empty(tile_px(sheet, ix)):
                tree_ixs.append(ix)
    if not tree_ixs:
        tree_ixs = [TILE["grass"]]
    for x in range(1, mw - 1, 2):
        for y in range(0, 3):
            ix = tree_ixs[(x * 3 + y * 11) % len(tree_ixs)]
            ground.alpha_composite(tile_px(sheet, ix), (x * T, y * T))

    # Esplanade (bande E-W entre institutions et dépts)
    esp_y = 13 * SCALE  # ~26
    esp_h = 3
    fill_rect(
        ground,
        sheet,
        TILE["stone"],
        2,
        esp_y,
        mw - 2,
        esp_y + esp_h,
        checker=TILE["stone2"],
    )

    # Lavaux (est)
    for y in range(4, mh - 6, 2):
        paste_custom(ground, "vigne_lavaux.png", (mw - 2) * T, y * T, center=False)

    # --- Sites (prefabs natifs centrés sur l'emprise world) ---
    hotspots = []
    sites_meta = []
    building_rects = {}  # siteId -> (ox, oy, pw, ph)
    path_cells: set[tuple[int, int]] = set()
    doors_meta: dict[str, dict] = {}

    # Esplanade = réseau de base (BFS)
    for y in range(esp_y, esp_y + esp_h):
        for x in range(2, mw - 2):
            path_cells.add((x, y))

    def add_path_vline(x: int, y0: int, y1: int) -> None:
        for y in range(min(y0, y1), max(y0, y1) + 1):
            if 0 <= x < mw and 0 <= y < mh:
                path_cells.add((x, y))

    for site in world["sites"]:
        sid = site["id"]
        msite = (mapping.get("sites") or {}).get(sid) or {}
        kit = msite.get("kit_color") or KIT_FOR_SITE.get(sid, "blue")

        # ancre = centre de l'emprise world (échelle map)
        f_gx, f_gy = site["gx"] * SCALE, site["gy"] * SCALE
        f_fw, f_fh = site["fw"] * SCALE, site["fh"] * SCALE
        cx_tile = f_gx + f_fw // 2
        cy_tile = f_gy + f_fh // 2

        if sid.startswith("dep-"):
            pname = PREFAB_FOR["dept"]
        elif sid == "parlement":
            pname = PREFAB_FOR["parlement"]
        elif sid == "chateau":
            pname = PREFAB_FOR["chateau"]
        else:
            pname = PREFAB_FALLBACK
        prefab = prefabs.get(pname) or prefabs.get(PREFAB_FALLBACK)
        if not prefab:
            print("missing prefab", pname, file=sys.stderr)
            continue

        pw, ph = prefab["size"]
        ox = max(0, min(mw - pw, cx_tile - pw // 2))
        oy = max(0, min(mh - ph, cy_tile - ph // 2))
        # Institutions un peu plus au nord pour laisser l'esplanade
        if sid in ("parlement", "chateau"):
            oy = max(3, min(oy, esp_y - ph - 2))
        # Départements sous l'esplanade
        if sid.startswith("dep-"):
            oy = max(esp_y + esp_h + 2, min(oy, mh - ph - 3))

        # Roofs = vue fermée (prefab complet)
        stamp_prefab_native(roofs, sheet, prefab, ox, oy, kit)

        # Interiors = footprint natif + sol + signatures (pas le prefab étiré)
        floor_ix = TILE["wood_floor"] if not sid.startswith("dep-") else TILE["stone_floor"]
        fill_rect(
            interiors,
            sheet,
            floor_ix,
            ox + 1,
            oy + 1,
            ox + pw - 1,
            oy + ph - 1,
        )
        # anneau mur léger (1 tuile) en réutilisant une tuile kit
        wall_src = 6 * COLS + 30
        wall_ix = transpose_ix(wall_src, BANDS[kit], sheet)
        for x in range(ox, ox + pw):
            interiors.alpha_composite(tile_px(sheet, wall_ix), (x * T, oy * T))
            interiors.alpha_composite(
                tile_px(sheet, wall_ix), (x * T, (oy + ph - 1) * T)
            )
        for y in range(oy, oy + ph):
            interiors.alpha_composite(tile_px(sheet, wall_ix), (ox * T, y * T))
            interiors.alpha_composite(
                tile_px(sheet, wall_ix), ((ox + pw - 1) * T, y * T)
            )

        door_x = ox + pw // 2
        if sid.startswith("dep-"):
            # porte N (face esplanade)
            door_y = oy
            face = "N"
            apron = (door_x, door_y - 1)
            interiors.alpha_composite(
                tile_px(sheet, floor_ix), (door_x * T, door_y * T)
            )
            # Allée porte → bord sud esplanade
            target_y = esp_y + esp_h - 1
            vline(ground, sheet, TILE["stone"], door_x, target_y, door_y)
            add_path_vline(door_x, target_y, door_y)
        else:
            # porte S (face esplanade)
            door_y = oy + ph - 1
            face = "S"
            apron = (door_x, door_y + 1)
            interiors.alpha_composite(
                tile_px(sheet, floor_ix), (door_x * T, door_y * T)
            )
            if door_y < esp_y:
                vline(ground, sheet, TILE["stone"], door_x, door_y, esp_y)
                add_path_vline(door_x, door_y, esp_y)

        doors_meta[sid] = {
            "door": [door_x, door_y],
            "apron": [apron[0], apron[1]],
            "face": face,
            "kind": site.get("kind", "site"),
        }
        building_rects[sid] = (ox, oy, pw, ph)

        # Hotspot site = bbox prefab réelle
        hotspots.append(
            {
                "id": sid,
                "kind": "site",
                "siteId": sid,
                "siteKind": site.get("kind", "site"),
                "label": site.get("displayName") or sid,
                "cx": (ox + pw / 2) * T,
                "cy": (oy + ph / 2) * T,
                "w": pw * T,
                "h": ph * T,
            }
        )

        # Rooms : grille dans le footprint **natif**
        rooms = site.get("rooms") or []
        n = max(1, len(rooms))
        cols_r = min(3, n)
        rows_r = (n + cols_r - 1) // cols_r
        inner_w = max(1, pw - 2)
        inner_h = max(1, ph - 2)
        rw = max(2, inner_w // cols_r)
        rh = max(2, inner_h // rows_r)
        for i, room in enumerate(rooms):
            col = i % cols_r
            row = i // cols_r
            rx = ox + 1 + col * rw
            ry = oy + 1 + row * rh
            rid = room.get("id") or f"{sid}-r{i}"
            rcx = (rx + rw / 2) * T
            rcy = (ry + rh / 2) * T
            hotspots.append(
                {
                    "id": rid,
                    "kind": "room",
                    "siteId": sid,
                    "siteKind": site.get("kind", "site"),
                    "label": room.get("label") or rid,
                    "sub": site.get("displayName") or sid,
                    "cx": rcx,
                    "cy": rcy,
                    "w": rw * T,
                    "h": rh * T,
                }
            )
            # signatures custom (plan ouvert)
            if rid == "plenum-gc":
                paste_custom(interiors, "hemicycle_arc.png", int(rcx), int(rcy))
                paste_custom(
                    interiors, "tribune_president.png", int(rcx), int(rcy + 18)
                )
                paste_custom(interiors, "urne.png", int(rcx + 22), int(rcy + 14))
                paste_custom(
                    interiors, "tableau_vote.png", int(rcx), int(ry * T + 10)
                )
            elif rid == "college-ce":
                paste_custom(interiors, "table_college.png", int(rcx), int(rcy))
            elif rid == "chancellerie":
                paste_custom(interiors, "presse_fao.png", int(rcx), int(rcy))
            elif "projet" in rid:
                paste_custom(interiors, "dossier_empd.png", int(rcx), int(rcy))

        # Symboles civiques sur toits (vue fermée)
        if sid == "parlement":
            paste_custom(
                roofs, "drapeau_vd.png", ox * T + 10, oy * T - 2, center=False
            )
            paste_custom(
                roofs,
                "lanterne_verte.png",
                (ox + pw - 2) * T,
                oy * T,
                center=False,
            )
        if sid == "chateau":
            paste_custom(
                roofs, "drapeau_ch.png", ox * T + 8, oy * T - 2, center=False
            )

        sites_meta.append(
            {
                "id": sid,
                "kit": kit,
                "prefab": pname,
                "native": True,
                "ox": ox,
                "oy": oy,
                "pw": pw,
                "ph": ph,
                "footprint_world": {
                    "gx": f_gx,
                    "gy": f_gy,
                    "fw": f_fw,
                    "fh": f_fh,
                },
            }
        )

    # Esplanade : statue + blason
    paste_custom(
        ground,
        "statue_or.png",
        mw * T // 2,
        (esp_y + esp_h // 2) * T,
    )
    paste_custom(
        ground,
        "blason_vd.png",
        mw * T // 2 + 48,
        (esp_y + 1) * T,
    )
    # dossier « en circulation » sur l'esplanade
    paste_custom(
        interiors,
        "dossier_16.png",
        mw * T // 2 - 80,
        (esp_y + 1) * T,
    )

    OUT.mkdir(parents=True, exist_ok=True)
    ground.save(OUT / "ground.png")
    roofs.save(OUT / "roofs.png")
    interiors.save(OUT / "interiors.png")

    p_roofs = ground.copy()
    p_roofs.alpha_composite(roofs)
    p_roofs.save(OUT / "preview_sunnyside_roofs.png")
    p_int = ground.copy()
    p_int.alpha_composite(interiors)
    p_int.save(OUT / "preview_sunnyside_interiors.png")

    path_graph = {
        "tile": T,
        "grid": {"w": mw, "h": mh},
        "cells": sorted(path_cells),
        "doors": doors_meta,
        "compose": "sunnyside-v2-nostretch",
    }
    (OUT / "path_graph.json").write_text(
        json.dumps(path_graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    meta = {
        "tile": T,
        "width": W,
        "height": H,
        "grid": {"w": mw, "h": mh},
        "scale": SCALE,
        "source": "sunnyside-v2.1-nostretch",
        "compose": "v2-native-prefabs",
        "playbook": "sprite-library TASK-117/119 + compose v2 no-stretch",
        "packs": [
            "Sunnyside World V2.1 — CC0",
            "Custom UX signatures TASK-119 — CC0-project",
        ],
        "credit": (
            "Sunnyside World (CC0) + custom civic/UX (CC0-project). "
            "Prefabs stamped at native size (no stretch). Layout anchors from state-of-vd world.json."
        ),
        "da": {
            "goal": "Place du Chateau dual-LOD — prefabs native + signatures",
            "method": "no-stretch stamp + color transpose + cobble paths + path_graph",
            "kits": KIT_FOR_SITE,
            "tiles": {
                "grass": TILE["grass"],
                "stone_path": TILE["stone"],
                "water": TILE["water"],
            },
        },
        "layers": {
            "ground": "ground.png",
            "roofs": "roofs.png",
            "interiors": "interiors.png",
        },
        "hotspots": len(hotspots),
        "path_cells": len(path_cells),
        "sites": sites_meta,
    }
    (OUT / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    HOTSPOTS_OUT.write_text(
        json.dumps(
            {
                "alignedTo": "state-of-vd/data/world.json",
                "compose": "sunnyside-v2-nostretch",
                "scale": SCALE,
                "hotspots": hotspots,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    proof = LIB_DIR / "proofs"
    proof.mkdir(exist_ok=True)
    p_roofs.save(proof / "proof_118_sunnyside_roofs.png")
    p_int.save(proof / "proof_118_sunnyside_interiors.png")

    print(f"OK compose Sunnyside v2 no-stretch {mw}x{mh} → {W}x{H}")
    print(f"  buildings: {len(sites_meta)} native prefabs")
    for s in sites_meta:
        print(
            f"    {s['id']:12} kit={s['kit']:6} prefab={s['prefab']} "
            f"@({s['ox']},{s['oy']}) {s['pw']}x{s['ph']}"
        )
    print(f"  hotspots: {len(hotspots)}")
    print(f"  path_cells: {len(path_cells)} doors: {len(doors_meta)}")


if __name__ == "__main__":
    main()
