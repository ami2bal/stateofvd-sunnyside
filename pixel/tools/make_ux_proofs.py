#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_ux_proofs.py — preuves d'usage des assets custom (TASK-119).

Compose des scènes minimales depuis library.json (customs + tuiles Sunnyside)
pour prouver que chaque groupe s'emploie en contexte. Sorties : proofs/ux_*.png
"""
import io
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "assets/sprite-library"
PROOFS = LIB / "proofs"
T, COLS, Z = 16, 64, 5

libj = json.load(open(LIB / "library.json", encoding="utf-8"))
BY_ID = {e["id"]: e for e in libj["entries"]}
SHEET = Image.open(ROOT / "assets/packs/sunnyside/Sunnyside_World_ASSET_PACK_V2.1/"
                          "Sunnyside_World_Assets/Tileset/spr_tileset_sunnysideworld_16px.png").convert("RGBA")


def cust(slug):
    return Image.open(ROOT / BY_ID[f"custom_{slug}"]["file"]).convert("RGBA")


def tile(cr):
    c, r = cr
    return SHEET.crop((c * T, r * T, c * T + T, r * T + T))


def frame(img, title):
    big = img.resize((img.width * Z, img.height * Z), Image.NEAREST)
    out = Image.new("RGBA", (big.width, big.height + 18), (30, 30, 34, 255))
    ImageDraw.Draw(out).text((4, 3), title, fill=(230, 230, 120, 255))
    out.alpha_composite(big, (0, 18))
    return out.convert("RGB")


def proof_dossier_carry():
    """Dossier sur table (kit bois) + perso CARRY portant le dossier overlay."""
    W, H = 14, 8
    img = Image.new("RGBA", (W * T, H * T), (0, 0, 0, 0))
    grass = tile((28, 8)); wood = tile((9, 8))
    for y in range(H):
        for x in range(W):
            img.alpha_composite(grass, (x * T, y * T))
    for y in range(4, 6):
        for x in range(2, 8):
            img.alpha_composite(wood, (x * T, y * T))       # table/plancher
    img.alpha_composite(cust("dossier_16"), (3 * T, 4 * T))  # dossier posé
    img.alpha_composite(cust("dossier_empd"), (5 * T, 4 * T))
    # perso CARRY (frame 0 base) + overlay dossier
    hum = None
    for e in libj["entries"]:
        if e.get("family") == "character_human" and e.get("subtype", "").startswith("carry"):
            hum = e; break
    if hum:
        strip = Image.open(ROOT / hum["file"]).convert("RGBA")
        fw = hum["frame_size"][0]
        img.alpha_composite(strip.crop((0, 0, fw, strip.height)), (9 * T, 2 * T))
    img.alpha_composite(cust("dossier_carry_overlay"), (9 * T, 2 * T))
    frame(img, "UX P1 — dossier pose (EMPD) + perso CARRY portant le dossier (fil conducteur)").save(
        PROOFS / "ux_1_dossier_carry.png")
    print("ux_1_dossier_carry.png")


def proof_hemicycle():
    """Hémicycle dans un footprint plénum (murs kit vert + sol bois)."""
    W, H = 15, 10
    img = Image.new("RGBA", (W * T, H * T), (0, 0, 0, 0))
    grass = tile((28, 8)); wood = tile((9, 8))
    # sol de salle
    for y in range(H):
        for x in range(W):
            img.alpha_composite(grass, (x * T, y * T))
    for y in range(1, 9):
        for x in range(1, 14):
            img.alpha_composite(wood, (x * T, y * T))
    # tableau de vote au mur du fond, tribune, hémicycle, urne
    img.alpha_composite(cust("tableau_vote"), (6 * T, 1 * T))
    hemi = cust("hemicycle_arc")
    img.alpha_composite(hemi, ((W * T - hemi.width) // 2, 3 * T))
    img.alpha_composite(cust("tribune_president"), (7 * T - 4, 8 * T))
    img.alpha_composite(cust("urne"), (12 * T, 7 * T))
    img.alpha_composite(cust("drapeau_vd"), (1 * T, 1 * T))
    img.alpha_composite(cust("lanterne_verte"), (13 * T, 2 * T))
    frame(img, "UX P2 — plenum GC : hemicycle en arc + tribune + tableau vote + urne + drapeau/lanterne VD").save(
        PROOFS / "ux_2_hemicycle_plenum.png")
    print("ux_2_hemicycle_plenum.png")


def proof_college():
    W, H = 12, 8
    img = Image.new("RGBA", (W * T, H * T), (0, 0, 0, 0))
    grass = tile((28, 8)); wood = tile((10, 8))
    for y in range(H):
        for x in range(W):
            img.alpha_composite(grass, (x * T, y * T))
    for y in range(1, 7):
        for x in range(1, 11):
            img.alpha_composite(wood, (x * T, y * T))
    tbl = cust("table_college")
    img.alpha_composite(tbl, ((W * T - tbl.width) // 2, (H * T - tbl.height) // 2))
    img.alpha_composite(cust("presse_fao"), (0, 0))
    img.alpha_composite(cust("drapeau_ch"), (10 * T, 0))
    frame(img, "UX P3 — college CE : table ovale 7 places + presse FAO + drapeau CH").save(
        PROOFS / "ux_3_college_ce.png")
    print("ux_3_college_ce.png")


def proof_hud():
    """Barre HUD Mode Parcours : Ariane (badges+digits) + transport + step-card icons."""
    W, H = 320, 120
    img = Image.new("RGBA", (W, H), (30, 30, 38, 255))
    d = ImageDraw.Draw(img)
    d.text((6, 4), "UX P4 — HUD Mode Parcours (atlas custom)", fill=(230, 230, 140, 255))
    # fil d'Ariane
    x = 12
    seq = ["badge_done", "badge_done", "badge_current", "badge_branch", "badge_next"]
    for i, b in enumerate(seq):
        ic = cust(b).resize((24, 24), Image.NEAREST)
        img.alpha_composite(ic, (x, 26))
        if i < len(seq) - 1:
            d.line([x + 26, 38, x + 40, 38], fill=(120, 130, 150, 255), width=2)
        x += 44
    # transport
    tx = 12
    for b in ["tr_play", "tr_pause", "tr_stop", "tr_speed_slow", "tr_speed_norm", "tr_speed_fast"]:
        img.alpha_composite(cust(b).resize((24, 24), Image.NEAREST), (tx, 62))
        tx += 30
    # activités + issues
    ax = 12
    for b in ["act_instruction", "act_transmission", "act_decision", "act_publication",
              "act_coordination", "act_controle", "act_citoyen", "issue_accept", "issue_reject"]:
        img.alpha_composite(cust(b).resize((22, 22), Image.NEAREST), (ax, 92))
        ax += 26
    img.convert("RGB").save(PROOFS / "ux_4_hud_parcours.png")
    print("ux_4_hud_parcours.png")


def proof_civic():
    W, H = 16, 6
    img = Image.new("RGBA", (W * T, H * T), (0, 0, 0, 0))
    grass = tile((28, 8)); stone = tile((9, 15))
    for y in range(H):
        for x in range(W):
            img.alpha_composite(grass, (x * T, y * T))
    for y in range(4, 6):
        for x in range(W):
            img.alpha_composite(stone, (x * T, y * T))   # esplanade
    img.alpha_composite(cust("statue_or"), (7 * T, 1 * T))
    img.alpha_composite(cust("drapeau_vd"), (2 * T, 1 * T))
    img.alpha_composite(cust("drapeau_ch"), (12 * T, 1 * T))
    img.alpha_composite(cust("blason_vd"), (5 * T, 3 * T))
    for x in (9, 10, 11):
        img.alpha_composite(cust("vigne_lavaux"), (x * T, 4 * T))
    frame(img, "UX P5 — esplanade : statue (grise+halo or) + drapeaux VD/CH + blason + vigne Lavaux").save(
        PROOFS / "ux_5_esplanade_civique.png")
    print("ux_5_esplanade_civique.png")


def main():
    PROOFS.mkdir(parents=True, exist_ok=True)
    proof_dossier_carry(); proof_hemicycle(); proof_college(); proof_hud(); proof_civic()
    print("5 proofs UX composees depuis library.json")


if __name__ == "__main__":
    main()
