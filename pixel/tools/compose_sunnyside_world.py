#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""compose_sunnyside_world.py — Assemblage carte dual-LOD Sunnyside (TASK-118).

Lit world.json (LECTURE SEULE), tamponne prefabs Room1 + transposition couleur,
pose customs TASK-119, émet ground/roofs/interiors PNG + meta + hotspots.

Usage (depuis proto/state-of-vd-pixel) :
  python tools/compose_sunnyside_world.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

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
SCALE = 2  # world 38×24 → 76×48
BANDS = {"blue": 8, "green": 16, "orange": 24, "red": 32, "purple": 40}

# Prefab templates by role (from room1_ground_truth)
PREFAB_FOR = {
    "parlement": "prefab_03_16x9",  # large multi-body
    "chateau": "prefab_02_9x13",
    "dept": "prefab_09_7x5",
}
# Fallback smaller if missing
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


def load_sheet() -> Image.Image:
    if not PACK.exists():
        raise SystemExit(f"Sunnyside tileset missing: {PACK}")
    return Image.open(PACK).convert("RGBA")


def tile_px(sheet: Image.Image, ix: int) -> Image.Image:
    if ix is None or ix < 0:
        return Image.new("RGBA", (T, T), (0, 0, 0, 0))
    col, row = ix % COLS, ix // COLS
    return sheet.crop((col * T, row * T, col * T + T, row * T + T))


def is_empty(im: Image.Image) -> bool:
    a = im.getchannel("A")
    return a.getbbox() is None


def transpose_ix(ix: int, band_src: int, band_dst: int, sheet: Image.Image) -> int:
    """Transpose kit band tiles; fallback source if target empty."""
    if ix is None or ix < 0:
        return -1
    col, row = ix % COLS, ix // COLS
    if not (15 <= col <= 35 and 8 <= row < 48):
        return ix
    # which source band is this row in?
    src_band = None
    for b in (8, 16, 24, 32, 40):
        if b <= row < b + 8:
            src_band = b
            break
    if src_band is None:
        return ix
    rel = row - src_band
    # map to destination band (relative to prefab's native band → target kit)
    # If prefab is in blue(8) and we want green(16): new_row = 16 + rel
    # General: new_row = band_dst + (row - band_src) but band_src should be prefab native
    new_row = band_dst + rel
    if not (0 <= new_row < 64):
        return ix
    new_ix = new_row * COLS + col
    if is_empty(tile_px(sheet, new_ix)):
        return ix
    return new_ix


def detect_prefab_band(prefab: dict) -> int:
    """Most common kit band in prefab base tiles."""
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


def stamp_prefab(
    canvas: Image.Image,
    sheet: Image.Image,
    prefab: dict,
    ox: int,
    oy: int,
    kit: str,
    scale_w: int,
    scale_h: int,
) -> None:
    """Stamp prefab at tile ox,oy (map coords), resized to scale_w × scale_h tiles."""
    pw, ph = prefab["size"]
    band_src = detect_prefab_band(prefab)
    band_dst = BANDS.get(kit, 8)

    def map_xy(lx: int, ly: int) -> tuple[int, int]:
        """Local prefab cell → stretched map cell."""
        # duplicate central columns/rows
        if pw <= 1:
            mx = 0
        elif scale_w <= pw:
            mx = min(lx, scale_w - 1)
        else:
            # map lx in [0,scale_w) to [0,pw)
            mx = int(lx * (pw - 1) / max(1, scale_w - 1))
        if ph <= 1:
            my = 0
        elif scale_h <= ph:
            my = min(ly, scale_h - 1)
        else:
            my = int(ly * (ph - 1) / max(1, scale_h - 1))
        return mx, my

    # Build stretched base from nearest prefab cell
    for ty in range(scale_h):
        for tx in range(scale_w):
            mx, my = map_xy(tx, ty)
            key = f"{mx},{my}"
            ix = prefab["base"].get(key, -1)
            if isinstance(ix, int) and ix >= 0:
                ix2 = transpose_ix(ix, band_src, band_dst, sheet)
                tile = tile_px(sheet, ix2)
                canvas.alpha_composite(tile, ((ox + tx) * T, (oy + ty) * T))
            # overlays
            ov = prefab.get("overlays", {}).get(key)
            if ov:
                for oix in ov if isinstance(ov, list) else [ov]:
                    if isinstance(oix, int) and oix >= 0:
                        oix2 = transpose_ix(oix, band_src, band_dst, sheet)
                        tile = tile_px(sheet, oix2)
                        canvas.alpha_composite(tile, ((ox + tx) * T, (oy + ty) * T))


def fill_rect(canvas: Image.Image, sheet: Image.Image, ix: int, x0, y0, x1, y1):
    tile = tile_px(sheet, ix)
    for y in range(y0, y1):
        for x in range(x0, x1):
            canvas.alpha_composite(tile, (x * T, y * T))


def paste_custom(canvas: Image.Image, name: str, px: int, py: int, center=True):
    # search families
    for fam in ("dossier_props", "furniture_signature", "civic_symbols", "ux_icons"):
        p = CUSTOM / fam / name
        if p.exists():
            im = Image.open(p).convert("RGBA")
            if center:
                px = px - im.width // 2
                py = py - im.height // 2
            canvas.alpha_composite(im, (max(0, px), max(0, py)))
            return True
    return False


def main():
    world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
    gt = json.loads(GT_PATH.read_text(encoding="utf-8"))
    mapping = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    prefabs = {p["name"]: p for p in gt["prefabs"]}
    sheet = load_sheet()

    gw, gh = world["grid"]["w"], world["grid"]["h"]  # 38×24
    mw, mh = gw * SCALE, gh * SCALE  # 76×48
    W, H = mw * T, mh * T

    ground = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    roofs = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    interiors = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # --- Terrain ---
    # Grass fill (sample green-ish tile from terrain band)
    grass_ix = 1 * COLS + 2  # approx grass
    # Better: scan first non-empty in rows 0-2
    for try_ix in range(0, 64 * 6):
        if not is_empty(tile_px(sheet, try_ix)):
            # prefer mid-green looking
            grass_ix = try_ix
            break
    # known-good from combinatorics: wood 9,8 / grass region cols 0-18 rows 0-8
    # coords from combinatorics / Sunnyside guide (col + row*64)
    grass_ix = 4 + 2 * COLS  # green fill
    water_ix = 32 + 3 * COLS  # water body
    path_ix = 10 + 15 * COLS  # stone_plateau-ish (floors row 15)
    sand_ix = 6 + 20 * COLS  # shore

    fill_rect(ground, sheet, grass_ix, 0, 0, mw, mh)

    # Lake south (bottom 4 tile rows of world * scale)
    lake_y0 = (gh - 4) * SCALE
    fill_rect(ground, sheet, water_ix, 0, lake_y0, mw, mh)
    # shore band
    for x in range(mw):
        for dy in range(2):
            y = lake_y0 - 1 - dy
            if 0 <= y < mh:
                ground.alpha_composite(tile_px(sheet, sand_ix), (x * T, y * T))

    # Jura trees north
    tree_candidates = []
    for r in range(0, 8):
        for c in range(48, 63):
            ix = r * COLS + c
            if not is_empty(tile_px(sheet, ix)):
                tree_candidates.append(ix)
    if not tree_candidates:
        tree_candidates = [grass_ix]
    for x in range(0, mw, 3):
        for y in range(0, 3):
            ix = tree_candidates[(x + y * 7) % len(tree_candidates)]
            ground.alpha_composite(tile_px(sheet, ix), (x * T, y * T))

    # Esplanade path (horizontal mid)
    # Between buildings (gy ~11-15 world) and depts (gy 16)
    path_y0 = 11 * SCALE
    path_y1 = 15 * SCALE
    fill_rect(ground, sheet, path_ix, 1, path_y0, mw - 1, path_y1)
    # vertical spurs to parlement / chateau entries
    fill_rect(ground, sheet, path_ix, 9 * SCALE, 8 * SCALE, 11 * SCALE, path_y1)
    fill_rect(ground, sheet, path_ix, 25 * SCALE, 8 * SCALE, 27 * SCALE, path_y1)
    # path along depts
    fill_rect(ground, sheet, path_ix, 1, 15 * SCALE, mw - 1, 16 * SCALE)

    # Lavaux vines east
    vigne = CUSTOM / "civic_symbols" / "vigne_lavaux.png"
    if vigne.exists():
        vim = Image.open(vigne).convert("RGBA")
        for y in range(4, mh - 6, 2):
            ground.alpha_composite(vim, ((mw - 2) * T, y * T))

    # --- Sites ---
    hotspots = []
    sites_meta = []

    def add_hs(h):
        hotspots.append(h)

    for site in world["sites"]:
        sid = site["id"]
        kit = KIT_FOR_SITE.get(sid, mapping.get("sites", {}).get(sid, {}).get("kit_color", "blue"))
        if isinstance(kit, dict):
            kit = kit.get("kit_color", "blue")
        # mapping sites structure
        msite = (mapping.get("sites") or {}).get(sid) or {}
        kit = msite.get("kit_color") or KIT_FOR_SITE.get(sid, "blue")

        gx, gy = site["gx"] * SCALE, site["gy"] * SCALE
        fw, fh = site["fw"] * SCALE, site["fh"] * SCALE

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

        # roofs = exterior stamp
        stamp_prefab(roofs, sheet, prefab, gx, gy, kit, fw, fh)

        # interiors: floor fill + light walls outline + customs
        floor_ix = 8 * COLS + 9  # wood-ish
        if sid.startswith("dep-"):
            floor_ix = 15 * COLS + 9  # stone-ish
        fill_rect(interiors, sheet, floor_ix, gx + 1, gy + 1, gx + fw - 1, gy + fh - 1)

        # wall ring (use plain wall tile approx)
        wall_ix = transpose_ix(6 * COLS + 30, 8, BANDS[kit], sheet)
        for x in range(gx, gx + fw):
            interiors.alpha_composite(tile_px(sheet, wall_ix), (x * T, gy * T))
            interiors.alpha_composite(tile_px(sheet, wall_ix), (x * T, (gy + fh - 1) * T))
        for y in range(gy, gy + fh):
            interiors.alpha_composite(tile_px(sheet, wall_ix), (gx * T, y * T))
            interiors.alpha_composite(tile_px(sheet, wall_ix), ((gx + fw - 1) * T, y * T))

        # door gap on south façade
        door_x = gx + fw // 2
        door_y = gy + fh - 1
        interiors.alpha_composite(tile_px(sheet, floor_ix), (door_x * T, door_y * T))

        # site hotspot (building)
        cx = (gx + fw / 2) * T
        cy = (gy + fh / 2) * T
        add_hs(
            {
                "id": sid,
                "kind": "site",
                "siteId": sid,
                "siteKind": site.get("kind", "site"),
                "label": site.get("displayName") or sid,
                "cx": cx,
                "cy": cy,
                "w": fw * T,
                "h": fh * T,
            }
        )

        # rooms as sub-hotspots (grid rooms if present, else synthetic)
        rooms = site.get("rooms") or []
        n = max(1, len(rooms))
        for i, room in enumerate(rooms):
            # distribute rooms in footprint
            col = i % max(1, min(3, n))
            row = i // max(1, min(3, n))
            rw = max(2, fw // min(3, n) - 0)
            rh = max(2, fh // max(1, (n + 2) // 3))
            rx = gx + 1 + col * rw
            ry = gy + 1 + row * rh
            rcx = (rx + rw / 2) * T
            rcy = (ry + rh / 2) * T
            rid = room.get("id") or f"{sid}-r{i}"
            add_hs(
                {
                    "id": rid,
                    "kind": "room",
                    "siteId": sid,
                    "siteKind": site.get("kind", "site"),
                    "label": room.get("label") or rid,
                    "sub": site.get("displayName") or sid,
                    "cx": rcx,
                    "cy": rcy,
                    "w": max(rw, 2) * T,
                    "h": max(rh, 2) * T,
                }
            )
            # room floor tint
            fill_rect(
                interiors,
                sheet,
                floor_ix,
                rx,
                ry,
                min(rx + max(rw - 1, 1), gx + fw - 1),
                min(ry + max(rh - 1, 1), gy + fh - 1),
            )

            # signatures
            if rid == "plenum-gc":
                paste_custom(
                    interiors,
                    "hemicycle_arc.png",
                    int(rcx),
                    int(rcy),
                )
                paste_custom(
                    interiors,
                    "tribune_president.png",
                    int(rcx),
                    int(rcy + 20),
                )
                paste_custom(
                    interiors,
                    "tableau_vote.png",
                    int(rcx),
                    int(ry * T + 8),
                )
                paste_custom(
                    interiors,
                    "urne.png",
                    int(rcx + 24),
                    int(rcy + 16),
                )
            elif rid == "college-ce":
                paste_custom(interiors, "table_college.png", int(rcx), int(rcy))
            elif rid == "chancellerie":
                paste_custom(interiors, "presse_fao.png", int(rcx), int(rcy))
            elif "projet" in rid or room.get("role") == "projet":
                paste_custom(interiors, "dossier_empd.png", int(rcx), int(rcy))

        # civic on roofs / ground near site
        if sid == "parlement":
            paste_custom(roofs, "drapeau_vd.png", int(gx * T + 8), int(gy * T - 4), center=False)
            paste_custom(roofs, "lanterne_verte.png", int((gx + fw - 2) * T), int(gy * T), center=False)
        if sid == "chateau":
            paste_custom(roofs, "drapeau_ch.png", int(gx * T + 8), int(gy * T - 4), center=False)

        sites_meta.append(
            {
                "id": sid,
                "kit": kit,
                "prefab": pname,
                "gx": gx,
                "gy": gy,
                "fw": fw,
                "fh": fh,
            }
        )

    # Esplanade statue
    paste_custom(
        ground,
        "statue_or.png",
        int(mw * T / 2),
        int(path_y0 * T + (path_y1 - path_y0) * T / 2),
    )
    paste_custom(
        ground,
        "blason_vd.png",
        int(mw * T / 2 + 40),
        int(path_y0 * T + 20),
    )

    # Sample dossier on path (parcours cue)
    paste_custom(
        interiors,
        "dossier_16.png",
        int(mw * T / 2 - 60),
        int(path_y0 * T + 30),
    )

    OUT.mkdir(parents=True, exist_ok=True)
    ground.save(OUT / "ground.png")
    roofs.save(OUT / "roofs.png")
    interiors.save(OUT / "interiors.png")

    # Preview dual
    preview = ground.copy()
    preview.alpha_composite(Image.blend(roofs, interiors, 0.0))
    # roofs only preview
    p_roofs = ground.copy()
    p_roofs.alpha_composite(roofs)
    p_roofs.save(OUT / "preview_sunnyside_roofs.png")
    p_int = ground.copy()
    p_int.alpha_composite(interiors)
    p_int.save(OUT / "preview_sunnyside_interiors.png")

    meta = {
        "tile": T,
        "width": W,
        "height": H,
        "grid": {"w": mw, "h": mh},
        "scale": SCALE,
        "source": "sunnyside-v2.1",
        "playbook": "sprite-library TASK-117/119",
        "packs": [
            "Sunnyside World V2.1 — CC0",
            "Custom UX signatures TASK-119 — CC0-project",
        ],
        "credit": "Sunnyside World (CC0) + custom civic/UX assets (CC0-project). Layout from state-of-vd world.json.",
        "da": {
            "goal": "serious-game Place du Château — dual LOD Sunnyside",
            "method": "prefab stamp + color transposition + custom signatures",
            "kits": KIT_FOR_SITE,
        },
        "layers": {
            "ground": "ground.png",
            "roofs": "roofs.png",
            "interiors": "interiors.png",
        },
        "hotspots": len(hotspots),
        "sites": sites_meta,
    }
    (OUT / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    hs_doc = {
        "alignedTo": "state-of-vd/data/world.json",
        "compose": "sunnyside",
        "scale": SCALE,
        "hotspots": hotspots,
    }
    HOTSPOTS_OUT.write_text(
        json.dumps(hs_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # proof for TASK-118
    proof_dir = LIB_DIR / "proofs"
    proof_dir.mkdir(exist_ok=True)
    # mini proof: crop parlement + esplanade
    box = (0, 0, min(W, 40 * T), min(H, 28 * T))
    p_roofs.crop(box).save(proof_dir / "proof_118_sunnyside_roofs.png")
    p_int.crop(box).save(proof_dir / "proof_118_sunnyside_interiors.png")

    print(f"OK compose Sunnyside {mw}x{mh} @ {T}px → {W}x{H}")
    print(f"  layers: {OUT}")
    print(f"  hotspots: {len(hotspots)}")
    print(f"  sites: {len(sites_meta)}")


if __name__ == "__main__":
    main()
