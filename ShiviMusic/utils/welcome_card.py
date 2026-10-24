# Welcome card (Krishna theme) - template + user photo + Name / ID / Username
import os
import unicodedata

from PIL import Image, ImageDraw, ImageFont, ImageOps

try:                                   # Pillow 9.5.0 rounded_rectangle crash guard
    from ShiviMusic.utils import pil_compat  # noqa: F401
except Exception:
    pass

_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
TEMPLATE = os.path.join(_ASSETS, "welcome_template.png")
FONT_PATH = os.path.join(_ASSETS, "font.ttf")        # Poppins (Latin + Devanagari)

SS = 3                                               # supersampling for the round photo
PHOTO_CENTER = (1302, 475)
PHOTO_RADIUS = 262

# text slots inside the pills: (x, vertical centre, max width)
SLOT_NAME = (293, 437, 590)
SLOT_ID   = (233, 590, 400)
SLOT_USER = (373, 741, 515)
FONT_SIZE = 42

_notdef_cache = {}

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
    f = _FONT_CACHE.get(size)
    if f is None:
        f = _FONT_CACHE[size] = ImageFont.truetype(FONT_PATH, size)
    return f


def _render_mask(font, ch):
    img = Image.new("L", (80, 80), 0)
    ImageDraw.Draw(img).text((10, 10), ch, font=font, fill=255)
    return img.tobytes()


def _has_glyph(font, ch):
    """True when the font really draws `ch` (not the empty box / nothing)."""
    key = id(font)
    if key not in _notdef_cache:
        _notdef_cache[key] = (_render_mask(font, "\uffff"), _render_mask(font, " "))
    notdef, blank = _notdef_cache[key]
    m = _render_mask(font, ch)
    return m != notdef and (m != blank or ch.isspace())


def clean_text(text, font=None):
    """Keep only characters the font can draw (fancy unicode -> plain letters when possible)."""
    font = font or _font()
    out = []
    for ch in str(text or ""):
        if ch in "\u200b\u200c\u200d\ufe0f\u200e\u200f":
            continue
        if ch.isspace():
            out.append(" ")
        elif _has_glyph(font, ch):
            out.append(ch)
        elif ch in _LOOK and _has_glyph(font, _LOOK[ch]):
            out.append(_LOOK[ch])
        else:
            for sub in unicodedata.normalize("NFKD", ch):
                if not unicodedata.combining(sub) and not sub.isspace() and _has_glyph(font, sub):
                    out.append(sub)
    return " ".join("".join(out).split()).strip()


def _fit(text, font, max_w):
    if font.getlength(text) <= max_w:
        return text
    for i in range(len(text) - 1, 0, -1):
        cand = text[:i].rstrip() + "..."
        if font.getlength(cand) <= max_w:
            return cand
    return "..."


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
    font = _font()

    # ---- photo ----
    photo = None
    if photo_path and os.path.exists(photo_path):
        try:
            photo = Image.open(photo_path)
            photo.load()
        except Exception:
            photo = None
    safe_name = clean_text(name, font) or "User"
    if photo is None:
        photo = _avatar(safe_name[:1])
    rp = _round_photo(photo, PHOTO_RADIUS)
    cx, cy = PHOTO_CENTER
    bg.paste(rp, (cx - PHOTO_RADIUS, cy - PHOTO_RADIUS), rp)

    # ---- text ----
    uname = clean_text(str(username or "").lstrip("@"), font) or "No Username"
    items = (
        (SLOT_NAME, safe_name),
        (SLOT_ID, str(user_id)),
        (SLOT_USER, uname),
    )
    draw = ImageDraw.Draw(bg, "RGBA")
    for (x, cy_, max_w), text in items:
        text = _fit(text, font, max_w)
        draw.text((x + 1, cy_ + 2), text, font=font, fill=(0, 50, 130, 70), anchor="lm")     # soft shadow
        draw.text((x, cy_), text, font=font, fill=(255, 255, 255, 255), anchor="lm")

    bg.convert("RGB").save(out_path, "PNG")
    return out_path
