# =======================================================
# Neon "NEW MEMBER" welcome card
# Har baar naye random neon colours (blue/green/red wali
# palette ka hue random rotate hota hai).
# =======================================================

import colorsys
import math
import os
import random
import time
from datetime import datetime, timezone

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
FONT_BOLD = os.path.join(ASSETS, "font.ttf")      # Poppins SemiBold
FALLBACK_PIC = os.path.join(ASSETS, "upic.png")

W, H = 1720, 914          # card size
SS = 2                    # supersampling for smooth edges

WHITE = (255, 255, 255)
BG_TOP = (0, 0, 0)
BG_BOT = (0, 0, 0)


# -------------------------------------------------------
# Random palette (different every time)
# -------------------------------------------------------

_last_hue = None


def _hsv(h, s=0.85, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def _next_palette():
    """3 neon colours, base hue har baar pichle se clearly alag."""
    global _last_hue
    while True:
        h = random.random()
        if _last_hue is None:
            break
        d = abs(h - _last_hue)
        d = min(d, 1 - d)
        if d >= 0.12:
            break
    _last_hue = h
    # same feel as the reference: 3 hues spread around the wheel
    return _hsv(h), _hsv(h + 0.34), _hsv(h + 0.68)


def _mix(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


# -------------------------------------------------------
# Helpers
# -------------------------------------------------------

def _font(size):
    try:
        return ImageFont.truetype(FONT_BOLD, size)
    except Exception:
        return ImageFont.load_default()


def _fit_font(draw, text, size, max_w, min_size=18):
    while size > min_size:
        f = _font(size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 2
    return _font(min_size)


def _safe(text, limit, default):
    import unicodedata

    try:
        text = unicodedata.normalize("NFKD", str(text or ""))
        text = "".join(ch for ch in text if 32 <= ord(ch) < 127)
        text = " ".join(text.split())
    except Exception:
        text = ""
    return text[:limit].strip() or default


def _interp(t, colors):
    """t (HxW array 0..1) -> HxWx3 uint8 piecewise-linear through colors."""
    n = len(colors) - 1
    xs = np.linspace(0, 1, n + 1)
    out = np.empty(t.shape + (3,), dtype=np.uint8)
    for i in range(3):
        out[..., i] = np.interp(t, xs, [c[i] for c in colors]).astype(np.uint8)
    return out


def _hgrad(size, colors, tilt=0.0):
    w, h = size
    x = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    t = np.clip((x + tilt * y) / (1 + tilt), 0, 1)
    return Image.fromarray(_interp(t, colors), "RGB")


def _conic(size, center, colors):
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ang = np.arctan2(yy - center[1], xx - center[0])
    t = (ang + math.pi) / (2 * math.pi)
    return Image.fromarray(_interp(t, colors), "RGB")


def _down(img):
    return img.resize((W, H), Image.LANCZOS)


def _neon_layer(bg, mask, grad, glow=10, strength=1.8):
    """mask(L) ko gradient colour se glow ke saath bg par chipkao."""
    g = mask.filter(ImageFilter.GaussianBlur(glow)).point(
        lambda v: min(255, int(v * strength))
    )
    bg.paste(grad, (0, 0), g)
    bg.paste(grad, (0, 0), mask)
    return bg


def _shear(mask, k):
    w, h = mask.size
    pad = int(h * k)
    out = mask.transform(
        (w + pad, h),
        Image.AFFINE,
        (1, k, -pad, 0, 1, 0),
        resample=Image.BICUBIC,
    )
    return out


# -------------------------------------------------------
# Main
# -------------------------------------------------------

def welcomepic(pic, user, chatname, user_id, uname, joined=None):
    c1, c2, c3 = _next_palette()
    pal = [c1, c2, c3]
    W2, H2 = W * SS, H * SS

    # ---------- background ----------
    arr = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    top = np.array(BG_TOP, dtype=np.float32)
    bot = np.array(BG_BOT, dtype=np.float32)
    base = (top + (bot - top) * arr) * np.ones((1, W, 1), dtype=np.float32)
    bg = Image.fromarray(base.astype(np.uint8), "RGB").convert("RGBA")

    # soft colour glows (avatar side + title side)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((40, 180, 740, 880), fill=(*c1, 60))
    gd.ellipse((1100, 90, 1720, 420), fill=(*c3, 38))
    gd.ellipse((900, 520, 1720, 1000), fill=(*c2, 34))

    grad_h = _hgrad((W, H), [c1, c2, c3], tilt=0.35)

    # =====================================================
    # LAYER A : gradient neon strokes (drawn 2x, then down)
    # =====================================================
    m = Image.new("L", (W2, H2), 0)
    md = ImageDraw.Draw(m)

    def S(v):
        return int(v * SS)

    # --- corner diagonal bars ---
    def corner(cx, cy, sx, sy):
        # cx,cy = corner point; sx,sy = direction (+1/-1) into the card
        for off, wd in ((70, 14), (125, 7), (165, 4)):
            p1 = (cx + sx * off, cy)
            p2 = (cx, cy + sy * off)
            md.line([(S(p1[0]), S(p1[1])), (S(p2[0]), S(p2[1]))], fill=255, width=S(wd))

    corner(0, 0, 1, 1)
    corner(W, 0, -1, 1)
    corner(0, H, 1, -1)
    corner(W, H, -1, -1)

    # --- top pill ---
    pill = (118, 57, 790, 122)
    md.rounded_rectangle(
        [S(pill[0]), S(pill[1]), S(pill[2]), S(pill[3])],
        radius=S(32), outline=255, width=S(5),
    )

    # --- info panel ---
    panel = (733, 362, 1638, 782)
    md.rounded_rectangle(
        [S(panel[0]), S(panel[1]), S(panel[2]), S(panel[3])],
        radius=S(38), outline=255, width=S(5),
    )

    # --- footer lines + slashes ---
    for x0, x1 in ((235, 430), (1288, 1490)):
        md.line([(S(x0), S(836)), (S(x1), S(836))], fill=255, width=S(2))
    # divider inside panel
    md.line([(S(772), S(678)), (S(1597), S(678))], fill=255, width=S(3))
    # title top/bottom accent lines
    md.line([(S(780), S(140)), (S(1580), S(140))], fill=255, width=S(3))

    # --- crown (above avatar) ---
    cx, cy = 392, 490
    crown = [
        (342, 218), (338, 172), (366, 196), (394, 150),
        (422, 196), (450, 172), (446, 218),
    ]
    md.line([(S(x), S(y)) for x, y in crown] + [(S(crown[0][0]), S(crown[0][1]))],
            fill=255, width=S(6), joint="curve")

    m1 = _down(m)
    bg = _neon_layer(bg.convert("RGB"), m1, grad_h, glow=9, strength=1.9).convert("RGBA")

    # =====================================================
    # LAYER B : avatar rings (conic gradient)
    # =====================================================
    rm = Image.new("L", (W2, H2), 0)
    rd = ImageDraw.Draw(rm)
    R_ARC = 282
    segs = [(-70, -8), (-2, 52), (58, 112), (118, 170), (176, 228), (234, 284)]
    for a0, a1 in segs:
        rd.arc(
            [S(cx - R_ARC), S(cy - R_ARC), S(cx + R_ARC), S(cy + R_ARC)],
            start=a0, end=a1, fill=255, width=S(15),
        )
    R_THIN = 262
    rd.ellipse(
        [S(cx - R_THIN), S(cy - R_THIN), S(cx + R_THIN), S(cy + R_THIN)],
        outline=255, width=S(3),
    )
    rm1 = _down(rm)
    conic = _conic((W, H), (cx, cy), [c1, c2, c3, c1])
    bg = _neon_layer(bg.convert("RGB"), rm1, conic, glow=12, strength=1.7).convert("RGBA")

    # white inner ring
    wm = Image.new("L", (W2, H2), 0)
    wd = ImageDraw.Draw(wm)
    R_W = 248
    wd.ellipse(
        [S(cx - R_W), S(cy - R_W), S(cx + R_W), S(cy + R_W)],
        outline=255, width=S(9),
    )
    wm1 = _down(wm)
    wglow = wm1.filter(ImageFilter.GaussianBlur(8)).point(lambda v: min(255, int(v * 1.2)))
    bg.paste(Image.new("RGBA", (W, H), (*_mix(c1, WHITE, 0.6), 255)), (0, 0), wglow)
    bg.paste(Image.new("RGBA", (W, H), (255, 255, 255, 255)), (0, 0), wm1)

    # =====================================================
    # Profile photo (circle)
    # =====================================================
    try:
        photo = Image.open(pic).convert("RGBA")
    except Exception:
        photo = Image.open(FALLBACK_PIC).convert("RGBA")
    R_P = 242
    photo = ImageOps.fit(photo, (R_P * 2, R_P * 2), Image.LANCZOS)
    photo = ImageEnhance.Brightness(photo).enhance(1.05)
    pm = Image.new("L", (R_P * 2 * SS, R_P * 2 * SS), 0)
    ImageDraw.Draw(pm).ellipse((0, 0, R_P * 2 * SS - 1, R_P * 2 * SS - 1), fill=255)
    pm = pm.resize((R_P * 2, R_P * 2), Image.LANCZOS)
    bg.paste(photo, (cx - R_P, cy - R_P), pm)

    # =====================================================
    # Fills (pill + panel) – glow ke upar, text ke neeche
    # =====================================================
    fill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fill)
    fd.rounded_rectangle(
        (pill[0] + 4, pill[1] + 4, pill[2] - 4, pill[3] - 4),
        radius=28, fill=(0, 0, 0, 255),
    )
    fd.rounded_rectangle(
        (panel[0] + 4, panel[1] + 4, panel[2] - 4, panel[3] - 4),
        radius=34, fill=(0, 0, 0, 255),
    )
    bg = Image.alpha_composite(bg, fill)
    # re-draw crisp borders on top of fills (so glow inside the fill doesn't hide them)
    bg = bg.convert("RGB")
    bg.paste(grad_h, (0, 0), m1)
    bg = bg.convert("RGBA")

    d = ImageDraw.Draw(bg)

    # =====================================================
    # Top pill text
    # =====================================================
    pf = _font(31)
    d.text((205, 89), "WELCOME TO THE COMMUNITY", font=pf, fill=(238, 246, 255), anchor="lm")
    # slashes
    for i in range(3):
        d.line([(150 + i * 14, 101), (166 + i * 14, 77)], fill=c1, width=4)
        d.line([(718 + i * 14, 101), (734 + i * 14, 77)], fill=c3, width=4)

    # =====================================================
    # Big title : NEW MEMBER (italic, gradient, glow)
    # =====================================================
    title = "NEW MEMBER"
    tx, ty, tw_max = 735, 170, 900
    tsize = 140
    tf = _font(tsize)
    probe = ImageDraw.Draw(Image.new("L", (10, 10)))
    while probe.textlength(title, font=tf) > tw_max and tsize > 60:
        tsize -= 4
        tf = _font(tsize)
    tmask = Image.new("L", (tw_max + 140, 220), 0)
    ImageDraw.Draw(tmask).text((20, 110), title, font=tf, fill=255, anchor="lm", stroke_width=4)
    tmask = _shear(tmask, 0.18)
    tl, tt, tr, tb = tmask.getbbox() or (0, 0, tmask.width, tmask.height)

    tcols = [_mix(c1, WHITE, 0.55), c1, c2, _mix(c2, WHITE, 0.2), _mix(c3, WHITE, 0.55)]
    tg = _hgrad(tmask.size, tcols)
    # top highlight (glossy)
    hl = np.linspace(0, 1, tmask.height, dtype=np.float32)[:, None, None]
    tg_arr = np.asarray(tg, dtype=np.float32)
    k = np.clip(0.55 - hl * 1.1, 0, 0.55)
    tg_arr = tg_arr + (255 - tg_arr) * k
    tg = Image.fromarray(tg_arr.astype(np.uint8), "RGB")

    ox, oy = tx - 20, ty + 56 - 110 - 8
    layer_glow = Image.new("L", (W, H), 0)
    layer_glow.paste(tmask, (ox, oy))
    gl = layer_glow.filter(ImageFilter.GaussianBlur(14)).point(lambda v: min(255, int(v * 1.0)))
    bg.paste(_hgrad((W, H), [c1, c2, c3]), (0, 0), gl)
    # drop shadow
    sh = Image.new("L", (W, H), 0)
    sh.paste(tmask, (ox + 4, oy + 6))
    bg.paste(Image.new("RGBA", (W, H), (0, 0, 20, 255)), (0, 0), sh.filter(ImageFilter.GaussianBlur(3)))
    bg.paste(tg, (ox, oy), tmask)

    d = ImageDraw.Draw(bg)

    # =====================================================
    # GROUP : name
    # =====================================================
    chat_name = _safe(chatname, 18, "GROUP").upper()
    gf = _font(46)
    pre = "GROUP :"
    cn_font = _fit_font(d, chat_name, 46, 300, 24)
    wpre = d.textlength(pre + "  ", font=gf)
    wname = d.textlength(chat_name, font=cn_font)
    gx = 1160 - (wpre + wname) / 2
    GY = 326
    d.text((gx, GY), pre, font=gf, fill=(238, 244, 255), anchor="lm")
    d.text((gx + wpre, GY), chat_name, font=cn_font, fill=c2, anchor="lm")
    lx1 = gx - 24
    lx2 = gx + wpre + wname + 24
    if lx1 - 765 > 30:
        d.line([(765, GY + 2), (lx1, GY + 2)], fill=c1, width=2)
    if 1560 - lx2 > 30:
        d.line([(lx2, GY + 2), (1560, GY + 2)], fill=c3, width=2)

    # =====================================================
    # Panel rows
    # =====================================================
    lab_f = _font(29)
    uname_txt = f"@{uname}" if uname else "NOT SET"
    rows = [
        (428, "USERNAME", uname_txt, WHITE),
        (521, "USER ID", str(user_id), WHITE),
        (614, "STATUS", "VERIFIED MEMBER", c2),
    ]
    lab_col = _mix(c1, WHITE, 0.7)
    for ry, lab, val, col in rows:
        d.text((880, ry), lab, font=lab_f, fill=lab_col, anchor="lm")
        d.line([(1088, ry - 28), (1088, ry + 28)], fill=(235, 240, 255), width=3)
        vf = _fit_font(d, val, 50, 480, 24)
        d.text((1130, ry), val, font=vf, fill=col, anchor="lm")

    # event code
    joined = joined or datetime.now(timezone.utc)
    code = joined.strftime("%d-%b-%Y").upper()
    d.text((880, 723), "VERIFIED EVENT CODE", font=_font(27), fill=lab_col, anchor="lm")
    d.line([(1212, 706), (1212, 742)], fill=(235, 240, 255), width=3)
    d.text((1244, 725), code, font=_font(38), fill=c3, anchor="lm")

    # =====================================================
    # Icons (drawn 2x on overlay, then down)
    # =====================================================
    ov = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)

    def circ(x, y, r, col, wdt):
        od.ellipse([S(x - r), S(y - r), S(x + r), S(y + r)], outline=col, width=S(wdt))

    # user
    ix = 818
    circ(ix, 428, 36, c1, 4)
    od.ellipse([S(ix - 9), S(412), S(ix + 9), S(430)], fill=_mix(c1, WHITE, 0.35))
    od.pieslice([S(ix - 19), S(434), S(ix + 19), S(474)], 180, 360, fill=_mix(c1, WHITE, 0.35))
    # id card
    circ(ix, 521, 36, c2, 4)
    od.rounded_rectangle([S(ix - 19), S(504), S(ix + 19), S(540)], radius=S(5), fill=_mix(c2, (0, 20, 10), 0.55), outline=_mix(c2, WHITE, 0.3), width=S(3))
    od.ellipse([S(ix - 5), S(509), S(ix + 5), S(519)], fill=WHITE)
    od.pieslice([S(ix - 11), S(520), S(ix + 11), S(540)], 180, 360, fill=WHITE)
    # shield
    circ(ix, 614, 36, WHITE, 4)
    shield = [(ix - 17, 600), (ix, 594), (ix + 17, 600), (ix + 15, 622), (ix, 634), (ix - 15, 622)]
    pts = [(S(x), S(y)) for x, y in shield]
    od.polygon(pts, fill=(0, 0, 0, 255))
    od.line(pts + [pts[0]], fill=WHITE, width=S(3), joint="curve")
    od.line([(S(ix - 8), S(614)), (S(ix - 2), S(621)), (S(ix + 9), S(606))], fill=WHITE, width=S(4), joint="curve")
    # calendar
    cal = [790, 697, 847, 757]
    od.rounded_rectangle([S(v) for v in cal], radius=S(9), fill=_mix(c3, (20, 0, 0), 0.25), outline=_mix(c3, WHITE, 0.25), width=S(3))
    od.rectangle([S(793), S(712), S(844), S(715)], fill=_mix(c3, WHITE, 0.55))
    for tx_ in (803, 834):
        od.rounded_rectangle([S(tx_ - 3), S(691), S(tx_ + 3), S(704)], radius=S(3), fill=_mix(c3, WHITE, 0.6))
    for gy in (727, 741):
        for gx_ in (803, 818, 833):
            od.rounded_rectangle([S(gx_ - 4), S(gy - 4), S(gx_ + 4), S(gy + 4)], radius=S(2), fill=_mix(c3, WHITE, 0.7))

    # footer diagonal bars
    for i in range(3):
        col = (c1, c2, c3)[i]
        od.line([(S(442 + i * 16), S(846)), (S(458 + i * 16), S(822))], fill=col, width=S(5))
        od.line([(S(1218 + i * 16), S(846)), (S(1234 + i * 16), S(822))], fill=(c1, c2, c3)[i], width=S(5))
    ov = _down(ov)
    bg = Image.alpha_composite(bg, ov)

    # footer text (letter-spaced)
    d = ImageDraw.Draw(bg)
    parts = ["STAY CONNECTED", "STAY ACTIVE", "BE PART OF US"]
    fsz, sp, gap = 24, 2.2, 30
    while True:
        ff = _font(fsz)

        def spaced_w(t):
            return sum(d.textlength(ch, font=ff) + sp for ch in t) - sp

        total = sum(spaced_w(p) for p in parts) + (gap * 2 + 8) * 2
        if total <= 660 or fsz <= 16:
            break
        fsz -= 1
    x = 857 - total / 2
    for i, p in enumerate(parts):
        for ch in p:
            d.text((x, 836), ch, font=ff, fill=(225, 235, 255), anchor="lm")
            x += d.textlength(ch, font=ff) + sp
        if i < len(parts) - 1:
            x += gap
            d.ellipse([x - 4, 832, x + 4, 840], fill=(235, 240, 255))
            x += 8 + gap

    # =====================================================
    # Save
    # =====================================================
    return _save(bg, user_id)


def _save(img, user_id):
    """Unique absolute path -> concurrent joins / cwd changes can't clash."""
    folder = os.path.abspath("downloads")
    os.makedirs(folder, exist_ok=True)
    out = os.path.join(folder, f"welcome_{user_id}_{int(time.time() * 1000)}.png")
    img.convert("RGB").save(out)
    return out


def simple_welcomepic(pic, user, chatname, user_id, uname, joined=None):
    """Light fallback card (plain Pillow, no numpy) used if the neon card ever fails."""
    c1, c2, _c3 = _next_palette()
    w, h = 1280, 720
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=_mix(BG_TOP, _mix(c1, BG_BOT, 0.75), y / h))

    try:
        photo = Image.open(pic).convert("RGB")
    except Exception:
        photo = Image.open(FALLBACK_PIC).convert("RGB")
    r = 190
    photo = ImageOps.fit(photo, (r * 2, r * 2), Image.LANCZOS)
    mask = Image.new("L", (r * 2, r * 2), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, r * 2 - 1, r * 2 - 1), fill=255)
    cx, cy = 280, h // 2
    d.ellipse((cx - r - 10, cy - r - 10, cx + r + 10, cy + r + 10), outline=c1, width=8)
    img.paste(photo, (cx - r, cy - r), mask)

    d.text((540, 190), "WELCOME", font=_font(110), fill=WHITE, anchor="lm")
    d.text((540, 300), _safe(chatname, 22, "GROUP").upper(), font=_font(50), fill=c2, anchor="lm")
    d.text((540, 420), f"USERNAME : {('@' + uname) if uname else 'NOT SET'}", font=_font(40), fill=WHITE, anchor="lm")
    d.text((540, 490), f"USER ID : {user_id}", font=_font(40), fill=WHITE, anchor="lm")
    d.text((540, 560), "STATUS : VERIFIED MEMBER", font=_font(40), fill=c2, anchor="lm")
    return _save(img, user_id)


# -------------------------------------------------------
# Simple fallback card (sirf basic PIL, numpy ke bina).
# Neon card kisi bhi wajah se fail ho to ye use hota hai,
# taaki welcome me image hamesha aaye.
# -------------------------------------------------------

def welcomepic_simple(pic, user, chatname, user_id, uname, joined=None):
    c1, c2, c3 = _next_palette()
    w, h = 1280, 640

    bg = Image.new("RGB", (w, h), BG_TOP)
    bd = ImageDraw.Draw(bg)
    for y in range(h):
        bd.line([(0, y), (w, y)], fill=_mix(BG_TOP, c1, 0.25 * y / h))

    bd.rounded_rectangle((30, 30, w - 30, h - 30), radius=40, outline=c2, width=5)

    # profile photo (circle + ring)
    try:
        photo = Image.open(pic).convert("RGB")
    except Exception:
        photo = Image.open(FALLBACK_PIC).convert("RGB")
    r = 190
    cx, cy = 290, h // 2
    photo = ImageOps.fit(photo, (r * 2, r * 2), Image.LANCZOS)
    mask = Image.new("L", (r * 2, r * 2), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, r * 2 - 1, r * 2 - 1), fill=255)
    bd.ellipse((cx - r - 12, cy - r - 12, cx + r + 12, cy + r + 12), outline=c1, width=10)
    bg.paste(photo, (cx - r, cy - r), mask)

    d = ImageDraw.Draw(bg)
    x0 = 560
    d.text((x0, 120), "NEW MEMBER", font=_font(92), fill=c1, anchor="lm")
    d.text((x0, 215), "WELCOME TO THE COMMUNITY", font=_font(32), fill=(238, 246, 255), anchor="lm")

    chat_name = _safe(chatname, 22, "GROUP").upper()
    d.text((x0, 300), "GROUP : ", font=_font(40), fill=(238, 244, 255), anchor="lm")
    d.text((x0 + d.textlength("GROUP : ", font=_font(40)), 300), chat_name,
           font=_fit_font(d, chat_name, 40, 480, 22), fill=c2, anchor="lm")

    uname_txt = f"@{uname}" if uname else "NOT SET"
    d.text((x0, 380), f"USERNAME : {uname_txt}", font=_fit_font(d, f"USERNAME : {uname_txt}", 36, 640, 20), fill=WHITE, anchor="lm")
    d.text((x0, 445), f"USER ID : {user_id}", font=_font(36), fill=WHITE, anchor="lm")
    d.text((x0, 510), "STATUS : VERIFIED MEMBER", font=_font(36), fill=c3, anchor="lm")

    os.makedirs("downloads", exist_ok=True)
    out = f"downloads/welcome_{user_id}.png"
    bg.save(out)
    return out
