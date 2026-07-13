#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_custom_assets.py — assets custom UX / identité (TASK-119).

Dessine (PIL, palette Sunnyside échantillonnée sur le tileset) les pièces
ABSENTES du pack village : fil « dossier législatif » (A), mobilier-signature
institutionnel (B), symboles civiques vaudois (C), atlas HUD Mode Parcours (D).

Chaque pièce → PNG sous assets/sprite-library/custom/<family>/<slug>.png +
une entrée dans custom_entries.json (fusionnée dans library.json par
build_sprite_library.py). Régénérable : python tools/build_custom_assets.py

Style : pixel 16-base, fond transparent, teintes prélevées sur
spr_tileset_sunnysideworld_16px.png (cohérence palette maître).
"""
import io
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
CUST = ROOT / "assets/sprite-library/custom"

# ── Palette Sunnyside (échantillonnée + nuances dérivées) ──────────────────
P = {
    "wood":   (228, 166, 114), "wood_d": (150, 96, 52),  "wood_l": (245, 205, 155),
    "stone":  (116, 132, 158), "stone_d": (78, 90, 112), "stone_l": (176, 188, 205),
    "grass":  (99, 199, 77),   "grass_d": (60, 140, 55),
    "water":  (50, 200, 220),
    "blue":   (0, 139, 199),   "green": (108, 170, 70),  "green_l": (144, 191, 93),
    "orange": (239, 151, 52),  "red": (226, 58, 67),     "purple": (150, 110, 180),
    "gold":   (230, 175, 60),  "gold_l": (250, 220, 120), "gold_d": (170, 120, 30),
    "paper":  (238, 226, 196), "paper_d": (205, 186, 150), "ink": (60, 48, 36),
    "vd_green": (0, 150, 70),  "white": (245, 245, 240),
    "dark":   (44, 40, 52),    "panel": (52, 60, 74),    "panel_l": (86, 98, 116),
    "black":  (28, 24, 30),    "cream": (250, 240, 214),
    "cloth":  (170, 60, 60),   "cloth_d": (120, 38, 44),
}


def C(name, a=255):
    r, g, b = P[name]
    return (r, g, b, a)


def canvas(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


ENTRIES = []


def save(img, family, slug, role, layer, assembly, subtype=None, **extra):
    d = CUST / family
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{slug}.png"
    img.save(path)
    e = {
        "id": f"custom_{slug}", "source": "custom",
        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "family": family, "fine": True, "role": role, "layer": layer,
        "assembly": assembly, "size": [img.width, img.height],
        "license": "CC0-project",
    }
    if subtype:
        e["subtype"] = subtype
    e.update(extra)
    ENTRIES.append(e)
    return e


# ── Primitives ─────────────────────────────────────────────────────────────
def rect(dr, x0, y0, x1, y1, col):
    dr.rectangle([x0, y0, x1, y1], fill=col)


def outline(dr, x0, y0, x1, y1, col):
    dr.rectangle([x0, y0, x1, y1], outline=col)


# ═══════════════════════════════ A — DOSSIER ═══════════════════════════════
FAM_DOSSIER = "dossier_props"
TYPES = [  # (slug, tab_color, lettre)
    ("empd", "red", "D"), ("empl", "orange", "L"), ("motion", "blue", "M"),
    ("postulat", "green", "P"), ("petition", "purple", "T"), ("decret", "gold", "✦"),
]


def draw_folder(w=16, h=16, tab="wood_d", body="wood", flap="wood_l"):
    img = canvas(w, h)
    d = ImageDraw.Draw(img)
    # chemise (folder) : corps + rabat + onglet
    rect(d, 2, 5, 13, 14, C(body))
    rect(d, 2, 5, 13, 6, C(flap))            # bord haut clair
    rect(d, 2, 13, 13, 14, C("wood_d"))      # ombre bas
    rect(d, 3, 3, 8, 5, C(tab))              # onglet
    # feuilles qui dépassent
    rect(d, 4, 6, 11, 7, C("paper"))
    rect(d, 4, 8, 10, 8, C("paper_d"))
    outline(d, 2, 5, 13, 14, C("wood_d"))
    return img


def asset_dossier():
    # prop 16 sol/table
    save(draw_folder(), FAM_DOSSIER, "dossier_16", "prop", "furniture", "overlay",
         subtype="dossier_base", usage="prop sol/table, base du fil conducteur")
    # icône HUD 32 (agrandie + liseré lisible)
    ic = draw_folder(16, 16).resize((32, 32), Image.NEAREST)
    d = ImageDraw.Draw(ic)
    outline(d, 0, 0, 31, 31, C("dark", 0))
    save(ic, FAM_DOSSIER, "dossier_icon_32", "ui", "ui", "overlay",
         subtype="dossier_icon", usage="icône HUD/step-card/pastille")
    # icône 24
    save(draw_folder(16, 16).resize((24, 24), Image.NEAREST), FAM_DOSSIER,
         "dossier_icon_24", "ui", "ui", "overlay", subtype="dossier_icon")
    # overlay porté CARRY (petit, aligné bras — cadre 96x64, dossier ~ centre-bas)
    ov = canvas(96, 64)
    fold = draw_folder(14, 14)
    ov.alpha_composite(fold, (44, 34))
    save(ov, FAM_DOSSIER, "dossier_carry_overlay", "prop", "entities", "overlay",
         subtype="dossier_carry", usage="overlay frame perso CARRY (main/bras)")
    # 6 variantes type (onglet couleur + lettre)
    for slug, col, letter in TYPES:
        img = draw_folder(tab=col)
        d = ImageDraw.Draw(img)
        # pastille lettre
        d.text((9, 8), letter, fill=C("ink"))
        save(img, FAM_DOSSIER, f"dossier_{slug}", "prop", "furniture", "overlay",
             subtype=f"dossier_{slug}", tab_color=col,
             usage=f"variante type d'objet : {slug.upper()}")


def asset_sceau_plume_enveloppe():
    # sceau / tampon (cire rouge + poignée)
    img = canvas(16, 16)
    d = ImageDraw.Draw(img)
    d.ellipse([3, 8, 12, 14], fill=C("cloth"))         # cire
    d.ellipse([5, 9, 10, 13], outline=C("cloth_d"))    # empreinte
    rect(d, 6, 3, 9, 8, C("wood_d"))                    # manche
    rect(d, 6, 3, 9, 4, C("wood_l"))
    save(img, FAM_DOSSIER, "sceau", "prop", "furniture", "overlay",
         subtype="sceau", usage="étape adoption/promulgation")
    # plume / signature
    img = canvas(16, 16)
    d = ImageDraw.Draw(img)
    d.line([3, 13, 12, 3], fill=C("white"), width=2)   # tige plume
    d.line([11, 3, 13, 5], fill=C("stone_l"), width=1)
    rect(d, 2, 12, 6, 14, C("ink"))                     # trait d'encre
    save(img, FAM_DOSSIER, "plume", "prop", "furniture", "overlay",
         subtype="plume", usage="étape collège CE / signature")
    # enveloppe / courrier
    img = canvas(16, 16)
    d = ImageDraw.Draw(img)
    rect(d, 2, 4, 13, 12, C("cream"))
    d.line([2, 4, 7, 8], fill=C("paper_d"))
    d.line([13, 4, 8, 8], fill=C("paper_d"))
    d.line([2, 4, 13, 4], fill=C("paper_d"))
    outline(d, 2, 4, 13, 12, C("wood_d"))
    rect(d, 10, 9, 12, 11, C("cloth"))                  # cachet
    save(img, FAM_DOSSIER, "enveloppe", "prop", "furniture", "overlay",
         subtype="enveloppe", usage="pétitions / courriers / saisine tiers")


# ═══════════════════════════════ D — HUD ═══════════════════════════════════
FAM_UX = "ux_icons"

DIGITS = {
    "0": ["111", "101", "101", "101", "111"], "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"], "3": ["111", "001", "111", "001", "111"],
    "4": ["101", "101", "111", "001", "001"], "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"], "7": ["111", "001", "010", "010", "010"],
    "8": ["111", "101", "111", "101", "111"], "9": ["111", "101", "111", "001", "111"],
}


def asset_digits():
    # strip horizontal 0-9, chaque chiffre 3x5 dans une cellule 5x7, échelle x2
    cell_w, cell_h, sc = 5, 7, 2
    strip = canvas(10 * cell_w * sc, cell_h * sc)
    d = ImageDraw.Draw(strip)
    for i in range(10):
        pat = DIGITS[str(i)]
        ox = i * cell_w * sc + 1 * sc
        for ry, row in enumerate(pat):
            for rx, ch in enumerate(row):
                if ch == "1":
                    x = ox + rx * sc
                    y = (1 + ry) * sc
                    rect(d, x, y, x + sc - 1, y + sc - 1, C("cream"))
    save(strip, FAM_UX, "digits_0_9", "ui", "ui", "overlay",
         subtype="digits", frames=10, cell=[cell_w * sc, cell_h * sc],
         usage="fil d'Ariane, pastilles d'étape (numéros)")


def disc(size, fill, ring=None, glyph=None):
    img = canvas(size, size)
    d = ImageDraw.Draw(img)
    d.ellipse([1, 1, size - 2, size - 2], fill=fill,
              outline=ring or C("dark"))
    if glyph:
        glyph(d, size)
    return img


def asset_step_badges():
    S = 16
    # done = vert plein + check ; current = or plein + point ; next = contour ; branch = losange
    def chk(d, s):
        d.line([4, 8, 7, 11], fill=C("white"), width=2)
        d.line([7, 11, 12, 5], fill=C("white"), width=2)

    save(disc(S, C("vd_green"), glyph=chk), FAM_UX, "badge_done", "ui", "ui", "overlay",
         subtype="badge", state="done", usage="étape faite")
    save(disc(S, C("gold"), C("gold_d"),
              glyph=lambda d, s: d.ellipse([6, 6, 9, 9], fill=C("white"))),
         FAM_UX, "badge_current", "ui", "ui", "overlay", subtype="badge",
         state="current", usage="étape courante")
    img = canvas(S, S)
    d = ImageDraw.Draw(img)
    d.ellipse([2, 2, S - 3, S - 3], outline=C("stone_l"))
    save(img, FAM_UX, "badge_next", "ui", "ui", "overlay", subtype="badge",
         state="next", usage="étape à venir")
    # branch = losange orange
    img = canvas(S, S)
    d = ImageDraw.Draw(img)
    d.polygon([(8, 1), (15, 8), (8, 15), (1, 8)], fill=C("orange"), outline=C("wood_d"))
    save(img, FAM_UX, "badge_branch", "ui", "ui", "overlay", subtype="badge",
         state="branch", usage="point de branche/décision")


def asset_transport():
    S = 16

    def mk(glyph, slug, usage):
        img = canvas(S, S)
        d = ImageDraw.Draw(img)
        d.ellipse([0, 0, S - 1, S - 1], fill=C("panel"), outline=C("panel_l"))
        glyph(d)
        save(img, FAM_UX, slug, "ui", "ui", "overlay", subtype="transport", usage=usage)

    mk(lambda d: d.polygon([(6, 4), (6, 12), (12, 8)], fill=C("cream")), "tr_play", "lecture Parcours")
    mk(lambda d: (rect(d, 5, 4, 7, 12, C("cream")), rect(d, 9, 4, 11, 12, C("cream"))),
       "tr_pause", "pause")
    mk(lambda d: rect(d, 5, 5, 11, 11, C("cream")), "tr_stop", "stop")
    # vitesses : 1, 2, 3 chevrons
    for n, slug in ((1, "tr_speed_slow"), (2, "tr_speed_norm"), (3, "tr_speed_fast")):
        def g(d, n=n):
            for k in range(n):
                x = 4 + k * 3
                d.polygon([(x, 5), (x, 11), (x + 3, 8)], fill=C("cream"))
        mk(g, slug, f"vitesse ×{['0,6','1','1,6'][n-1]}")


def asset_branch_issue():
    S = 16
    img = canvas(S, S)
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, S - 1, S - 1], fill=C("vd_green"), outline=C("grass_d"))
    d.line([4, 8, 7, 11], fill=C("white"), width=2)
    d.line([7, 11, 12, 5], fill=C("white"), width=2)
    save(img, FAM_UX, "issue_accept", "ui", "ui", "overlay", subtype="issue",
         state="accept", usage="accepter (branche)")
    img = canvas(S, S)
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, S - 1, S - 1], fill=C("red"), outline=C("cloth_d"))
    d.line([4, 4, 12, 12], fill=C("white"), width=2)
    d.line([12, 4, 4, 12], fill=C("white"), width=2)
    save(img, FAM_UX, "issue_reject", "ui", "ui", "overlay", subtype="issue",
         state="reject", usage="rejeter (branche)")


def asset_activity_icons():
    """7 icônes d'activité alignées ACTIVITY_LABEL."""
    S = 16
    acts = {
        "instruction": ("blue", lambda d: (rect(d, 4, 3, 11, 13, C("cream")),
                                            rect(d, 5, 5, 10, 6, C("blue")),
                                            rect(d, 5, 8, 10, 9, C("blue")))),
        "transmission": ("orange", lambda d: (d.polygon([(3, 8), (10, 4), (10, 12)], fill=C("cream")),
                                               rect(d, 10, 7, 13, 9, C("cream")))),
        "decision": ("gold", lambda d: (rect(d, 7, 3, 8, 13, C("cream")),      # balance
                                        rect(d, 3, 5, 12, 6, C("cream")),
                                        d.ellipse([2, 6, 5, 9], outline=C("cream")),
                                        d.ellipse([10, 6, 13, 9], outline=C("cream")))),
        "publication": ("green", lambda d: (rect(d, 3, 4, 12, 12, C("cream")),   # journal
                                            rect(d, 4, 6, 7, 11, C("green")),
                                            rect(d, 8, 6, 11, 7, C("green")),
                                            rect(d, 8, 9, 11, 10, C("green")))),
        "coordination": ("purple", lambda d: (d.ellipse([5, 5, 10, 10], outline=C("cream")),
                                               d.ellipse([2, 8, 6, 12], outline=C("cream")),
                                               d.ellipse([9, 8, 13, 12], outline=C("cream")))),
        "controle": ("red", lambda d: (d.ellipse([3, 3, 10, 10], outline=C("cream")),  # loupe
                                       d.line([9, 9, 13, 13], fill=C("cream"), width=2))),
        "citoyen": ("vd_green", lambda d: (d.ellipse([6, 3, 10, 7], fill=C("cream")),   # personne
                                           d.polygon([(4, 13), (5, 8), (11, 8), (12, 13)], fill=C("cream")))),
    }
    for name, (col, glyph) in acts.items():
        img = canvas(S, S)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([0, 0, S - 1, S - 1], radius=3, fill=C(col), outline=C("dark"))
        glyph(d)
        save(img, FAM_UX, f"act_{name}", "ui", "ui", "overlay", subtype="activity",
             activity=name, usage=f"kicker step-card / Ariane : {name}")


def asset_flow_markers():
    # perle IN (entrée) / OUT (sortie) + têtes de flèche
    img = canvas(10, 10)
    d = ImageDraw.Draw(img)
    d.ellipse([1, 1, 8, 8], fill=C("vd_green"), outline=C("white"))
    save(img, FAM_UX, "flow_perle_in", "ui", "ui", "overlay", subtype="flow",
         dir="in", usage="perle entrée flux RBAC")
    img = canvas(10, 10)
    d = ImageDraw.Draw(img)
    d.ellipse([1, 1, 8, 8], fill=C("orange"), outline=C("white"))
    save(img, FAM_UX, "flow_perle_out", "ui", "ui", "overlay", subtype="flow",
         dir="out", usage="perle sortie flux RBAC")
    img = canvas(10, 10)
    d = ImageDraw.Draw(img)
    d.polygon([(2, 2), (8, 5), (2, 8)], fill=C("cream"))
    save(img, FAM_UX, "flow_arrowhead", "ui", "ui", "overlay", subtype="flow",
         usage="tête de flèche sémantique (connections)")


def asset_ring_pin_timer():
    # anneau de sélection (4 coins)
    S = 20
    img = canvas(S, S)
    d = ImageDraw.Draw(img)
    for cx, cy in ((0, 0), (1, 0), (0, 1)):
        pass
    L = 5
    for (ax, ay, bx, by) in [(0, 0, L, 0), (0, 0, 0, L),
                             (S - 1, 0, S - 1 - L, 0), (S - 1, 0, S - 1, L),
                             (0, S - 1, L, S - 1), (0, S - 1, 0, S - 1 - L),
                             (S - 1, S - 1, S - 1 - L, S - 1), (S - 1, S - 1, S - 1, S - 1 - L)]:
        d.line([ax, ay, bx, by], fill=C("gold_l"), width=2)
    save(img, FAM_UX, "selection_ring", "ui", "ui", "overlay", subtype="ring",
         usage="hover/pin salle")
    # pin carte
    img = canvas(12, 16)
    d = ImageDraw.Draw(img)
    d.ellipse([1, 1, 10, 10], fill=C("red"), outline=C("cloth_d"))
    d.ellipse([4, 4, 7, 7], fill=C("white"))
    d.polygon([(3, 9), (8, 9), (6, 15)], fill=C("red"))
    save(img, FAM_UX, "map_pin", "ui", "ui", "overlay", subtype="pin",
         usage="focus scénario / marque-lieu")
    # timer ring : 1 track + 4 arcs (frames)
    for i, frac in enumerate((25, 50, 75, 100)):
        S = 16
        img = canvas(S, S)
        d = ImageDraw.Draw(img)
        d.ellipse([1, 1, S - 2, S - 2], outline=C("panel_l"))
        d.arc([1, 1, S - 2, S - 2], -90, -90 + int(360 * frac / 100),
              fill=C("gold_l"), width=2)
        save(img, FAM_UX, f"timer_ring_{frac}", "ui", "ui", "overlay", subtype="timer",
             frac=frac, usage="countdown step-card")


def asset_9slice_tinted():
    """3 panels 9-slice teintés (vert GC / or CE / bleu neutre), 24x24, coins 6px."""
    for slug, col in (("panel_gc_green", "vd_green"), ("panel_ce_gold", "gold"),
                      ("panel_neutral_blue", "blue")):
        S = 24
        img = canvas(S, S)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([0, 0, S - 1, S - 1], radius=6,
                            fill=C("panel"), outline=C(col))
        d.rounded_rectangle([1, 1, S - 2, S - 2], radius=5, outline=C(col, 120))
        save(img, FAM_UX, slug, "ui", "ui", "fill", subtype="panel_9slice",
             tint=col, slice9=6, usage="inspector / step-card / Ariane (teinté)")


# ═══════════════════════════════ C — CIVIQUE ═══════════════════════════════
FAM_CIVIC = "civic_symbols"


def asset_civic():
    # Drapeau Vaud : mât + drapeau vert(haut)/blanc(bas)
    img = canvas(16, 20)
    d = ImageDraw.Draw(img)
    rect(d, 2, 1, 3, 19, C("wood_d"))               # mât
    rect(d, 4, 2, 14, 6, C("vd_green"))             # bande verte
    rect(d, 4, 7, 14, 11, C("white"))               # bande blanche
    outline(d, 4, 2, 14, 11, C("grass_d"))
    # devise stylisée (2 traits) sur le blanc
    rect(d, 6, 8, 12, 8, C("vd_green"))
    save(img, FAM_CIVIC, "drapeau_vd", "prop", "entities", "overlay",
         subtype="flag_vd", usage="façades GC, esplanade (identité cantonale)")
    # Drapeau suisse : rouge + croix blanche
    img = canvas(16, 20)
    d = ImageDraw.Draw(img)
    rect(d, 2, 1, 3, 19, C("wood_d"))
    rect(d, 4, 2, 13, 11, C("red"))
    rect(d, 8, 4, 9, 9, C("white"))
    rect(d, 6, 6, 11, 7, C("white"))
    save(img, FAM_CIVIC, "drapeau_ch", "prop", "entities", "overlay",
         subtype="flag_ch", usage="accent fédéral (facultatif)")
    # Blason / armoiries VD (écu vert-blanc)
    img = canvas(16, 16)
    d = ImageDraw.Draw(img)
    d.polygon([(3, 2), (12, 2), (12, 9), (7, 14), (3, 9)], fill=C("white"),
              outline=C("gold_d"))
    d.polygon([(3, 2), (12, 2), (12, 6), (3, 6)], fill=C("vd_green"))
    save(img, FAM_CIVIC, "blason_vd", "ui", "ui", "overlay", subtype="crest_vd",
         usage="chrome UI, esplanade, boot")
    # Statue dorée (silhouette grise + halo doré documenté)
    img = canvas(16, 22)
    d = ImageDraw.Draw(img)
    rect(d, 5, 18, 10, 21, C("stone_d"))            # socle
    rect(d, 6, 16, 9, 18, C("stone"))
    d.ellipse([6, 4, 9, 8], fill=C("stone_l"))      # tête
    d.polygon([(5, 16), (6, 8), (9, 8), (10, 16)], fill=C("stone_l"))  # corps
    # halo doré
    d.ellipse([3, 2, 12, 11], outline=C("gold_l"))
    save(img, FAM_CIVIC, "statue_or", "prop", "entities", "overlay",
         subtype="statue", usage="esplanade centrale (l'or réservé — halo doré)",
         note="statue grise + halo doré : l'or plein reste réservé à la navette")
    # Lanterne verte GC
    img = canvas(12, 16)
    d = ImageDraw.Draw(img)
    rect(d, 4, 1, 7, 2, C("wood_d"))                # support
    rect(d, 3, 3, 8, 11, C("green"))                # cage verte
    rect(d, 4, 4, 7, 10, C("green_l"))              # vitre
    rect(d, 3, 11, 8, 12, C("wood_d"))
    save(img, FAM_CIVIC, "lanterne_verte", "prop", "walls", "overlay",
         subtype="lantern_gc", usage="signature façade parlement (DA)")
    # Tuile vigne Lavaux (rang de ceps)
    img = canvas(16, 16)
    d = ImageDraw.Draw(img)
    rect(d, 0, 0, 15, 15, C("grass_d"))
    for x in (2, 7, 12):
        rect(d, x, 2, x + 1, 13, C("wood_d"))       # piquet
        d.ellipse([x - 2, 4, x + 3, 9], outline=C("green"))   # feuillage
        d.ellipse([x - 1, 5, x + 2, 8], fill=C("green_l"))
    save(img, FAM_CIVIC, "vigne_lavaux", "prop", "ground", "fill",
         subtype="vine_row", usage="bande Est Lavaux (rang de ceps)")


# ═══════════════════════════════ B — MOBILIER ══════════════════════════════
FAM_FURN = "furniture_signature"


def asset_furniture():
    # Hémicycle : bancs en arc (3 rangs concentriques) — bbox ~ 13x8
    W, H = 13, 8
    img = canvas(W * 4, H * 4)  # dessiné x4 pour lisibilité de l'arc
    d = ImageDraw.Draw(img)
    cx, cy = W * 2, H * 4 - 4
    for k, rad in enumerate((14, 22, 30)):
        col = C("wood") if k % 2 == 0 else C("wood_d")
        d.arc([cx - rad, cy - rad, cx + rad, cy + rad], 200, 340, fill=col, width=4)
    # perchoir central (petit rectangle au foyer)
    rect(d, cx - 4, cy - 6, cx + 4, cy, C("cloth"))
    rect(d, cx - 4, cy - 6, cx + 4, cy - 5, C("gold"))
    save(img, FAM_FURN, "hemicycle_arc", "furniture", "furniture", "overlay",
         subtype="hemicycle", bbox=[W, H], room="plenum-gc",
         usage="bancs en arc du Grand Conseil (cœur identité GC)")
    # Perchoir / tribune président (prop dédié 16x16)
    img = canvas(16, 16)
    d = ImageDraw.Draw(img)
    rect(d, 3, 6, 12, 14, C("wood"))
    rect(d, 3, 6, 12, 7, C("wood_l"))
    rect(d, 4, 8, 11, 11, C("cloth"))               # drapé
    rect(d, 6, 3, 9, 6, C("wood_d"))                # pupitre haut
    save(img, FAM_FURN, "tribune_president", "furniture", "furniture", "overlay",
         subtype="tribune", room="plenum-gc", usage="perchoir/tribune président")
    # Tableau de vote / panneau résultats (mural 16x12)
    img = canvas(16, 12)
    d = ImageDraw.Draw(img)
    rect(d, 1, 1, 14, 10, C("dark"))
    outline(d, 1, 1, 14, 10, C("stone_l"))
    for i, col in enumerate((C("vd_green"), C("red"), C("gold"))):
        rect(d, 3 + i * 4, 3, 5 + i * 4, 8, col)     # 3 colonnes de votes
    save(img, FAM_FURN, "tableau_vote", "furniture", "walls", "overlay",
         subtype="vote_board", room="plenum-gc", usage="panneau résultats de votes")
    # Urne / boîte de scrutin (16x16)
    img = canvas(16, 16)
    d = ImageDraw.Draw(img)
    rect(d, 3, 6, 12, 14, C("wood"))
    rect(d, 3, 6, 12, 7, C("wood_l"))
    rect(d, 6, 5, 9, 6, C("dark"))                  # fente
    rect(d, 5, 9, 10, 12, C("vd_green"))            # écusson
    save(img, FAM_FURN, "urne", "furniture", "furniture", "overlay",
         subtype="urne", room="plenum-gc", usage="boîte de scrutin (branche rejet/adopt)")
    # Table ovale collège (7 places) — 12x8
    img = canvas(12, 8)
    d = ImageDraw.Draw(img)
    d.ellipse([1, 2, 10, 7], fill=C("wood"), outline=C("wood_d"))
    d.ellipse([3, 3, 8, 6], fill=C("wood_l"))
    for (px, py) in [(1, 2), (4, 1), (7, 1), (10, 2), (2, 7), (6, 7), (9, 7)]:
        d.ellipse([px, py, px + 1, py + 1], fill=C("cloth"))  # 7 sièges
    save(img, FAM_FURN, "table_college", "furniture", "furniture", "overlay",
         subtype="table_ovale", room="college-ce", usage="table ovale du collège CE (7)")
    # Presse d'imprimerie / FAO (16x16)
    img = canvas(16, 16)
    d = ImageDraw.Draw(img)
    rect(d, 2, 3, 13, 5, C("stone_d"))              # bâti haut
    rect(d, 3, 5, 4, 13, C("stone"))                # montants
    rect(d, 11, 5, 12, 13, C("stone"))
    rect(d, 4, 8, 11, 10, C("wood"))                # plateau
    rect(d, 6, 10, 9, 13, C("paper"))               # feuille sortante
    rect(d, 6, 2, 9, 3, C("wood_d"))                # vis/levier
    save(img, FAM_FURN, "presse_fao", "furniture", "furniture", "overlay",
         subtype="presse", room="chancellerie", usage="presse FAO (publication officielle)")


# ═══════════════════════════════ MAIN ═════════════════════════════════════
def main():
    asset_dossier()
    asset_sceau_plume_enveloppe()
    asset_digits(); asset_step_badges(); asset_transport(); asset_branch_issue()
    asset_activity_icons(); asset_flow_markers(); asset_ring_pin_timer()
    asset_9slice_tinted()
    asset_civic()
    asset_furniture()
    out = ROOT / "assets/sprite-library/custom_entries.json"
    payload = {
        "custom_entries": "State of VD — assets custom UX/identité (TASK-119)",
        "generated_by": "tools/build_custom_assets.py (regenerable)",
        "license": "CC0-project (dessins originaux, palette Sunnyside)",
        "count": len(ENTRIES),
        "families": sorted({e["family"] for e in ENTRIES}),
        "entries": ENTRIES,
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    byf = {}
    for e in ENTRIES:
        byf[e["family"]] = byf.get(e["family"], 0) + 1
    print(f"custom_entries.json : {len(ENTRIES)} entrees")
    for k, v in sorted(byf.items()):
        print(f"  {v:3d}  {k}")
    make_custom_sheets(byf)


def make_custom_sheets(byf):
    """Planches de contact par famille custom (family_<family>.png sous sheets/)."""
    sheets = ROOT / "assets/sprite-library/sheets"
    sheets.mkdir(parents=True, exist_ok=True)
    for fam in byf:
        items = [(e["id"].replace("custom_", ""), Image.open(ROOT / e["file"]).convert("RGBA"))
                 for e in ENTRIES if e["family"] == fam]
        tw, PAD, LBL, PERROW = 56, 6, 10, 8
        rows = (len(items) + PERROW - 1) // PERROW
        W = PAD + PERROW * (tw + PAD)
        H = PAD + rows * (tw + LBL + PAD) + LBL
        cv = Image.new("RGBA", (W, H), (38, 38, 44, 255))
        d = ImageDraw.Draw(cv)
        d.text((PAD, 1), f"{fam} ({len(items)}) — custom CC0-project", fill=(230, 230, 120, 255))
        for i, (name, im) in enumerate(items):
            sc = max(1, min(tw // max(im.width, 1), tw // max(im.height, 1)))
            big = im.resize((im.width * sc, im.height * sc), Image.NEAREST)
            x = PAD + (i % PERROW) * (tw + PAD)
            y = LBL + PAD + (i // PERROW) * (tw + LBL + PAD)
            cv.alpha_composite(big, (x + (tw - big.width) // 2, y + (tw - big.height) // 2))
            d.text((x, y + tw), name[:10], fill=(255, 255, 255, 255))
        cv.convert("RGB").save(sheets / f"family_{fam}.png")
    print(f"planches custom : {len(byf)} familles -> sheets/family_<famille>.png")


if __name__ == "__main__":
    main()
