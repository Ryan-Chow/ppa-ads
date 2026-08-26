#!/usr/bin/env python3
"""
Peer Prep Academy — 5-card Meta carousel ad generator.

Outputs five 1080x1080 PNGs (output/card1.png ... card5.png) plus a
preview_strip.png contact sheet.

Brand system
------------
  navy    #0F1E30   background
  paper   #F7F3EA   primary text
  gold    #CBA254   accent
  slate   #A8B2C0   secondary text

  Display type : Instrument Serif (google/fonts)
  UI type      : Inter variable (opsz, wght) via set_variation_by_axes

Every card carries the wordmark top-left with a gold underline, 92px
margins, and a scantron A–E bubble strip bottom-right whose filled gold
bubble advances one position per card.

Every mark drawn through the helpers below is recorded in INK, and
`check_safe_area` asserts nothing lands within 60px of an edge.
"""

import os
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageEnhance

# --------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------

W = H = 1080
MARGIN = 92
SAFE = 60                      # hard "no ink inside this" edge band
CONTENT_BOTTOM = 880           # keeps copy clear of the scantron strip
FONT_DIR = "fonts"
OUT_DIR = "output"

NAVY = (15, 30, 48)            # #0F1E30
PAPER = (247, 243, 234)        # #F7F3EA
GOLD = (203, 162, 84)          # #CBA254
SLATE = (168, 178, 192)        # #A8B2C0

DUO_SHADOW = (9, 19, 32)       # #091320
DUO_HIGHLIGHT = (198, 212, 226)  # soft blue-grey

SERIF = os.path.join(FONT_DIR, "InstrumentSerif-Regular.ttf")
SERIF_IT = os.path.join(FONT_DIR, "InstrumentSerif-Italic.ttf")
INTER = os.path.join(FONT_DIR, "Inter[opsz,wght].ttf")

INK = []                       # bounding boxes of everything drawn


def ink(box):
    INK.append(tuple(box))


# --------------------------------------------------------------------------
# type helpers
# --------------------------------------------------------------------------

def serif(size, italic=False):
    return ImageFont.truetype(SERIF_IT if italic else SERIF, size)


def inter(size, weight=400, opsz=None):
    f = ImageFont.truetype(INTER, size)
    if opsz is None:
        opsz = max(14, min(32, size))
    f.set_variation_by_axes([opsz, weight])
    return f


def text_w(draw, s, font, tracking=0.0):
    """Width of a string, accounting for manual letter-spacing."""
    if not s:
        return 0.0
    return draw.textlength(s, font=font) + tracking * (len(s) - 1)


def draw_tracked(draw, xy, s, font, fill, tracking=0.0):
    """Draw one line with optional manual letter-spacing. xy = left/top."""
    x, y = xy
    if tracking == 0:
        draw.text((x, y), s, font=font, fill=fill)
    else:
        cx = x
        for ch in s:
            draw.text((cx, y), ch, font=font, fill=fill)
            cx += draw.textlength(ch, font=font) + tracking
    bb = font.getbbox(s)
    ink((x + bb[0], y + bb[1],
         x + text_w(draw, s, font, tracking), y + bb[3]))


def wrap(draw, s, font, max_w, tracking=0.0):
    """Greedy word wrap to a pixel width."""
    lines, cur = [], ""
    for word in s.split():
        trial = word if not cur else cur + " " + word
        if text_w(draw, trial, font, tracking) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_block(draw, x, y, lines, font, fill, leading, tracking=0.0):
    """Draw pre-wrapped lines from a top-left origin. Returns the new y."""
    for ln in lines:
        draw_tracked(draw, (x, y), ln, font, fill, tracking)
        y += leading
    return y


def rect(draw, box, fill):
    draw.rectangle(box, fill=fill)
    ink(box)


def layer(img, fn, scale=4):
    """Run fn(draw, scale) on a supersampled RGBA layer, then composite.

    Keeps circles and rounded corners clean — Pillow's own shape drawing
    is not antialiased.
    """
    big = Image.new("RGBA", (W * scale, H * scale), (0, 0, 0, 0))
    fn(ImageDraw.Draw(big), scale)
    small = big.resize((W, H), Image.LANCZOS)
    img.paste(small, (0, 0), small)


# --------------------------------------------------------------------------
# photo treatment
# --------------------------------------------------------------------------

def duotone_square(path, size=W, focus=(0.5, 0.5), zoom=1.0):
    """EXIF-corrected square crop, navy duotone.

    focus is a point of the source in 0..1, held at the centre of the crop
    as far as the frame allows.
    """
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    sw, sh = im.size

    side = min(int(min(sw, sh) / zoom), sw, sh)
    cx, cy = focus[0] * sw, focus[1] * sh
    left = int(round(max(0, min(sw - side, cx - side / 2))))
    top = int(round(max(0, min(sh - side, cy - side / 2))))

    im = im.crop((left, top, left + side, top + side))
    im = im.resize((size, size), Image.LANCZOS)

    # tonal prep, then map black -> shadow, white -> highlight
    g = ImageOps.grayscale(im)
    g = ImageOps.autocontrast(g, cutoff=1)
    g = ImageEnhance.Contrast(g).enhance(1.06)
    duo = ImageOps.colorize(g, black=DUO_SHADOW, white=DUO_HIGHLIGHT,
                            mid=(46, 74, 104))
    return duo.convert("RGB")


def _apply_mask(img, mask, colour):
    layer_img = Image.new("RGB", img.size, colour)
    return Image.composite(layer_img, img, mask)


def bottom_scrim(img, start=0.26, strength=252, colour=(6, 14, 24), gamma=1.5):
    """Dark gradient rising from the bottom so type stays legible."""
    h = img.size[1]
    mask = Image.new("L", (1, h))
    px = mask.load()
    y0 = int(h * start)
    for y in range(h):
        t = 0.0 if y <= y0 else (y - y0) / float(h - y0)
        px[0, y] = max(0, min(255, int(strength * (t ** gamma))))
    return _apply_mask(img, mask.resize(img.size, Image.BILINEAR), colour)


def top_scrim(img, depth=0.32, strength=165, colour=(6, 14, 24)):
    """Softer gradient at the top so the wordmark reads on any photo."""
    h = img.size[1]
    mask = Image.new("L", (1, h))
    px = mask.load()
    y1 = max(1, int(h * depth))
    for y in range(h):
        t = 0.0 if y >= y1 else 1.0 - (y / float(y1))
        px[0, y] = max(0, min(255, int(strength * (t ** 1.4))))
    return _apply_mask(img, mask.resize(img.size, Image.BILINEAR), colour)


def left_scrim(img, end=0.68, strength=180, colour=(6, 14, 24)):
    """Left-hand gradient — holds the text column against a busy photo."""
    w = img.size[0]
    mask = Image.new("L", (w, 1))
    px = mask.load()
    x1 = max(1, int(w * end))
    for x in range(w):
        t = 0.0 if x >= x1 else 1.0 - (x / float(x1))
        px[x, 0] = max(0, min(255, int(strength * (t ** 1.25))))
    return _apply_mask(img, mask.resize(img.size, Image.BILINEAR), colour)


def navy_field():
    """Navy ground with a slight warm lift top-left and a soft vignette."""
    base = Image.new("RGB", (W, H), NAVY)

    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse((-460, -560, 760, 500), fill=44)
    glow = glow.filter(ImageFilter.GaussianBlur(200))
    base = Image.composite(Image.new("RGB", (W, H), (26, 45, 68)), base, glow)

    vig = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vig).ellipse((-300, -300, W + 300, H + 300), fill=255)
    vig = ImageOps.invert(vig.filter(ImageFilter.GaussianBlur(180)))
    vig = vig.point(lambda v: int(v * 0.55))
    return Image.composite(Image.new("RGB", (W, H), (8, 17, 28)), base, vig)


# --------------------------------------------------------------------------
# recurring furniture: wordmark + scantron strip
# --------------------------------------------------------------------------

def wordmark(img, colour=PAPER):
    d = ImageDraw.Draw(img)
    f = inter(21, weight=600, opsz=14)
    draw_tracked(d, (MARGIN, MARGIN), "PEER PREP ACADEMY", f, colour,
                 tracking=4.6)
    rect(d, (MARGIN, MARGIN + 40, MARGIN + 58, MARGIN + 43), GOLD)


BUBBLE_D = 30
BUBBLE_PITCH = 50
BUBBLE_TOP = H - MARGIN - BUBBLE_D          # 958
LETTER_TOP = BUBBLE_TOP - 32                # 926


def scantron(img, index):
    """A–E bubble strip, bottom-right; bubble `index` (0-based) filled gold."""
    letters = "ABCDE"
    strip_w = BUBBLE_PITCH * (len(letters) - 1) + BUBBLE_D
    x0 = W - MARGIN - strip_w
    d0 = ImageDraw.Draw(img)
    lab = inter(15, weight=600, opsz=14)

    def paint(dd, s):
        for i in range(len(letters)):
            cx = (x0 + i * BUBBLE_PITCH + BUBBLE_D / 2) * s
            cy = (BUBBLE_TOP + BUBBLE_D / 2) * s
            r = (BUBBLE_D / 2) * s
            box = (cx - r, cy - r, cx + r, cy + r)
            if i == index:
                dd.ellipse(box, fill=GOLD + (255,))
            else:
                dd.ellipse(box, outline=(112, 126, 145, 255),
                           width=int(2 * s))

    layer(img, paint)

    for i, ch in enumerate(letters):
        cx = x0 + i * BUBBLE_PITCH + BUBBLE_D / 2
        lw = d0.textlength(ch, font=lab)
        draw_tracked(d0, (cx - lw / 2, LETTER_TOP), ch, lab,
                     GOLD if i == index else (128, 141, 158))

    ink((x0, BUBBLE_TOP, x0 + strip_w, BUBBLE_TOP + BUBBLE_D))


def furniture(img, index, wordmark_colour=PAPER):
    wordmark(img, wordmark_colour)
    scantron(img, index)
    return img


# --------------------------------------------------------------------------
# cards
# --------------------------------------------------------------------------

def card1():
    """Photo card — the hook. Copy sits in a left column, clear of the face."""
    img = duotone_square("photo1.jpg", focus=(0.5, 0.0), zoom=1.13)
    img = top_scrim(img, depth=0.30, strength=150)
    img = left_scrim(img, end=0.66, strength=155)
    img = bottom_scrim(img, start=0.18, strength=255, gamma=1.22)
    d = ImageDraw.Draw(img)

    col_w = 630
    head_f = serif(72)
    gold_f = serif(60)
    head = wrap(d, "The SAT changed in 2024. We took the new one.",
                head_f, col_w)

    head_lead = 82
    block_h = len(head) * head_lead + 22 + 62
    y = CONTENT_BOTTOM - block_h

    y = draw_block(d, MARGIN, y, head, head_f, PAPER, head_lead)
    y += 18

    rule_y = y + 30
    rect(d, (MARGIN, rule_y, MARGIN + 44, rule_y + 3), GOLD)
    draw_tracked(d, (MARGIN + 68, y - 6), "Scored 1560.", gold_f, GOLD)

    return furniture(img, 0)


def card2():
    """Typographic proof card."""
    img = navy_field()
    d = ImageDraw.Draw(img)
    max_w = W - 2 * MARGIN

    eyebrow_f = inter(22, weight=600, opsz=14)
    num_f = serif(300)
    gold_f = serif(48)
    body_f = inter(30, weight=400, opsz=28)

    gold_lines = wrap(d, "SAT, taken in 2025 — plus ten AP 5s.", gold_f, max_w)
    body = wrap(d, "Adaptive modules, built-in Desmos, this year’s question "
                   "types. We teach exactly what worked for us.", body_f, 830)

    y = 252
    draw_tracked(d, (MARGIN, y), "WHY PARENTS CALL US", eyebrow_f, GOLD,
                 tracking=4.2)
    y += 78

    nb = num_f.getbbox("1560")                       # visual top/bottom
    draw_tracked(d, (MARGIN - nb[0] - 4, y - nb[1]), "1560", num_f, PAPER)
    y += (nb[3] - nb[1]) + 62

    y = draw_block(d, MARGIN, y, gold_lines, gold_f, GOLD, 62)
    y += 38

    rect(d, (MARGIN, y, MARGIN + 120, y + 2), (58, 78, 100))
    y += 44

    draw_block(d, MARGIN, y, body, body_f, SLATE, 46)

    return furniture(img, 1)


def card3():
    """Photo card — what we teach."""
    img = duotone_square("photo2.jpg", focus=(0.60, 0.46), zoom=1.02)
    img = top_scrim(img, depth=0.32, strength=160)
    img = left_scrim(img, end=0.70, strength=175)
    img = bottom_scrim(img, start=0.04, strength=255, gamma=1.15)
    d = ImageDraw.Draw(img)

    eyebrow_f = inter(22, weight=600, opsz=14)
    item_f = serif(58)
    gold_f = serif(40)

    items = ["SAT prep", "AP Calculus", "AP Chemistry",
             "AP Biology & Physics", "Algebra through Precalc"]
    gold_lines = wrap(d, "Taught by students who just took these exact exams.",
                      gold_f, 760)

    item_lead = 72
    block_h = 62 + len(items) * item_lead + 32 + len(gold_lines) * 50
    y = CONTENT_BOTTOM - block_h

    draw_tracked(d, (MARGIN, y), "WHAT WE TEACH", eyebrow_f, GOLD, tracking=4.2)
    y += 62

    dots = []
    for it in items:
        dots.append(y + 38)
        draw_tracked(d, (MARGIN + 34, y), it, item_f, PAPER)
        y += item_lead

    def paint(dd, s):
        for cy in dots:
            dd.ellipse(((MARGIN + 4) * s, (cy - 5) * s,
                        (MARGIN + 14) * s, (cy + 5) * s), fill=GOLD + (255,))
    layer(img, paint)

    y += 32
    draw_block(d, MARGIN, y, gold_lines, gold_f, GOLD, 50)

    return furniture(img, 2)


def card4():
    """Typographic card — how it works."""
    img = navy_field()
    d = ImageDraw.Draw(img)

    eyebrow_f = inter(22, weight=600, opsz=14)
    head_f = serif(54)
    sub_f = inter(27, weight=400, opsz=26)

    rows = [
        ("Structured weekly sessions",
         "A clear plan for the whole semester."),
        ("A written progress report after every session",
         "You always know what your kid worked on."),
        ("Evenings, weekends, your schedule",
         "In person around the Bay, or online."),
    ]

    y = 250
    draw_tracked(d, (MARGIN, y), "HOW IT WORKS", eyebrow_f, GOLD, tracking=4.2)
    y += 86

    max_w = W - 2 * MARGIN - 48
    dots = []
    for i, (head, sub) in enumerate(rows):
        if i:
            rect(d, (MARGIN, y, W - MARGIN, y + 1), (44, 62, 84))
            y += 48

        dots.append(y + 34)
        hl = wrap(d, head, head_f, max_w)
        yy = draw_block(d, MARGIN + 44, y, hl, head_f, PAPER, 62)
        yy += 10
        yy = draw_block(d, MARGIN + 44, yy, wrap(d, sub, sub_f, max_w),
                        sub_f, SLATE, 40)
        y = yy + 42

    def paint(dd, s):
        for cy in dots:
            dd.ellipse((MARGIN * s, (cy - 7) * s,
                        (MARGIN + 14) * s, (cy + 7) * s), fill=GOLD + (255,))
    layer(img, paint)

    return furniture(img, 3)


def card5():
    """CTA card."""
    img = navy_field()
    d = ImageDraw.Draw(img)
    max_w = W - 2 * MARGIN

    eyebrow_f = inter(22, weight=600, opsz=14)
    head_f = serif(104)
    gold_f = serif(46)
    pill_f = inter(34, weight=600, opsz=32)

    head_lines = wrap(d, "Free 20-minute consult.", head_f, max_w)
    gold_lines = wrap(d, "150+ point guarantee on our 12-session package.",
                      gold_f, 820)

    pill_h = 96
    block_h = (88 + len(head_lines) * 112 + 30 + len(gold_lines) * 58
               + 72 + pill_h)
    y = (H - block_h) // 2 + 26

    draw_tracked(d, (MARGIN, y), "LIMITED SPOTS EACH SEMESTER", eyebrow_f,
                 GOLD, tracking=4.2)
    y += 88

    y = draw_block(d, MARGIN, y, head_lines, head_f, PAPER, 112)
    y += 26
    y = draw_block(d, MARGIN, y, gold_lines, gold_f, GOLD, 58)
    y += 68

    label = "peerprepacademy.com"
    pill_w = int(d.textlength(label, font=pill_f) + 84)
    pill_y = y

    def paint(dd, s):
        dd.rounded_rectangle((MARGIN * s, pill_y * s,
                              (MARGIN + pill_w) * s, (pill_y + pill_h) * s),
                             radius=(pill_h / 2) * s, fill=PAPER + (255,))
    layer(img, paint)
    ink((MARGIN, pill_y, MARGIN + pill_w, pill_y + pill_h))

    bb = pill_f.getbbox(label)
    d.text((MARGIN + 42, pill_y + (pill_h - (bb[3] - bb[1])) / 2 - bb[1]),
           label, font=pill_f, fill=NAVY)

    return furniture(img, 4)


# --------------------------------------------------------------------------
# checks + build
# --------------------------------------------------------------------------

def check_safe_area(name):
    """Assert nothing drawn lands within SAFE px of any edge."""
    bad = [b for b in INK
           if b[0] < SAFE or b[1] < SAFE or b[2] > W - SAFE or b[3] > H - SAFE]
    if bad:
        raise AssertionError(f"{name}: {len(bad)} mark(s) inside the "
                             f"{SAFE}px safe band: {bad[:4]}")
    x0 = min(b[0] for b in INK)
    y0 = min(b[1] for b in INK)
    x1 = max(b[2] for b in INK)
    y1 = max(b[3] for b in INK)
    print(f"  ink bounds {x0:.0f},{y0:.0f} -> {x1:.0f},{y1:.0f} "
          f"(min edge gap {min(x0, y0, W - x1, H - y1):.0f}px)")


def preview_strip(paths, tile=640, gutter=28, pad=28):
    n = len(paths)
    sheet = Image.new("RGB", (pad * 2 + tile * n + gutter * (n - 1),
                              pad * 2 + tile), (7, 15, 25))
    for i, p in enumerate(paths):
        sheet.paste(Image.open(p).resize((tile, tile), Image.LANCZOS),
                    (pad + i * (tile + gutter), pad))
    return sheet


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    paths = []
    for i, fn in enumerate([card1, card2, card3, card4, card5], start=1):
        INK.clear()
        img = fn()
        assert img.size == (W, H), img.size
        p = os.path.join(OUT_DIR, f"card{i}.png")
        img.save(p, "PNG")
        paths.append(p)
        print(f"wrote {p} {img.size}")
        check_safe_area(f"card{i}")

    strip = preview_strip(paths)
    sp = os.path.join(OUT_DIR, "preview_strip.png")
    strip.save(sp, "PNG")
    print("wrote", sp, strip.size)


if __name__ == "__main__":
    main()
