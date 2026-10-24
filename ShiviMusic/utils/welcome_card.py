# Welcome card (Krishna theme) - template + user photo + Name / ID / Username
import os
import struct
import unicodedata

from PIL import Image, ImageDraw, ImageFont, ImageOps

try:                                   # Pillow 9.5.0 rounded_rectangle crash guard
    from ShiviMusic.utils import pil_compat  # noqa: F401
except Exception:
    pass

_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
TEMPLATE = os.path.join(_ASSETS, "welcome_template.png")
FONT_PATH = os.path.join(_ASSETS, "font.ttf")        # Poppins (Latin + Devanagari)
# used per character when Poppins has no glyph (fancy names: small caps, greek, ˹ ˼ ♡ ...)
FALLBACK_PATHS = (
    os.path.join(_ASSETS, "fallback_bold.ttf"),      # DejaVu Sans Bold
    os.path.join(_ASSETS, "fallback_symbols.ttf"),   # FreeSans (brackets, dingbats, IPA ...)
)

SS = 3                                               # supersampling for the round photo
PHOTO_CENTER = (1302, 475)
PHOTO_RADIUS = 262

# text slots inside the pills: (x, vertical centre, max width)
SLOT_NAME = (293, 437, 590)
SLOT_ID   = (233, 590, 400)
SLOT_USER = (373, 741, 515)
FONT_SIZE = 42

_CMAP_CACHE = {}


def _read_cmap(path):
    """Set of code points a .ttf really contains (own parser - no fontTools needed).
    Render-and-compare tricks gave 'tofu' boxes on some Pillow versions."""
    if path in _CMAP_CACHE:
        return _CMAP_CACHE[path]
    cps = set()
    try:
        with open(path, "rb") as fh:
            d = fh.read()
        num = struct.unpack(">H", d[4:6])[0]
        cmap_off = None
        for i in range(num):
            tag, _, off, _ = struct.unpack(">4sIII", d[12 + 16 * i:28 + 16 * i])
            if tag == b"cmap":
                cmap_off = off
                break
        n = struct.unpack(">H", d[cmap_off + 2:cmap_off + 4])[0]
        for i in range(n):
            _, _, soff = struct.unpack(">HHI", d[cmap_off + 4 + 8 * i:cmap_off + 12 + 8 * i])
            o = cmap_off + soff
            fmt = struct.unpack(">H", d[o:o + 2])[0]
            if fmt == 4:
                segx2 = struct.unpack(">H", d[o + 6:o + 8])[0]
                seg = segx2 // 2
                ends = struct.unpack(f">{seg}H", d[o + 14:o + 14 + segx2])
                starts = struct.unpack(f">{seg}H", d[o + 16 + segx2:o + 16 + 2 * segx2])
                for st, en in zip(starts, ends):
                    if st != 0xFFFF:
                        cps.update(range(st, en + 1))
            elif fmt == 12:
                ng = struct.unpack(">I", d[o + 12:o + 16])[0]
                for g in range(ng):
                    st, en, _ = struct.unpack(">III", d[o + 16 + 12 * g:o + 28 + 12 * g])
                    cps.update(range(st, en + 1))
        cps.discard(0)
    except Exception:
        cps = set()
    _CMAP_CACHE[path] = cps
    return cps


def _chain(size=None):
    """[(font_object, code point set), ...] primary first, then fallbacks."""
    size = size or FONT_SIZE
    out = []
    for path in (FONT_PATH,) + FALLBACK_PATHS:
        if not os.path.exists(path):
            continue
        key = (path, size)
        f = _FONT_CACHE.get(key)
        if f is None:
            try:
                f = _FONT_CACHE[key] = ImageFont.truetype(path, size)
            except Exception:
                continue
        out.append((f, _read_cmap(path)))
    return out


def _pick(ch, chain):
    for f, cps in chain:
        if ord(ch) in cps:
            return f
    return None


def layout(text, size=None):
    """text -> [(char, font)] where every char is drawable (fancy unicode kept when any bundled
    font has it, else a plain lookalike, else dropped). Emoji / unknown symbols are skipped."""
    chain = _chain(size)
    out = []
    for ch in str(text or ""):
        if ch in "\u200b\u200c\u200d\ufe0f\u200e\u200f":
            continue
        if ch.isspace():
            if out and out[-1][0] != " ":
                out.append((" ", chain[0][0]))
            continue
        f = _pick(ch, chain)
        if f:
            out.append((ch, f))
            continue
        alts = [_LOOK[ch]] if ch in _LOOK else []
        alts += list(unicodedata.normalize("NFKD", ch))
        for sub in alts:
            if unicodedata.combining(sub) or sub.isspace():
                continue
            f = _pick(sub, chain)
            if f:
                out.append((sub, f))
    while out and out[-1][0] == " ":
        out.pop()
    return out


def clean_text(text, font=None):
    return "".join(c for c, _ in layout(text))


# styled-name lookalikes (small caps, greek, african letters) -> plain letters
_LOOK = {}
_LOOK.update(dict(zip("ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡʏᴢ", "ABCDEFGHIJKLMNOPQRSTUVWYZ")))
_LOOK.update({
    "ɑ": "a", "ɗ": "d", "η": "n", "ɱ": "m", "σ": "o", "ᴧ": "A", "є": "e", "ʋ": "v", "ɳ": "n",
    "ɾ": "r", "ƙ": "k", "ʂ": "s", "ɦ": "h", "ʝ": "j", "ɠ": "g", "ɓ": "b", "ƈ": "c", "ʈ": "t",
    "α": "a", "ι": "i", "ν": "v", "υ": "u", "ρ": "p", "τ": "t", "κ": "k", "ε": "e", "ο": "o",
    "м": "m", "ɛ": "e", "ʌ": "v", "ɔ": "c", "ᴎ": "N", "ᴙ": "R", "ꭙ": "x", "ɯ": "w", "ʍ": "w",
})


_FONT_CACHE = {}


def _font(size=FONT_SIZE):
    return _chain(size)[0][0]


def _runs(items):
    """Group neighbouring chars that use the same font -> [(text, font)]; keeps Hindi matras with
    their base letter and keeps kerning inside a run."""
    out = []
    for c, f in items:
        if out and out[-1][1] is f:
            out[-1][0] += c
        else:
            out.append([c, f])
    return out


def _width(items):
    return sum(f.getlength(t) for t, f in _runs(items))


def _fit(items, max_w):
    """Trim [(char, font)] to max_w, adding '...' when cut."""
    if _width(items) <= max_w:
        return items
    dots = [(".", items[0][1])] * 3 if items else []
    for i in range(len(items) - 1, 0, -1):
        cand = items[:i]
        while cand and cand[-1][0] == " ":
            cand = cand[:-1]
        cand = cand + dots
        if _width(cand) <= max_w:
            return cand
    return dots


def _draw_items(draw, x, mid_y, items, fill):
    """Draw char by char (each with its own font) on a shared baseline, centred on mid_y."""
    if not items:
        return
    asc, desc = items[0][1].getmetrics()
    base = mid_y + (asc - desc) / 2
    for t, f in _runs(items):
        draw.text((x, base), t, font=f, fill=fill, anchor="ls")
        x += f.getlength(t)


def _round_photo(img, radius):
    size = radius * 2
    img = ImageOps.fit(img.convert("RGB"), (size, size), Image.LANCZOS)
    mask = Image.new("L", (size * SS, size * SS), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size * SS - 1, size * SS - 1], fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0))
    out.putalpha(mask)
    return out


def _avatar(initial):
    """Fallback when the user has no profile photo."""
    size = PHOTO_RADIUS * 2
    img = Image.new("RGB", (size, size))
    d = ImageDraw.Draw(img)
    for y in range(size):                              # simple vertical gradient
        t = y / size
        d.line([(0, y), (size, y)], fill=(int(40 + 60 * t), int(90 + 70 * t), int(200 - 30 * t)))
    f = _font(260)
    d.text((size / 2, size / 2), (initial or "?")[:1].upper(), font=f, fill=(255, 255, 255), anchor="mm")
    return img


def welcomepic(photo_path, name, user_id, username, out_path):
    """Render the welcome card to out_path and return it. Never raises on bad text sizes."""
    bg = Image.open(TEMPLATE).convert("RGBA")

    # ---- photo ----
    photo = None
    if photo_path and os.path.exists(photo_path):
        try:
            photo = Image.open(photo_path)
            photo.load()
        except Exception:
            photo = None
    name_items = layout(name) or layout("User")
    if photo is None:
        photo = _avatar(name_items[0][0])
    rp = _round_photo(photo, PHOTO_RADIUS)
    cx, cy = PHOTO_CENTER
    bg.paste(rp, (cx - PHOTO_RADIUS, cy - PHOTO_RADIUS), rp)

    # ---- text ----
    items = (
        (SLOT_NAME, name_items),
        (SLOT_ID, layout(str(user_id))),
        (SLOT_USER, layout(str(username or "").lstrip("@")) or layout("No Username")),
    )
    draw = ImageDraw.Draw(bg, "RGBA")
    for (x, mid, max_w), its in items:
        its = _fit(its, max_w)
        _draw_items(draw, x + 1, mid + 2, its, (0, 50, 130, 70))        # soft shadow
        _draw_items(draw, x, mid, its, (255, 255, 255, 255))

    bg.convert("RGB").save(out_path, "PNG")
    return out_path
