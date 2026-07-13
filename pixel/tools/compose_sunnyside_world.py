#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""compose_sunnyside_world.py — Assemblage dual-LOD Sunnyside v3.

Règles d'or (TASK-117 / combinatorics.json) :
  1. Prefabs Room1 tamponnés à **taille native** (jamais d'étirement).
  2. Transposition kit (cols 15-35, bandes 8/16/24/32/40) ; slot vide → source.
  3. **Roofs** = prefabs EXTÉRIEURS (05/02/09…) ; **Interiors** = prefab_01
     meublé (vue ouverte DA) ou salles meublées pour les dépts.
  4. Clustering multi-prefab pour densifier GC/CE sans scale.
  5. Customs / meubles toujours en ratio 1:1 (NEAREST, jamais resize).
  6. Terrain + allées cobble + path_graph alignés.

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
SCALE = 2  # world 38×24 → map 76×48 (runtime historique)
BANDS = {"blue": 8, "green": 16, "orange": 24, "red": 32, "purple": 40}
KIT_C0, KIT_C1 = 15, 36  # colonnes kit (combinatorics)


def _ix(col: int, row: int) -> int:
    return row * COLS + col


# Indices library / combinatorics (pas de moyenne RGB hasardeuse)
TILE = {
    # Herbe : UNIQUEMENT fills verts (évite damier beige/vert des mauvais indices)
    "grass": _ix(2, 1),  # sun_c2r1 fill vert
    "grass2": _ix(2, 2),  # sun_c2r2 variation verte
    "grass3": _ix(1, 1),  # sun_c1r1 autre fill vert
    "flower": _ix(5, 2),  # fleur sur herbe (pas terre)
    "water": _ix(32, 6),
    "water2": _ix(32, 7),
    "water_edge_n": _ix(32, 5),
    "cobble": _ix(1, 15),  # floor_stone cobble_dark
    "cobble2": _ix(9, 15),
    "stone_plateau": _ix(10, 15),
    "wood": _ix(9, 8),
    "wood2": _ix(10, 8),
    "wall_kit_src": _ix(30, 8 + 6),
}

# Clusters roofs (extérieurs natifs) — offsets relatifs en tuiles
# GC densifié : corps principal + ailes + tour (pas de prefab_03 épars)
ROOF_CLUSTERS = {
    "parlement": [
        # (prefab_name, dx, dy) — repère haut-gauche du footprint
        ("prefab_05_9x6", 2, 3),  # corps principal
        ("prefab_05_9x6", 10, 3),  # aile E (juxtaposé)
        ("prefab_09_7x5", 4, 8),  # avant-corps / porche S
        ("prefab_07_4x9", 18, 1),  # tour / lanterne
        ("prefab_15_6x4", 0, 0),  # annexe N-O
    ],
    "chateau": [
        ("prefab_02_9x13", 6, 2),  # tour + multi-corps (identité CE)
        ("prefab_05_9x6", 0, 6),  # aile O
        ("prefab_09_7x5", 15, 8),  # aile E basse
    ],
}

# Dépts : petite maison extérieure (gabarit P5)
DEPT_ROOF = "prefab_09_7x5"
# Intérieur institution (vue ouverte DA — prefab_01 meublé)
INT_INSTITUTION = "prefab_01_14x11"

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
    a = im.getchannel("A")
    # getbbox None = entièrement transparent
    bb = a.getbbox()
    if bb is None:
        return True
    # quasi-vide
    hist = a.histogram()
    opaque = sum(hist[17:])
    return opaque < 6


def band_of(row: int) -> str | None:
    for name, r0 in BANDS.items():
        if r0 <= row < r0 + 8:
            return name
    return None


def transpose_ix(ix: int, dst_color: str, sheet: Image.Image) -> int:
    """Transposition kit + fallback si slot cible vide (preuves P3)."""
    if ix is None or ix < 0 or dst_color not in BANDS:
        return ix if ix is not None else -1
    col, row = ix % COLS, ix // COLS
    src = band_of(row)
    if not src or not (KIT_C0 <= col < KIT_C1) or src == dst_color:
        return ix
    r2 = row - BANDS[src] + BANDS[dst_color]
    if not (0 <= r2 < 64):
        return ix
    new_ix = r2 * COLS + col
    if is_empty(tile_px(sheet, new_ix)):
        return ix
    return new_ix


def stamp_prefab(
    canvas: Image.Image,
    sheet: Image.Image,
    prefab: dict,
    ox: int,
    oy: int,
    kit: str | None,
    mw: int,
    mh: int,
) -> tuple[int, int, int, int]:
    """Stamp native. Clip hors carte. Returns bbox tiles (ox,oy,pw,ph)."""
    pw, ph = prefab["size"]
    for key, ix in prefab.get("base", {}).items():
        if not isinstance(ix, int) or ix < 0:
            continue
        try:
            mx, my = map(int, key.split(","))
        except ValueError:
            continue
        tx, ty = ox + mx, oy + my
        if not (0 <= tx < mw and 0 <= ty < mh):
            continue
        ix2 = transpose_ix(ix, kit, sheet) if kit else ix
        canvas.alpha_composite(tile_px(sheet, ix2), (tx * T, ty * T))
    for key, ov in prefab.get("overlays", {}).items():
        try:
            mx, my = map(int, key.split(","))
        except ValueError:
            continue
        tx, ty = ox + mx, oy + my
        if not (0 <= tx < mw and 0 <= ty < mh):
            continue
        for oix in ov if isinstance(ov, list) else [ov]:
            if not isinstance(oix, int) or oix < 0:
                continue
            oix2 = transpose_ix(oix, kit, sheet) if kit else oix
            canvas.alpha_composite(tile_px(sheet, oix2), (tx * T, ty * T))
    return ox, oy, pw, ph


def fill_rect(canvas, sheet, ix, x0, y0, x1, y1, checker=None):
    for y in range(max(0, y0), y1):
        for x in range(max(0, x0), x1):
            t = checker if checker is not None and (x + y) % 2 else ix
            canvas.alpha_composite(tile_px(sheet, t), (x * T, y * T))


def put(canvas, sheet, ix, x, y, mw, mh):
    if 0 <= x < mw and 0 <= y < mh:
        canvas.alpha_composite(tile_px(sheet, ix), (x * T, y * T))


def hline(canvas, sheet, ix, x0, x1, y, mw, mh, checker=None):
    for x in range(min(x0, x1), max(x0, x1) + 1):
        t = checker if checker is not None and x % 2 else ix
        put(canvas, sheet, t, x, y, mw, mh)


def vline(canvas, sheet, ix, x, y0, y1, mw, mh, checker=None):
    for y in range(min(y0, y1), max(y0, y1) + 1):
        t = checker if checker is not None and y % 2 else ix
        put(canvas, sheet, t, x, y, mw, mh)


def paste_custom(
    canvas: Image.Image,
    name: str,
    px: int,
    py: int,
    center: bool = True,
    scale: int = 1,
) -> bool:
    """Paste custom PNG at integer scale (1 or 2 only) — never fractional."""
    if scale not in (1, 2):
        scale = 1
    for fam in ("dossier_props", "furniture_signature", "civic_symbols", "ux_icons"):
        p = CUSTOM / fam / name
        if not p.exists():
            continue
        im = Image.open(p).convert("RGBA")
        if scale == 2:
            im = im.resize((im.width * 2, im.height * 2), Image.NEAREST)
        x, y = px, py
        if center:
            x -= im.width // 2
            y -= im.height // 2
        # clip
        if x >= canvas.width or y >= canvas.height:
            return False
        canvas.alpha_composite(im, (max(0, x), max(0, y)))
        return True
    return False


def collect_tree_ixs(sheet: Image.Image) -> list[int]:
    out = []
    for r in range(0, 8):
        for c in range(48, 63):
            ix = r * COLS + c
            if not is_empty(tile_px(sheet, ix)):
                out.append(ix)
    return out or [TILE["grass"]]


def collect_furniture_ixs(sheet: Image.Image) -> list[int]:
    """Props meubles (région cols 36-47 rows 8-20 approx)."""
    out = []
    for r in range(8, 22):
        for c in range(36, 48):
            ix = r * COLS + c
            if not is_empty(tile_px(sheet, ix)):
                out.append(ix)
    return out


def stamp_dept_interior(
    interiors: Image.Image,
    sheet: Image.Image,
    ox: int,
    oy: int,
    pw: int,
    ph: int,
    kit: str,
    furn: list[int],
    mw: int,
    mh: int,
) -> None:
    """Petite salle meublée pour département (sols + murs kit + props, natif)."""
    # sol bois chaleureux (bureaux) — pas de prefab extérieur recyclé
    fill_rect(interiors, sheet, TILE["wood"], ox + 1, oy + 1, ox + pw - 1, oy + ph - 1, checker=TILE["wood2"])
    wall = transpose_ix(TILE["wall_kit_src"], kit, sheet)
    for x in range(ox, ox + pw):
        put(interiors, sheet, wall, x, oy, mw, mh)
        put(interiors, sheet, wall, x, oy + ph - 1, mw, mh)
    for y in range(oy, oy + ph):
        put(interiors, sheet, wall, ox, y, mw, mh)
        put(interiors, sheet, wall, ox + pw - 1, y, mw, mh)
    # porte N (trouée vers esplanade)
    put(interiors, sheet, TILE["wood"], ox + pw // 2, oy, mw, mh)
    # cloison légère 3 zones (cabinet | sg | projet)
    mid = ox + pw // 2
    for y in range(oy + 1, oy + ph - 1):
        if y != oy + ph // 2:
            put(interiors, sheet, wall, mid, y, mw, mh)
    # props
    if furn:
        spots = [
            (ox + 2, oy + 2),
            (ox + 2, oy + ph - 3),
            (ox + pw - 3, oy + 2),
            (ox + pw - 3, oy + ph - 3),
            (ox + pw // 2, oy + ph // 2),
        ]
        for i, (sx, sy) in enumerate(spots):
            put(interiors, sheet, furn[(i * 11) % len(furn)], sx, sy, mw, mh)


def main() -> None:
    world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
    gt = json.loads(GT_PATH.read_text(encoding="utf-8"))
    mapping = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    prefabs = {p["name"]: p for p in gt["prefabs"]}
    sheet = load_sheet()
    trees = collect_tree_ixs(sheet)
    furn = collect_furniture_ixs(sheet)

    gw, gh = world["grid"]["w"], world["grid"]["h"]
    mw, mh = gw * SCALE, gh * SCALE
    W, H = mw * T, mh * T

    ground = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    roofs = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    interiors = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # ---------- Terrain ----------
    # Base herbe unie (pas de damier violent) + rare variation
    fill_rect(ground, sheet, TILE["grass"], 0, 0, mw, mh)
    for y in range(0, mh):
        for x in range(0, mw):
            h = (x * 17 + y * 31) % 11
            if h == 0:
                put(ground, sheet, TILE["grass2"], x, y, mw, mh)
            elif h == 1:
                put(ground, sheet, TILE["grass3"], x, y, mw, mh)

    # Jura (nord) — bande dense arbres
    for x in range(0, mw):
        for y in range(0, 4):
            if (x + y * 3) % 2 == 0:
                put(ground, sheet, trees[(x * 7 + y * 13) % len(trees)], x, y, mw, mh)
            elif (x * y) % 7 == 0:
                put(ground, sheet, TILE["flower"], x, y, mw, mh)

    # Léman (sud) + quai
    lake_y0 = mh - 5
    fill_rect(
        ground, sheet, TILE["water"], 0, lake_y0, mw, mh, checker=TILE["water2"]
    )
    hline(ground, sheet, TILE["cobble"], 0, mw - 1, lake_y0 - 1, mw, mh, TILE["cobble2"])
    hline(ground, sheet, TILE["cobble2"], 0, mw - 1, lake_y0 - 2, mw, mh)

    # Esplanade pavée 3 tuiles (place)
    esp_y = 14 * SCALE  # 28
    esp_h = 3
    fill_rect(
        ground,
        sheet,
        TILE["cobble"],
        1,
        esp_y,
        mw - 1,
        esp_y + esp_h,
        checker=TILE["cobble2"],
    )
    # bordure plateau
    hline(ground, sheet, TILE["stone_plateau"], 1, mw - 2, esp_y - 1, mw, mh)
    hline(
        ground,
        sheet,
        TILE["stone_plateau"],
        1,
        mw - 2,
        esp_y + esp_h,
        mw,
        mh,
    )

    # Lavaux (est) — rangée vignes custom 1:1 (2 colonnes)
    for y in range(6, mh - 7, 2):
        paste_custom(ground, "vigne_lavaux.png", (mw - 3) * T + 8, y * T, center=True)
        paste_custom(ground, "vigne_lavaux.png", (mw - 2) * T + 4, y * T + 8, center=True)

    # Fleurs le long des chemins futurs
    for x in range(3, mw - 3, 4):
        put(ground, sheet, TILE["flower"], x, esp_y - 2, mw, mh)
        put(ground, sheet, TILE["flower"], x + 1, esp_y + esp_h + 1, mw, mh)

    path_cells: set[tuple[int, int]] = set()
    doors_meta: dict[str, dict] = {}
    for y in range(esp_y, esp_y + esp_h):
        for x in range(1, mw - 1):
            path_cells.add((x, y))

    def add_path_line(x0, y0, x1, y1, thick=1):
        """Bresenham-ish ortho paths, 1 or 2 tiles wide."""
        if x0 == x1:
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for dx in range(thick):
                    xx = x0 + dx - thick // 2
                    put(
                        ground,
                        sheet,
                        TILE["cobble"] if (xx + y) % 2 == 0 else TILE["cobble2"],
                        xx,
                        y,
                        mw,
                        mh,
                    )
                    path_cells.add((xx, y))
        else:
            for x in range(min(x0, x1), max(x0, x1) + 1):
                for dy in range(thick):
                    yy = y0 + dy - thick // 2
                    put(
                        ground,
                        sheet,
                        TILE["cobble"] if (x + yy) % 2 == 0 else TILE["cobble2"],
                        x,
                        yy,
                        mw,
                        mh,
                    )
                    path_cells.add((x, yy))

    hotspots = []
    sites_meta = []
    site_bbox: dict[str, tuple[int, int, int, int]] = {}

    for site in world["sites"]:
        sid = site["id"]
        msite = (mapping.get("sites") or {}).get(sid) or {}
        kit = msite.get("kit_color") or KIT_FOR_SITE.get(sid, "blue")

        # Footprint world → map tiles
        fx = site["gx"] * SCALE
        fy = site["gy"] * SCALE
        fw = site["fw"] * SCALE
        fh = site["fh"] * SCALE

        # Clamp institutions au-dessus esplanade, dépts en-dessous
        if sid in ("parlement", "chateau"):
            # remonter si besoin
            if fy + fh > esp_y - 1:
                fy = max(4, esp_y - fh - 1)
        if sid.startswith("dep-"):
            fy = max(esp_y + esp_h + 1, min(fy, mh - 8))

        pieces_meta = []
        minx, miny = fx + fw, fy + fh
        maxx, maxy = fx, fy

        if sid in ROOF_CLUSTERS:
            # --- Roofs : cluster multi-prefab natif ---
            for pname, dx, dy in ROOF_CLUSTERS[sid]:
                pf = prefabs.get(pname)
                if not pf:
                    print("missing prefab", pname, file=sys.stderr)
                    continue
                ox = fx + dx
                oy = fy + dy
                # garder dans footprint élargi (±2)
                ox = max(0, min(mw - pf["size"][0], ox))
                oy = max(3, min(esp_y - pf["size"][1] - 1, oy))
                stamp_prefab(roofs, sheet, pf, ox, oy, kit, mw, mh)
                pieces_meta.append(
                    {"prefab": pname, "ox": ox, "oy": oy, "pw": pf["size"][0], "ph": pf["size"][1]}
                )
                minx = min(minx, ox)
                miny = min(miny, oy)
                maxx = max(maxx, ox + pf["size"][0])
                maxy = max(maxy, oy + pf["size"][1])

            # --- Interiors : prefab_01 meublé (vue ouverte) centré dans footprint ---
            ip = prefabs.get(INT_INSTITUTION)
            if ip:
                iw, ih = ip["size"]
                iox = max(0, min(mw - iw, fx + (fw - iw) // 2))
                ioy = max(3, min(esp_y - ih - 1, fy + (fh - ih) // 2))
                stamp_prefab(interiors, sheet, ip, iox, ioy, kit, mw, mh)
                pieces_meta.append(
                    {
                        "prefab": INT_INSTITUTION,
                        "layer": "interiors",
                        "ox": iox,
                        "oy": ioy,
                        "pw": iw,
                        "ph": ih,
                    }
                )
                # hotspot bbox = union roofs + interior
                minx = min(minx, iox)
                miny = min(miny, ioy)
                maxx = max(maxx, iox + iw)
                maxy = max(maxy, ioy + ih)
                # porte S de l'intérieur vers esplanade
                door_x = iox + iw // 2
                door_y = ioy + ih - 1
            else:
                door_x = (minx + maxx) // 2
                door_y = maxy - 1

            face = "S"
            apron = (door_x, door_y + 1)
            if door_y < esp_y:
                add_path_line(door_x, door_y, door_x, esp_y, thick=2)

            # signatures civic roofs (1:1)
            if sid == "parlement":
                paste_custom(
                    roofs,
                    "drapeau_vd.png",
                    minx * T + 12,
                    miny * T - 4,
                    center=False,
                )
                paste_custom(
                    roofs,
                    "lanterne_verte.png",
                    (maxx - 2) * T,
                    miny * T,
                    center=False,
                )
            if sid == "chateau":
                paste_custom(
                    roofs,
                    "drapeau_ch.png",
                    minx * T + 10,
                    miny * T - 4,
                    center=False,
                )

            # signatures salles sur interiors
            if sid == "parlement" and ip:
                cx = (iox + iw / 2) * T
                cy = (ioy + ih / 2) * T
                paste_custom(interiors, "hemicycle_arc.png", int(cx), int(cy + 8))
                paste_custom(
                    interiors, "tribune_president.png", int(cx), int(cy + 24)
                )
                paste_custom(interiors, "urne.png", int(cx + 28), int(cy + 20))
                paste_custom(
                    interiors, "tableau_vote.png", int(cx), int(ioy * T + 12)
                )
            if sid == "chateau" and ip:
                cx = (iox + iw / 2) * T
                cy = (ioy + ih / 2) * T
                paste_custom(interiors, "table_college.png", int(cx), int(cy))
                paste_custom(
                    interiors, "presse_fao.png", int(cx + 40), int(cy - 10)
                )

        else:
            # --- Départements : roof prefab_09 + intérieur meublé maison ---
            pf = prefabs.get(DEPT_ROOF) or prefabs.get("prefab_09_7x5")
            if not pf:
                continue
            pw, ph = pf["size"]
            ox = max(0, min(mw - pw, fx + (fw - pw) // 2))
            oy = max(esp_y + esp_h + 1, min(mh - ph - 3, fy + (fh - ph) // 2))
            stamp_prefab(roofs, sheet, pf, ox, oy, kit, mw, mh)
            stamp_dept_interior(
                interiors, sheet, ox, oy, pw, ph, kit, furn, mw, mh
            )
            minx, miny, maxx, maxy = ox, oy, ox + pw, oy + ph
            pieces_meta.append(
                {"prefab": DEPT_ROOF, "ox": ox, "oy": oy, "pw": pw, "ph": ph}
            )
            door_x = ox + pw // 2
            door_y = oy
            face = "N"
            apron = (door_x, door_y - 1)
            add_path_line(door_x, esp_y + esp_h - 1, door_x, door_y, thick=1)
            paste_custom(
                interiors,
                "dossier_empd.png",
                ((minx + maxx) * T) // 2,
                ((miny + maxy) * T) // 2,
            )

        bw = max(1, maxx - minx)
        bh = max(1, maxy - miny)
        site_bbox[sid] = (minx, miny, bw, bh)

        doors_meta[sid] = {
            "door": [door_x, door_y],
            "apron": [apron[0], apron[1]],
            "face": face,
            "kind": site.get("kind", "site"),
        }

        hotspots.append(
            {
                "id": sid,
                "kind": "site",
                "siteId": sid,
                "siteKind": site.get("kind", "site"),
                "label": site.get("displayName") or sid,
                "cx": (minx + bw / 2) * T,
                "cy": (miny + bh / 2) * T,
                "w": bw * T,
                "h": bh * T,
            }
        )

        # Rooms : grille dans bbox réelle
        rooms = site.get("rooms") or []
        n = max(1, len(rooms))
        cols_r = min(3, n) if n > 1 else 1
        rows_r = (n + cols_r - 1) // cols_r
        inner_w = max(2, bw - 2)
        inner_h = max(2, bh - 2)
        rw = max(2, inner_w // cols_r)
        rh = max(2, inner_h // rows_r)
        for i, room in enumerate(rooms):
            col = i % cols_r
            row = i // cols_r
            rx = minx + 1 + col * rw
            ry = miny + 1 + row * rh
            rid = room.get("id") or f"{sid}-r{i}"
            hotspots.append(
                {
                    "id": rid,
                    "kind": "room",
                    "siteId": sid,
                    "siteKind": site.get("kind", "site"),
                    "label": room.get("label") or rid,
                    "sub": site.get("displayName") or sid,
                    "cx": (rx + rw / 2) * T,
                    "cy": (ry + rh / 2) * T,
                    "w": rw * T,
                    "h": rh * T,
                }
            )

        sites_meta.append(
            {
                "id": sid,
                "kit": kit,
                "native": True,
                "ox": minx,
                "oy": miny,
                "pw": bw,
                "ph": bh,
                "pieces": pieces_meta,
                "footprint_world": {"gx": fx, "gy": fy, "fw": fw, "fh": fh},
            }
        )

    # Esplanade props (1:1)
    paste_custom(ground, "statue_or.png", mw * T // 2, (esp_y + esp_h // 2) * T)
    paste_custom(
        ground, "blason_vd.png", mw * T // 2 + 40, (esp_y + 1) * T
    )
    paste_custom(
        ground, "dossier_16.png", mw * T // 2 - 56, (esp_y + 1) * T
    )

    # Arbres d'appoint entre institutions et dépts (hors chemins)
    for x in range(2, mw - 2, 3):
        for y in (esp_y - 3, esp_y + esp_h + 2):
            if (x, y) not in path_cells and (x, y + 1) not in path_cells:
                put(ground, sheet, trees[(x + y) % len(trees)], x, y, mw, mh)

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
        "compose": "sunnyside-v3-dense-native",
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
        "source": "sunnyside-v3-dense-native",
        "compose": "v3-multi-prefab-dual-lod",
        "playbook": "combinatorics TASK-117 + customs TASK-119 + dual LOD roofs/interiors",
        "packs": [
            "Sunnyside World V2.1 — CC0",
            "Custom civic/UX signatures TASK-119 — CC0-project",
        ],
        "credit": (
            "Sunnyside World (CC0) + custom civic/UX (CC0-project). "
            "Native prefab stamp (no stretch). Roofs=exterior clusters ; "
            "Interiors=prefab_01 furnished. Color transpose with empty-slot fallback."
        ),
        "da": {
            "goal": "Place du Chateau dual-LOD dense, ratios natifs",
            "method": "multi-prefab cluster + interior prefab_01 + cobble paths + customs 1:1",
            "kits": KIT_FOR_SITE,
            "rules": [
                "never stretch prefabs",
                "kit transpose cols 15-35 only",
                "customs NEAREST integer scale only",
                "roofs exterior / interiors furnished",
            ],
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
                "compose": "sunnyside-v3-dense-native",
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

    print(f"OK compose Sunnyside v3 dense-native {mw}x{mh} -> {W}x{H}")
    print(f"  buildings: {len(sites_meta)}")
    for s in sites_meta:
        pcs = len(s.get("pieces") or [])
        print(
            f"    {s['id']:12} kit={s['kit']:6} bbox=({s['ox']},{s['oy']}) "
            f"{s['pw']}x{s['ph']} pieces={pcs}"
        )
    print(f"  hotspots: {len(hotspots)}  path_cells: {len(path_cells)}")


if __name__ == "__main__":
    main()
