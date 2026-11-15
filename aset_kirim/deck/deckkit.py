"""deckkit: pixel-grid slide helpers on top of python-pptx.

The canvas is 1920 x 1080 "px" (16:9). Every size you pass is in px, including font sizes
(1 px = 0.75 pt), so you can reason about a slide like a web page.

Everything is drawn as native, editable shapes, text boxes and pictures. That is what lets the
PPTX import cleanly into Canva / Google Slides / Keynote: no images of text, no native charts
(Canva drops per-point colours and number formats), no SmartArt.

Usage:
    import deckkit as dk
    dk.set_theme(brand="acme", accent="#0F766E", assets="assets")
    prs = dk.new_deck()
    s = dk.add_slide(prs)
    dk.title_block(s, "Action title that states the takeaway", page=2)
    dk.text(s, 80, 210, 900, 60, ["Plain run ", ("accent run", {"color": dk.T["accent"], "bold": True})], size=28)
    prs.save("deck.pptx")
"""
import math
import os
import sys

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

for _stream in (sys.stdout, sys.stderr):  # Windows consoles default to cp1252; slide text has → · “ ”
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ----------------------------------------------------------------------------- theme
# One ink colour, one accent, greys, and a red that is only for flagged values. One dark
# palette for a single hero slide. Change these per brand with set_theme(); keep the roles.
T = dict(
    font="Inter",            # maps 1:1 in Canva. Plus Jakarta Sans / Spectral do NOT (fall back to Arimo).
    mono="Roboto Mono",
    ink="#16224A",           # titles and body text
    accent="#4338CA",        # the one accent colour: key numbers, highlights, active states
    muted="#6B7280",         # secondary text
    faint="#A3A8B4",         # footnotes, page numbers, "before" bars
    line="#E3E5EA",          # rules and box borders
    flag="#C8102E",          # only for flagged / wrong / missing values
    tint="#EEF0FF",          # one light accent tint, used sparingly (one strip or blob per slide)
    tint2="#DCDFFF",
    dark="#1E1B4B",          # background of the one dark hero slide
    dark2="#2B2770",         # cards on the dark slide
    dark_text="#C7C9FF",     # secondary text on the dark slide
    green="#15803D", green_bg="#E7F6EC", amber="#B45309", amber_bg="#FFF4E0",
    white="#FFFFFF",
    brand="",                # brand word shown next to the logo in title_block
    logo=None,               # logo image file (square). None draws a lettered square.
    assets=".",              # folder for images; icons live in <assets>/icons/<name>-<color>.png
)

W, H = 1920, 1080
MARGIN = 80


def set_theme(**kw):
    T.update(kw)


def E(v):
    return Emu(int(round(v * 9525)))


def rgb(h):
    return RGBColor.from_string(h.lstrip("#"))


def _c(key_or_hex):
    """Accept a theme key ('accent') or a hex colour ('#4338CA')."""
    if key_or_hex is None:
        return None
    return T.get(key_or_hex, key_or_hex) if not str(key_or_hex).startswith("#") else key_or_hex


def asset(path):
    return path if os.path.isabs(path) else os.path.join(T["assets"], path)


# ----------------------------------------------------------------------------- deck / slide
def new_deck():
    prs = Presentation()
    prs.slide_width, prs.slide_height = E(W), E(H)
    return prs


def add_slide(prs, bg="white"):
    s = prs.slides.add_slide(prs.slide_layouts[6])  # blank layout
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = rgb(_c(bg))
    return s


def notes(s, body):
    """Speaker notes. Canva imports them, so put the timed cue card here."""
    s.notes_slide.notes_text_frame.text = body
    return s


# ----------------------------------------------------------------------------- text
def _runs(p, runs, size, color, bold, font, italic):
    for item in runs:
        t, o = (item, {}) if isinstance(item, str) else item
        r = p.add_run()
        r.text = t
        f = r.font
        f.name = o.get("font", font)
        f.size = Pt(o.get("size", size) * 0.75)
        f.bold = o.get("bold", bold)
        f.italic = o.get("italic", italic)
        f.color.rgb = rgb(_c(o.get("color", color)))
        if o.get("spacing") is not None:
            r._r.get_or_add_rPr().set("spc", str(int(o["spacing"] * 100)))


def fill_tf(tf, content, size=22, color="ink", bold=False, align="l", anchor="t", lh=None, italic=False,
            spacing=None, para_space=0, font=None, margins=(0, 0, 0, 0)):
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left, tf.margin_top, tf.margin_right, tf.margin_bottom = [E(m) for m in margins]
    tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}[anchor]
    lines = content if isinstance(content, list) else str(content).split("\n")
    # A flat list of runs (str/tuple mix) on one line is the common case: ["a ", ("b", {...})]
    if isinstance(content, list) and any(isinstance(x, tuple) for x in content):
        lines = [content]
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[align]
        if lh:
            p.line_spacing = lh
        if para_space and i > 0:
            p.space_before = Pt(para_space * 0.75)
        runs = ln if isinstance(ln, list) else [ln]
        if spacing is not None:
            runs = [(r, {"spacing": spacing}) if isinstance(r, str) else (r[0], {**r[1], "spacing": spacing})
                    for r in runs]
        _runs(p, runs, size, color, bold, font or T["font"], italic)


def text(s, x, y, w, h, content, size=22, color="ink", bold=False, align="l", anchor="t", lh=None,
         italic=False, spacing=None, para_space=0, font=None):
    """Text box. content: 'str\\nwith newlines' | [line, line] | one line of runs ['a', ('b', {'bold': True})].

    Canva tip: prefer anchor 't' or 'm' and give boxes ~10% spare width/height (Inter renders wider in
    Canva). Small bottom-anchored boxes can disappear on import.
    """
    tb = s.shapes.add_textbox(E(x), E(y), E(w), E(h))
    fill_tf(tb.text_frame, content, size, color, bold, align, anchor, lh, italic, spacing, para_space, font)
    return tb


# ----------------------------------------------------------------------------- shapes
def rect(s, x, y, w, h, fill=None, line=None, lw=1.5, r=0, shape=None, label=None, size=20, color="ink",
         bold=False, align="c", anchor="m", pad=(12, 6, 12, 6), lh=None, spacing=None, dash=False):
    st = shape or (MSO_SHAPE.ROUNDED_RECTANGLE if r else MSO_SHAPE.RECTANGLE)
    shp = s.shapes.add_shape(st, E(x), E(y), E(w), E(h))
    if r and st == MSO_SHAPE.ROUNDED_RECTANGLE:
        shp.adjustments[0] = min(0.5, r / max(1, min(w, h)))
    if fill:
        shp.fill.solid()
        shp.fill.fore_color.rgb = rgb(_c(fill))
    else:
        shp.fill.background()
    if line:
        shp.line.color.rgb = rgb(_c(line))
        shp.line.width = Pt(lw * 0.75)
        if dash:
            from pptx.enum.dml import MSO_LINE
            shp.line.dash_style = MSO_LINE.DASH
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    if label is not None:
        fill_tf(shp.text_frame, label, size, color, bold, align, anchor, lh, spacing=spacing, margins=pad)
    return shp


def oval(s, x, y, d, fill=None, line=None, lw=1.5, label=None, size=20, color="white", bold=True):
    return rect(s, x, y, d, d, fill, line, lw, shape=MSO_SHAPE.OVAL, label=label, size=size, color=color,
                bold=bold, pad=(0, 0, 0, 0))


def hline(s, x, y, w, color="line", t=2):
    """A rule. Drawn as a thin rectangle (connectors import less reliably)."""
    return rect(s, x, y, w, t, fill=color)


def line(s, x1, y1, x2, y2, color="line", w=2, arrow=False, dash=False):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, E(x1), E(y1), E(x2), E(y2))
    c.line.color.rgb = rgb(_c(color))
    c.line.width = Pt(w * 0.75)
    if dash:
        from pptx.enum.dml import MSO_LINE
        c.line.dash_style = MSO_LINE.DASH
    if arrow:
        tail = etree.SubElement(c.line._get_or_add_ln(), qn("a:tailEnd"))
        tail.set("type", "triangle")
        tail.set("w", "med")
        tail.set("len", "med")
    return c


def arrow_r(s, x, y, w=44, h=30, color="accent"):
    return rect(s, x, y, w, h, fill=color, shape=MSO_SHAPE.RIGHT_ARROW)


def box(s, x, y, w, h, r=14, lw=1.5, line_color="line", fill="white"):
    """The default container: white fill, hairline border, small radius. No shadow, no gradient."""
    return rect(s, x, y, w, h, fill=fill, line=line_color, lw=lw, r=r)


def card(s, x, y, w, h, fill="white", line="line", r=18, shadow="#E6E8F5", lw=1.5):
    """Floating card with a soft offset shadow (used for overlay cards on the cover mockup)."""
    if shadow:
        rect(s, x + 4, y + 6, w, h, fill=shadow, r=r)
    return rect(s, x, y, w, h, fill=fill, line=line, r=r, lw=lw)


def chip(s, x, y, label, fill="tint", color="accent", h=34, size=15, w=None, line=None, bold=True, spacing=0.4):
    if w is None:
        w = len(label) * size * 0.74 + 34
    rect(s, x, y, w, h, fill=fill, line=line, r=h / 2, label=label, size=size, color=color, bold=bold,
         pad=(10, 0, 10, 0), spacing=spacing)
    return w


def num_dot(s, n, x, y, d=46, fill="accent", color="white", size=20):
    oval(s, x, y, d, fill=fill, label=str(n), size=size, color=color)


def kv(s, x, y, w, k, v, size=22, vcolor="ink", kcolor="muted", bold_v=True):
    """Key on the left, value right-aligned: receipts, quote lines, spec rows."""
    text(s, x, y, w * 0.62, size * 1.6, k, size=size, color=kcolor, anchor="m")
    text(s, x + w * 0.38, y, w * 0.62, size * 1.6, v, size=size, color=vcolor, bold=bold_v, align="r", anchor="m")


# ----------------------------------------------------------------------------- pictures & icons
def pic(s, path, x, y, w=None, h=None):
    """Picture; if the file is missing, draws a labelled placeholder so drafts still build."""
    full = asset(path)
    if not os.path.exists(full):
        print(f"[deckkit] missing image, placeholder used: {full}", file=sys.stderr)
        ww, hh = w or h or 200, h or w or 200
        return rect(s, x, y, ww, hh, fill="#F1F2F5", line="line", r=12, label=f"[{os.path.basename(path)}]",
                    size=16, color="faint")
    return s.shapes.add_picture(full, E(x), E(y), E(w) if w else None, E(h) if h else None)


def pic_cover(s, path, x, y, w, h, focus=(0.5, 0.5)):
    """Picture cropped to fill the box (CSS object-fit: cover)."""
    full = asset(path)
    if not os.path.exists(full):
        return pic(s, path, x, y, w, h)
    from PIL import Image
    iw, ih = Image.open(full).size
    p = s.shapes.add_picture(full, E(x), E(y), E(w), E(h))
    box_ar, img_ar = w / h, iw / ih
    if img_ar > box_ar:
        extra = 1 - box_ar / img_ar
        p.crop_left, p.crop_right = extra * focus[0], extra * (1 - focus[0])
    else:
        extra = 1 - img_ar / box_ar
        p.crop_top, p.crop_bottom = extra * focus[1], extra * (1 - focus[1])
    return p


def icon(s, name, color, x, y, d=32):
    """Icon PNG rendered by make_assets.py icons: <assets>/icons/<name>-<color>.png."""
    return pic(s, os.path.join("icons", f"{name}-{color}.png"), x, y, d, d)


def icon_badge(s, name, x, y, d=64, bg="tint", color="accent", ratio=0.5):
    """Coloured icon on a light circle."""
    oval(s, x, y, d, fill=bg)
    i = d * ratio
    icon(s, name, color, x + (d - i) / 2, y + (d - i) / 2, i)


def glyph(s, name, x, y, d=60, fill="ink", ratio=0.5):
    """White icon on a dark circle (row markers)."""
    oval(s, x, y, d, fill=fill)
    g = d * ratio
    icon(s, name, "white", x + (d - g) / 2, y + (d - g) / 2, g)


def logo(s, x, y, d=36, dark=False, word_size=None):
    """Logo mark + brand word."""
    if T["logo"] and os.path.exists(asset(T["logo"])):
        pic(s, T["logo"], x, y, d, d)
    else:
        rect(s, x, y, d, d, fill="accent", r=d * 0.28, label=(T["brand"][:1] or "•").upper(), size=d * 0.55,
             color="white", bold=True, pad=(0, 0, 0, 0))
    if T["brand"]:
        ws = word_size or d * 0.72
        text(s, x + d + 8, y - d * 0.1, ws * len(T["brand"]) * 0.7 + 20, d * 1.2, T["brand"], size=ws,
             color="white" if dark else "ink", bold=True, anchor="m")


# ----------------------------------------------------------------------------- slide furniture
def title_block(s, title, page=None, size=46):
    """Action title (a full-sentence takeaway), bottom-aligned above a rule, logo top-right, page number.

    Title area: x 80-1660, y 40-168; rule at y 180. Body starts at y ~200. Keep titles to 2 lines:
    size 46 fits ~70 characters per line at this width; use size=42 for longer titles.
    """
    text(s, 80, 40, 1580, 128, title, size=size, color="ink", bold=True, anchor="b", lh=1.05)
    hline(s, 80, 180, 1760)
    if T["brand"] or T["logo"]:
        logo(s, 1736 if T["brand"] else 1804, 56, 36)
    if page is not None:
        text(s, 1760, 1030, 80, 26, str(page), size=16, color="faint", align="r")


def kicker(s, label, x=80, y=46, dark=False):
    text(s, x, y, 900, 30, label.upper(), size=18, color="dark_text" if dark else "accent", bold=True, spacing=2)


def footnote(s, body, y=1004, w=1500):
    """Sources and honesty labels ('Seeded demo prices', 'proposed, not traction'). Small but present."""
    text(s, 80, y, w, 28, body, size=16, color="faint")


def team(s, x, y, members, d=172, gap=100, name_size=22, dark=False):
    """members: [(photo, name, role)]. Photos should already be round PNGs (make_assets.py avatar)."""
    for i, (img, name, role) in enumerate(members):
        cx = x + i * (d + gap)
        oval(s, cx - 4, y - 4, d + 8, fill="white", line="line", lw=2)
        if img and os.path.exists(asset(img)):
            pic(s, img, cx, y, d, d)
        else:
            initials = "".join(p[0] for p in name.split()[:2]).upper()
            oval(s, cx, y, d, fill="tint", label=initials, size=d * 0.32, color="accent")
        text(s, cx - 50, y + d + 12, d + 100, 60, name, size=name_size, bold=True, color="white" if dark else "ink",
             align="c", lh=1.05)
        if role:
            text(s, cx - 50, y + d + 12 + name_size * 2.4, d + 100, 30, role, size=name_size - 4, color="muted",
                 align="c")


# ----------------------------------------------------------------------------- charts (shape-drawn)
def columns_chart(s, x, y, w, h, cats, vals, labels, colors, max_v, label_size=34, cat_size=20, gap=0.45):
    """Column chart drawn with rectangles: looks identical in PowerPoint and Canva."""
    n = len(vals)
    top, bottom = y + 50, y + h - 44
    ph, slot = bottom - top, w / n
    bw = slot * (1 - gap)
    for k in (0.33, 0.66):
        rect(s, x, bottom - ph * k, w, 1, fill="#EEF0F3")
    for i, v in enumerate(vals):
        bh = max(3, v / max_v * ph)
        bx = x + i * slot + (slot - bw) / 2
        rect(s, bx, bottom - bh, bw, bh, fill=colors[i])
        text(s, bx - 40, bottom - bh - 46, bw + 80, 40, labels[i], size=label_size, bold=True, color="ink", align="c")
        text(s, x + i * slot, bottom + 8, slot, 34, cats[i], size=cat_size, color="muted", align="c")
    rect(s, x, bottom, w, 2, fill="#C9CDD6")


def waterfall(s, x, y, w, h, cats, bases, deltas, labels, colors, max_v, label_size=22, cat_size=18):
    """Bridge chart (quote -> hidden extras -> final bill). bases[i] is where bar i starts."""
    n = len(deltas)
    top, bottom = y + 10, y + h - 52
    ph, slot = bottom - top, w / n
    bw = slot * 0.6
    for k in (0.33, 0.66):
        rect(s, x, bottom - ph * k, w, 1, fill="#EEF0F3")
    for i in range(n):
        y_top = bottom - (bases[i] + deltas[i]) / max_v * ph
        bh = deltas[i] / max_v * ph
        bx = x + i * slot + (slot - bw) / 2
        rect(s, bx, y_top, bw, bh, fill=colors[i])
        inside = bh > 44
        text(s, bx - 30, (y_top + 8) if inside else (y_top - 34), bw + 60, 30, labels[i], size=label_size, bold=True,
             color="white" if inside else "ink", align="c")
        text(s, x + i * slot, bottom + 8, slot, 44, cats[i], size=cat_size, color="muted", align="c", lh=1.0)
    rect(s, x, bottom, w, 2, fill="#C9CDD6")


def paired_bars(s, x, y, w, rows, max_v, label_w=300, row_h=70, unknown_text="unknown, not ranked"):
    """Before/after horizontal bars per row: rows = [(name, before, before_label, after|None, after_label, best)]."""
    bar_w = w - label_w - 180
    for i, (name, a, alab, b, blab, best) in enumerate(rows):
        yy = y + i * row_h
        text(s, x, yy, label_w - 10, row_h - 6, name, size=21, color="ink", anchor="m")
        rect(s, x + label_w, yy + 6, a / max_v * bar_w, row_h / 2 - 8, fill="faint")
        text(s, x + label_w + a / max_v * bar_w + 8, yy + 2, 200, row_h / 2 - 4, alab, size=18, color="muted", anchor="m")
        if b is None:
            text(s, x + label_w, yy + row_h / 2 - 4, 460, row_h / 2, unknown_text, size=20, bold=True, color="flag",
                 anchor="m")
        else:
            rect(s, x + label_w, yy + row_h / 2, b / max_v * bar_w, row_h / 2 - 8, fill="accent" if best else "ink")
            text(s, x + label_w + b / max_v * bar_w + 8, yy + row_h / 2 - 4, 200, row_h / 2, blab, size=20, bold=True,
                 color="ink", anchor="m")


# ----------------------------------------------------------------------------- QA
def text_width(s, size, bold=False):
    """Approximate rendered width in px of a string in Inter (calibrated against Canva renders)."""
    em = 0.0
    for ch in s:
        if ch == " ":
            em += 0.26
        elif ch in "ijlrtf.,:;'!|()[]":
            em += 0.30
        elif ch.isdigit():
            em += 0.56
        elif ch.isupper():
            em += 0.66
        elif ch in "mwMW@%":
            em += 0.80
        else:
            em += 0.50
    return em * size * (1.03 if bold else 1.0)


def fit_report(prs, slack=1.0, min_size=15):
    """Heuristic overflow and tiny-text check. Returns a list of warnings; run before rendering.

    It wraps each paragraph word by word with text_width() and compares the needed height with the box.
    Approximate: treat a warning as 'look at this box in the render', not as truth.
    """
    out = []
    for si, slide in enumerate(prs.slides, 1):
        for shp in slide.shapes:
            if not shp.has_text_frame or not shp.text_frame.text.strip():
                continue
            bw, bh = shp.width / 9525, shp.height / 9525
            need, last = 0.0, (0, 1.2)
            for p in shp.text_frame.paragraphs:
                lh = p.line_spacing if isinstance(p.line_spacing, float) else 1.2
                if not p.runs:
                    need += 20 * lh
                    continue
                size = max((r.font.size.pt / 0.75 if r.font.size else 20) for r in p.runs)
                # word-by-word wrap across runs
                avail, lines, cur = max(1, bw - 4), 1, 0.0
                for r in p.runs:
                    rs = r.font.size.pt / 0.75 if r.font.size else 20
                    for k, word in enumerate(r.text.split(" ")):
                        ww = text_width(word + " ", rs, bool(r.font.bold))
                        if cur + ww - text_width(" ", rs) > avail and cur > 0:
                            lines, cur = lines + 1, ww
                        else:
                            cur += ww
                need += lines * size * lh
                last = (size, lh)
                if size < min_size:
                    out.append(f"slide {si}: {size:.0f}px text is too small to read: {p.runs[0].text[:40]!r}")
            need = (need - last[0] * (last[1] - 1.0)) * 1.02  # the last line needs ~1 em, not a full line box
            if need > bh * slack + 4:
                out.append(f"slide {si}: may overflow ({need:.0f}px needed, box {bh:.0f}px): "
                           f"{shp.text_frame.text[:50]!r}")
    return out


SLOP_WORDS = ["revolutioniz", "revolutionis", "seamless", "empower", "unlock", "leverag", "cutting-edge",
              "game-chang", "game chang", "next-gen", "next generation", "robust", "synergy", "transformative",
              "supercharg", "effortless", "world-class", "state-of-the-art", "best-in-class", "harness the power",
              "in today's", "delve", "elevate", "unleash", "reimagin", "one-stop", "paradigm"]
TOPIC_TITLES = {"problem", "the problem", "solution", "our solution", "the solution", "market", "market size",
                "architecture", "team", "our team", "demo", "business model", "roadmap", "agenda", "overview",
                "introduction", "thank you", "conclusion", "features", "competition", "traction", "vision"}


def _is_emoji(ch):
    o = ord(ch)
    return 0x1F300 <= o <= 0x1FAFF or 0x2600 <= o <= 0x27BF or 0x1F000 <= o <= 0x1F2FF


def _hue_bucket(hexcol):
    import colorsys
    r, g, b = [int(hexcol[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return None if s < 0.35 or v < 0.3 else round(h * 12) % 12


def slop_report(prs, appendix_from=None, max_words=45, max_hues=3):
    """Catch the machine-checkable AI-slop tells. Returns warnings (see references/anti-slop.md).

    Checks: hype words, emoji, topic-only titles, gradient fills, >2 fonts, too many vivid hues on one
    slide (colour without meaning), and word walls on main slides. appendix_from: first appendix slide no.
    """
    from pptx.enum.dml import MSO_FILL
    out, fonts = [], set()
    for si, slide in enumerate(prs.slides, 1):
        main = appendix_from is None or si < appendix_from
        hues = set()
        for shp in slide.shapes:
            try:
                if shp.fill.type == MSO_FILL.GRADIENT:
                    out.append(f"slide {si}: gradient fill. Use a flat colour.")
                elif shp.fill.type == MSO_FILL.SOLID:
                    b = _hue_bucket(str(shp.fill.fore_color.rgb))
                    if b is not None:
                        hues.add(b)
            except (AttributeError, TypeError, ValueError):
                pass
            if not shp.has_text_frame:
                continue
            body = shp.text_frame.text
            low = body.lower()
            for w in SLOP_WORDS:
                if w in low:
                    out.append(f"slide {si}: hype word '{w}' in {body[:50]!r}. Say what it does, with a number.")
            if any(_is_emoji(ch) for ch in body):
                out.append(f"slide {si}: emoji in {body[:40]!r}. Use a drawn icon or nothing.")
            big = 0
            for p in shp.text_frame.paragraphs:
                for r in p.runs:
                    if r.font.name:
                        fonts.add(r.font.name)
                    try:
                        b = _hue_bucket(str(r.font.color.rgb))
                        if b is not None:
                            hues.add(b)
                    except (AttributeError, TypeError, ValueError):
                        pass
                    if r.font.size and r.font.size.pt / 0.75 >= 20:
                        big += len(r.text.split())
            # title box from title_block(): x 80, y 40, w 1580
            if abs(shp.left / 9525 - 80) < 2 and abs(shp.top / 9525 - 40) < 2 and abs(shp.width / 9525 - 1580) < 4:
                t = body.strip().rstrip(".").lower()
                if t in TOPIC_TITLES or (len(t.split()) <= 2 and not t.endswith("?")):
                    out.append(f"slide {si}: topic title {body.strip()!r}. Write the takeaway as a sentence.")
            if main and big > max_words:
                out.append(f"slide {si}: {big} words in one box. Split into rows or move detail to the appendix.")
        if len(hues) > max_hues:
            out.append(f"slide {si}: {len(hues)} vivid hues. Keep ink + accent + flag; colour must mean something.")
    if len(fonts) > 2:
        out.append(f"deck uses {len(fonts)} fonts ({', '.join(sorted(fonts))}). Use Inter (plus one mono at most).")
    return out


if __name__ == "__main__":  # quick self-check
    prs = new_deck()
    s = add_slide(prs)
    title_block(s, "deckkit self-check: a two-line action title sits above the rule", page=1)
    columns_chart(s, 80, 220, 600, 500, ["2021", "2024"], [1.3, 5.3], ["1.3M", "5.3M"], ["faint", "accent"], 6)
    print("\n".join(fit_report(prs)) or "fit ok")
