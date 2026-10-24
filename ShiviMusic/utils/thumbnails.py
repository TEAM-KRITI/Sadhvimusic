import os
import re
import time
import random
import colorsys
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance, ImageOps
from py_yt import VideosSearch
from config import YOUTUBE_IMG_URL

# ───────────────────────── Fonts (same as reference thumbnail) ─────────────────────────
_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
FONT_TITLE = os.path.join(_ASSETS, "fonts.ttf")   # Boogaloo   -> song title (English)
FONT_INFO  = os.path.join(_ASSETS, "font.ttf")    # Poppins SB -> info line, credits + Hindi title text

# ───────────────────────── Text shown on the thumbnail ─────────────────────────
DEV_TEXT    = "Dev :- @kirti_bots"     # top-right
OWNER_TEXT  = "@System_xd_lll"         # bottom-left
CREDIT_COLOR = (255, 241, 0)           # yellow

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# ───────────────────────── Layout (iPhone music-player card) ─────────────────────────
W, H = 1280, 720
SS = 2                                  # supersampling for smooth shapes
CARD = (130, 76, 1150, 647)             # glass player card
CARD_R = 66
_K = (CARD[2] - CARD[0]) / 621.0        # scale from the reference template

def _X(x): return CARD[0] + (x - 46) * _K
def _Y(y): return CARD[1] + (y - 30) * _K

ART_BOX = tuple(int(v) for v in (_X(70), _Y(62), _X(363), _Y(345)))
TXT_X   = int(_X(395))
BAR_X0, BAR_X1 = int(_X(395)), int(_X(631))
MAX_TITLE_WIDTH = BAR_X1 - TXT_X

DIRECT_THUMB_FALLBACK = "https://i.ytimg.com/vi/{videoid}/hqdefault.jpg"

# ───────────────────────── Border colour: different every time ─────────────────────────
_last_hue = None


def _next_accent():
    """Random vivid colour, guaranteed to differ clearly from the previous one."""
    global _last_hue
    while True:
        hue = random.random()
        if _last_hue is None:
            break
        diff = abs(hue - _last_hue)
        diff = min(diff, 1 - diff)
        if diff >= 0.15:
            break
    _last_hue = hue
    r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    return int(r * 255), int(g * 255), int(b * 255)


_last_title_hue = None


def _next_title_color(accent):
    """Bright title colour, new on every call (differs from the last one and from the border colour)."""
    global _last_title_hue
    acc_h = colorsys.rgb_to_hsv(*[v / 255 for v in accent])[0]
    while True:
        hue = random.random()
        d_acc = min(abs(hue - acc_h), 1 - abs(hue - acc_h))
        d_last = 1.0 if _last_title_hue is None else min(abs(hue - _last_title_hue), 1 - abs(hue - _last_title_hue))
        if d_acc >= 0.1 and d_last >= 0.15:
            break
    _last_title_hue = hue
    r, g, b = colorsys.hsv_to_rgb(hue, random.uniform(0.45, 0.7), 1.0)
    return int(r * 255), int(g * 255), int(b * 255)


def _accent2(accent):
    """Second colour of the wash: hue shifted from the accent (also new every time)."""
    r, g, b = [v / 255 for v in accent]
    h, sat, v = colorsys.rgb_to_hsv(r, g, b)
    r, g, b = colorsys.hsv_to_rgb((h + random.choice((0.12, 0.18, -0.12, -0.18))) % 1.0, min(1, sat + 0.1), v * 0.75)
    return int(r * 255), int(g * 255), int(b * 255)


def _mix(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _is_devanagari(ch):
    o = ord(ch)
    return 0x0900 <= o <= 0x097F or 0xA8E0 <= o <= 0xA8FF or 0x1CD0 <= o <= 0x1CFF


def _plain_name(value):
    """'[Name](tg://user?id=1)' / '<a href=..>Name</a>' / 'Name' -> 'Name'."""
    if not value:
        return ""
    text = str(value)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.strip()
    return "" if text.lower() in {"unknown", "none", "badnam"} else text


def _clean_title(text):
    """Drop characters neither font can draw (emoji etc.) so the title never shows boxes."""
    out = []
    for ch in str(text):
        o = ord(ch)
        if ch.isspace():
            out.append(" ")
        elif o <= 0x024F or 0x2010 <= o <= 0x2027 or _is_devanagari(ch) or o in (0x200C, 0x200D):
            out.append(ch)
    return re.sub(r"\s+", " ", "".join(out)).strip()


def _segments(text, latin_font, hindi_font):
    """Split text into runs: Hindi -> Poppins, everything else -> title font."""
    segs = []
    for ch in text:
        if _is_devanagari(ch):
            f = hindi_font
        elif ord(ch) in (0x200C, 0x200D) and segs:
            f = segs[-1][0]
        elif ch == " " and segs:
            f = segs[-1][0]
        else:
            f = latin_font
        if segs and segs[-1][0] is f:
            segs[-1][1] += ch
        else:
            segs.append([f, ch])
    return segs


def _text_width(segs):
    return sum(f.getlength(t) for f, t in segs)


def trim_text(text, latin_font, hindi_font, max_width):
    try:
        if _text_width(_segments(text, latin_font, hindi_font)) <= max_width:
            return text
        for i in range(len(text) - 1, 0, -1):
            cand = text[:i].rstrip() + " ..."
            if _text_width(_segments(cand, latin_font, hindi_font)) <= max_width:
                return cand
        return "..."
    except Exception:
        return text[:60]


def _draw_title(draw, baseline_y, text, latin_font, hindi_font, fill):
    segs = _segments(text, latin_font, hindi_font)
    x = (W - _text_width(segs)) / 2
    for f, t in segs:                      # shadow
        draw.text((x + 1, baseline_y + 1), t, font=f, fill=(0, 0, 0, 110), anchor="ls")
        x += f.getlength(t)
    x = (W - _text_width(segs)) / 2
    for f, t in segs:                      # text
        draw.text((x, baseline_y), t, font=f, fill=fill, anchor="ls")
        x += f.getlength(t)


def _draw_centered(draw, y, text, font, fill, shadow=True):
    w = font.getlength(text)
    x = (W - w) / 2
    if shadow:
        draw.text((x + 1, y + 1), text, font=font, fill=(0, 0, 0, 110))
    draw.text((x, y), text, font=font, fill=fill)


def _rr_mask(box, radius, size=(W, H)):
    """Smooth (supersampled) rounded-rectangle mask."""
    m = Image.new("L", (size[0] * SS, size[1] * SS), 0)
    ImageDraw.Draw(m).rounded_rectangle([v * SS for v in box], radius=radius * SS, fill=255)
    return m.resize(size, Image.LANCZOS)


def _draw_player(bg, accent, accent2, src, title, sub, title_color, requester, t_left, t_right, progress):
    """iPhone-style 'now playing' card. Colours come from accent/accent2 (new every call)."""
    # ---- pure black background + black card (lines are neon) ----
    bg = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    cm = _rr_mask(CARD, CARD_R)

    # ---- everything shape-like drawn at 2x then downsampled ----
    ov = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)

    def S(v): return int(v * SS)

    white = (*accent, 255)      # neon lines
    soft = (*accent, 90)        # dim track

    od.rounded_rectangle([S(v) for v in CARD], radius=S(CARD_R), outline=white, width=S(7))



    # progress bar
    by = int(_Y(170))
    od.rounded_rectangle([S(BAR_X0), S(by - 3), S(BAR_X1), S(by + 3)], radius=S(3), fill=soft)
    px = BAR_X0 + (BAR_X1 - BAR_X0) * max(0.0, min(1.0, progress))
    od.rounded_rectangle([S(BAR_X0), S(by - 3), S(px), S(by + 3)], radius=S(3), fill=white)
    od.ellipse([S(px - 8), S(by - 8), S(px + 8), S(by + 8)], fill=white)

    # controls: prev / pause / next
    cy = int(_Y(226))
    cx = (BAR_X0 + BAR_X1) // 2
    off = 138
    ih = 24
    # pause
    for dx in (-17, 6):
        od.rounded_rectangle([S(cx + dx), S(cy - 30), S(cx + dx + 12), S(cy + 30)], radius=S(3), fill=white)
    # prev  |◀◀
    for base in (cx - off - 22, cx - off + 2):
        od.polygon([(S(base + 24), S(cy - ih)), (S(base + 24), S(cy + ih)), (S(base), S(cy))], fill=white)
    # next  ▶▶|
    for base in (cx + off - 4, cx + off + 20):
        od.polygon([(S(base), S(cy - ih)), (S(base), S(cy + ih)), (S(base + 24), S(cy))], fill=white)

    # volume row
    vy = int(_Y(287))
    vx0, vx1 = int(_X(409)), int(_X(607))
    od.rounded_rectangle([S(vx0), S(vy - 3), S(vx1), S(vy + 3)], radius=S(3), fill=soft)
    vk = vx0 + (vx1 - vx0) * 0.88
    od.rounded_rectangle([S(vx0), S(vy - 3), S(vk), S(vy + 3)], radius=S(3), fill=white)
    od.ellipse([S(vk - 7), S(vy - 7), S(vk + 7), S(vy + 7)], fill=white)
    # speaker icons
    sx = TXT_X + 2
    od.polygon([(S(sx), S(vy - 4)), (S(sx + 6), S(vy - 4)), (S(sx + 13), S(vy - 10)), (S(sx + 13), S(vy + 10)), (S(sx + 6), S(vy + 4)), (S(sx), S(vy + 4))], fill=soft)
    sx = BAR_X1 + 20
    od.polygon([(S(sx - 14), S(vy - 4)), (S(sx - 8), S(vy - 4)), (S(sx - 1), S(vy - 10)), (S(sx - 1), S(vy + 10)), (S(sx - 8), S(vy + 4)), (S(sx - 14), S(vy + 4))], fill=white)
    for r in (8, 14):
        od.arc([S(sx - 3 - r), S(vy - r), S(sx - 3 + r), S(vy + r)], -50, 50, fill=white, width=S(2.5))

    # AirPlay-style icon (top-right of text column)
    ax, ay = BAR_X1 - 8, int(_Y(100))
    od.arc([S(ax - 16), S(ay - 16), S(ax + 16), S(ay + 16)], 150, 390, fill=white, width=S(3))
    od.arc([S(ax - 9), S(ay - 9), S(ax + 9), S(ay + 9)], 150, 390, fill=white, width=S(3))
    od.polygon([(S(ax), S(ay + 1)), (S(ax - 9), S(ay + 17)), (S(ax + 9), S(ay + 17))], fill=white)

    # home indicator
    hy = int(_Y(357))
    od.rounded_rectangle([S(_X(467)), S(hy - 3), S(_X(571)), S(hy + 3)], radius=S(3), fill=(*accent, 220))

    ov = ov.resize((W, H), Image.LANCZOS)
    # neon glow: blurred copies of the lines under the crisp lines
    for rad, gain in ((22, 1.6), (8, 1.4)):
        g = ov.filter(ImageFilter.GaussianBlur(rad))
        g.putalpha(g.getchannel("A").point(lambda v, k=gain: min(255, int(v * k))))
        bg = Image.alpha_composite(bg, g)
    bg = Image.alpha_composite(bg, ov)
    # hot white-ish core so it reads as a lit neon tube
    core = ov.copy()
    core.putalpha(core.getchannel("A").point(lambda v: int(v * 0.35)))
    core_c = Image.new("RGBA", (W, H), (*_mix(accent, (255, 255, 255), 0.7), 255))
    core_c.putalpha(core.getchannel("A"))
    bg = Image.alpha_composite(bg, core_c)

    # ---- album art (rounded, with shadow) ----
    ax0, ay0, ax1, ay1 = ART_BOX
    am = _rr_mask(ART_BOX, 38)
    ash = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ash.putalpha(am.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.5)))
    ash2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ash2.paste(ash, (0, 8))
    bg = Image.alpha_composite(bg, ash2)
    art = ImageOps.fit(src, (ax1 - ax0, ay1 - ay0), Image.LANCZOS)
    art = ImageEnhance.Brightness(art).enhance(1.04)
    bg.paste(art, (ax0, ay0), am.crop((ax0, ay0, ax1, ay1)))

    # ---- text ----
    f_title = ImageFont.truetype(FONT_TITLE, 38)   # Boogaloo
    f_hi    = ImageFont.truetype(FONT_INFO, 29)    # Poppins (Hindi runs)
    f_sub   = ImageFont.truetype(FONT_TITLE, 30)
    f_name  = ImageFont.truetype(FONT_TITLE, 29)
    f_name_hi = ImageFont.truetype(FONT_INFO, 23)
    f_init  = ImageFont.truetype(FONT_TITLE, 26)
    f_init_hi = ImageFont.truetype(FONT_INFO, 22)
    f_time  = ImageFont.truetype(FONT_TITLE, 23)

    # requester pill:  ( A ) Name   -- coloured initial circle + frosted pill
    name = _clean_title(requester) if requester else ""
    name_segs = []
    if name:
        name = trim_text(name, f_name, f_name_hi, MAX_TITLE_WIDTH - 110)
        name_segs = _segments(name, f_name, f_name_hi)
        ph, pad = 42, 6
        pcy = 556                      # bottom of the text column, under the volume row
        pw = pad + ph - 2 * pad + 12 + _text_width(name_segs) + 20
        px0 = (BAR_X0 + BAR_X1 - pw) / 2
        px1 = px0 + pw
        pill = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
        pd = ImageDraw.Draw(pill)
        pd.rounded_rectangle([int(px0 * SS), int((pcy - ph / 2) * SS), int(px1 * SS), int((pcy + ph / 2) * SS)],
                             radius=int(ph / 2 * SS), fill=(255, 255, 255, 48), outline=(255, 255, 255, 170), width=2 * SS)
        cr = ph / 2 - pad
        ccx = px0 + pad + cr
        pd.ellipse([int((ccx - cr) * SS), int((pcy - cr) * SS), int((ccx + cr) * SS), int((pcy + cr) * SS)], fill=(*title_color, 255))
        pill = pill.resize((W, H), Image.LANCZOS)
        bg = Image.alpha_composite(bg, pill)

    draw = ImageDraw.Draw(bg)

    if name_segs:
        ch = name[0].upper()
        fi = f_init_hi if _is_devanagari(ch) else f_init
        draw.text((ccx, pcy + 1), ch, font=fi, fill=(25, 25, 35, 255), anchor="mm")
        x = ccx + cr + 12
        for f, t in name_segs:
            draw.text((x, pcy + 1), t, font=f, fill=(255, 255, 255, 255), anchor="lm")
            x += f.getlength(t)

    # title (Latin + Hindi runs)
    title = _clean_title(title) or "Now Playing"
    title = trim_text(title, f_title, f_hi, MAX_TITLE_WIDTH)
    x = TXT_X
    for f, t in _segments(title, f_title, f_hi):
        draw.text((x, _Y(116) + 6), t, font=f, fill=(*title_color, 255), anchor="lm")
        x += f.getlength(t)

    # artist — views
    sub = _clean_title(sub)
    sub = trim_text(sub, f_sub, f_hi, MAX_TITLE_WIDTH)
    x = TXT_X
    for f, t in _segments(sub, f_sub, f_hi):
        draw.text((x, _Y(138) + 8), t, font=f, fill=(255, 255, 255, 215), anchor="lm")
        x += f.getlength(t)

    # times
    ty = _Y(182)
    draw.text((BAR_X0, ty), t_left, font=f_time, fill=(255, 255, 255, 200), anchor="lm")
    draw.text((BAR_X1, ty), t_right, font=f_time, fill=(255, 255, 255, 200), anchor="rm")
    return bg


def _to_seconds(text):
    try:
        parts = [int(p) for p in str(text).split(":")]
    except Exception:
        return 0
    sec = 0
    for p in parts:
        sec = sec * 60 + p
    return sec


def _fmt_time(sec):
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s_ = divmod(rem, 60)
    return f"{h}:{m:02d}:{s_:02d}" if h else f"{m}:{s_:02d}"


async def _fetch_meta_via_search(videoid: str):
    """title / thumb / duration / views / channel via py_yt. Verifies the id so a
    drifting text-search can't return a different video."""
    for _attempt in range(2):
        try:
            results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
            results_data = await results.next()
            data = results_data.get("result", [{}])[0]

            fetched_id = data.get("id") or data.get("videoId")
            if fetched_id and fetched_id != videoid:
                continue

            title = re.sub(r"\s+", " ", data.get("title", "Song")).strip() or "Song"
            thumbnail_url = data.get("thumbnails", [{}])[0].get("url", "").split("?")[0]
            duration = data.get("duration")
            views = data.get("viewCount", {}).get("short", "Unknown")
            channel = data.get("channel", {}).get("name", "YouTube")
            if thumbnail_url:
                return title, thumbnail_url, duration, views, channel
        except Exception:
            pass
    return None


async def _fetch_title_via_oembed(videoid: str):
    """Fallback: real title/channel straight from YouTube oEmbed (no API key)."""
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={videoid}&format=json"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    title = re.sub(r"\s+", " ", data.get("title", "")).strip()
                    if title:
                        return title, data.get("author_name", "YouTube")
    except Exception:
        pass
    return None


# ═════════════════════════ Glass "now playing" card (1920x1080) ═════════════════════════
GW, GH = 1920, 1080
G_CARD = (460, 190, 1460, 890)
G_CARD_R = 70
G_ART = (535, 275, 810, 550)
G_TXT_X = 836
G_TXT_MAX = 1385 - 836
G_BAR_X0, G_BAR_X1, G_BAR_Y = 611, 1300, 640
G_VOL_X0, G_VOL_X1, G_VOL_Y = 577, 1330, 827
BITRATE_TEXT = "140 KBPS"       # bottom-right pill
SHOW_CREDITS = False            # True = DEV_TEXT / OWNER_TEXT bhi dikhao


def _g_rr_mask(box, radius, size=(GW, GH)):
    m = Image.new("L", (size[0] * SS, size[1] * SS), 0)
    ImageDraw.Draw(m).rounded_rectangle([v * SS for v in box], radius=radius * SS, fill=255)
    return m.resize(size, Image.LANCZOS)


def _star_points(cx, cy, ro, ri):
    import math
    pts = []
    for i in range(10):
        r = ro if i % 2 == 0 else ri
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _draw_glass_player(src, title, sub, t_left, t_right, progress, is_live=False):
    """Dark glass card over the blurred cover: art + title + progress + controls + volume."""
    # ---- background: cover blurred + darkened ----
    small = ImageOps.fit(src.convert("RGB"), (480, 270), Image.LANCZOS).filter(ImageFilter.GaussianBlur(10))
    bg = small.resize((GW, GH), Image.BICUBIC).convert("RGBA")
    bg = ImageEnhance.Brightness(bg).enhance(0.62)

    # ---- glass card: darker + extra soft ----
    cm = _g_rr_mask(G_CARD, G_CARD_R)
    card = bg.filter(ImageFilter.GaussianBlur(30))
    card = ImageEnhance.Brightness(card).enhance(0.34)
    bg = Image.composite(card, bg, cm)

    # ---- vector bits (bars, icons) drawn at SS x ----
    ox, oy = 440, 170
    rw, rh = 1040, 740
    ov = Image.new("RGBA", (rw * SS, rh * SS), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)

    def S(v, o): return int((v - o) * SS)
    def X(v): return S(v, ox)
    def Y(v): return S(v, oy)

    fill_c  = (255, 255, 255, 175)
    track_c = (255, 255, 255, 55)
    icon_c  = (255, 255, 255, 235)
    dim_c   = (255, 255, 255, 105)

    # progress bar
    px = G_BAR_X0 + (G_BAR_X1 - G_BAR_X0) * max(0.0, min(1.0, progress))
    od.rounded_rectangle([X(G_BAR_X0), Y(G_BAR_Y - 7), X(G_BAR_X1), Y(G_BAR_Y + 7)], radius=7 * SS, fill=track_c)
    if px - G_BAR_X0 > 1:
        od.rounded_rectangle([X(G_BAR_X0), Y(G_BAR_Y - 7), X(max(px, G_BAR_X0 + 14)), Y(G_BAR_Y + 7)], radius=7 * SS, fill=fill_c)
    if not is_live:
        od.rectangle([X(1320), Y(G_BAR_Y - 1), X(1334), Y(G_BAR_Y + 2)], fill=icon_c)   # "-" before remaining time

    # controls row
    cy = 733
    od.polygon([(X(x), Y(y)) for x, y in _star_points(568, cy - 2, 31, 13)], fill=dim_c)           # star
    for base in (722, 764):                                                                       # rewind
        od.polygon([(X(base + 44), Y(cy - 25)), (X(base + 44), Y(cy + 25)), (X(base), Y(cy))], fill=icon_c)
    for dx in (934, 972):                                                                         # pause
        od.rounded_rectangle([X(dx), Y(cy - 38), X(dx + 22), Y(cy + 38)], radius=5 * SS, fill=icon_c)
    for base in (1120, 1162):                                                                     # forward
        od.polygon([(X(base), Y(cy - 25)), (X(base), Y(cy + 25)), (X(base + 44), Y(cy))], fill=icon_c)
    # earbuds icon
    for sgn in (-1, 1):
        ex = 1357 + sgn * 17
        od.ellipse([X(ex - 11), Y(cy - 24), X(ex + 11), Y(cy + 2)], fill=dim_c)
        od.rounded_rectangle([X(ex - 4 + sgn * 6), Y(cy - 6), X(ex + 4 + sgn * 6), Y(cy + 26)], radius=4 * SS, fill=dim_c)

    # volume row
    vk = G_VOL_X0 + (G_VOL_X1 - G_VOL_X0) * 0.36
    od.rounded_rectangle([X(G_VOL_X0), Y(G_VOL_Y - 8), X(G_VOL_X1), Y(G_VOL_Y + 8)], radius=8 * SS, fill=track_c)
    od.rounded_rectangle([X(G_VOL_X0), Y(G_VOL_Y - 8), X(vk), Y(G_VOL_Y + 8)], radius=8 * SS, fill=fill_c)
    sx = 521   # low speaker
    od.polygon([(X(sx), Y(G_VOL_Y - 7)), (X(sx + 8), Y(G_VOL_Y - 7)), (X(sx + 20), Y(G_VOL_Y - 16)),
                (X(sx + 20), Y(G_VOL_Y + 16)), (X(sx + 8), Y(G_VOL_Y + 7)), (X(sx), Y(G_VOL_Y + 7))], fill=dim_c)
    sx = 1361  # loud speaker
    od.polygon([(X(sx), Y(G_VOL_Y - 7)), (X(sx + 8), Y(G_VOL_Y - 7)), (X(sx + 20), Y(G_VOL_Y - 16)),
                (X(sx + 20), Y(G_VOL_Y + 16)), (X(sx + 8), Y(G_VOL_Y + 7)), (X(sx), Y(G_VOL_Y + 7))], fill=dim_c)
    for r in (10, 18, 26):
        od.arc([X(sx + 22 - r), Y(G_VOL_Y - r), X(sx + 22 + r), Y(G_VOL_Y + r)], -48, 48, fill=dim_c, width=3 * SS)

    ov = ov.resize((rw, rh), Image.LANCZOS)
    bg.alpha_composite(ov, (ox, oy))

    # ---- album art ----
    ax0, ay0, ax1, ay1 = G_ART
    am = _g_rr_mask(G_ART, 36)
    sh = Image.new("RGBA", (GW, GH), (0, 0, 0, 0))
    sh.putalpha(am.filter(ImageFilter.GaussianBlur(16)).point(lambda v: int(v * 0.55)))
    sh2 = Image.new("RGBA", (GW, GH), (0, 0, 0, 0))
    sh2.paste(sh, (0, 10))
    bg = Image.alpha_composite(bg, sh2)
    art = ImageOps.fit(src.convert("RGBA"), (ax1 - ax0, ay1 - ay0), Image.LANCZOS)
    bg.paste(art, (ax0, ay0), am.crop((ax0, ay0, ax1, ay1)))

    # ---- text ----
    f_title = ImageFont.truetype(FONT_INFO, 40)
    f_sub   = ImageFont.truetype(FONT_INFO, 27)
    f_time  = ImageFont.truetype(FONT_INFO, 26)
    f_pill  = ImageFont.truetype(FONT_INFO, 24)
    draw = ImageDraw.Draw(bg, "RGBA")

    t = trim_text(_clean_title(title) or "Now Playing", f_title, f_title, G_TXT_MAX)
    draw.text((G_TXT_X, 382), t, font=f_title, fill=(255, 255, 255, 255), anchor="lm")
    sb = trim_text(_clean_title(sub) or "YouTube", f_sub, f_sub, G_TXT_MAX)
    draw.text((G_TXT_X + 2, 438), sb, font=f_sub, fill=(255, 255, 255, 235), anchor="lm")

    draw.text((531, 639), t_left, font=f_time, fill=(255, 255, 255, 120), anchor="lm")
    draw.text((1385, 640), t_right, font=f_time, fill=(255, 255, 255, 235), anchor="rm")

    # ---- bitrate pill (bottom-right) ----
    pl = Image.new("RGBA", (GW * SS, GH * SS), (0, 0, 0, 0))
    ImageDraw.Draw(pl).rounded_rectangle([1718 * SS, 988 * SS, 1865 * SS, 1025 * SS], radius=19 * SS,
                                         fill=(14, 14, 14, 235))
    bg = Image.alpha_composite(bg, pl.resize((GW, GH), Image.LANCZOS))
    draw = ImageDraw.Draw(bg, "RGBA")
    draw.text(((1718 + 1865) / 2, 1007), BITRATE_TEXT, font=f_pill, fill=(255, 255, 255, 255), anchor="mm")
    return bg



async def get_thumb(videoid: str, progress_percent: int = 0, use_cache: bool = True, user_name=None) -> str:
    # user_name = person who requested the song (plain name or markdown/html mention)
    print(f"📥 get_thumb called with videoid: {videoid}")

    timestamp = int(time.time() * 1000)
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_{timestamp}.png")
    thumb_path = os.path.join(CACHE_DIR, f"thumb_{videoid}_{timestamp}.png")

    accent = _next_accent()   # new border colour on every call

    meta = await _fetch_meta_via_search(videoid)
    if meta:
        title, thumbnail_url, duration, views, channel = meta
    else:
        title, thumbnail_url, duration, views, channel = (
            "Song", DIRECT_THUMB_FALLBACK.format(videoid=videoid), None, "Unknown", "YouTube"
        )
        alt = await _fetch_title_via_oembed(videoid)
        if alt:
            title, channel = alt

    is_live = not duration or str(duration).strip().lower() in {"", "live"}
    duration_text = "LIVE" if is_live else str(duration)
    views_text = str(views)
    if "view" not in views_text.lower():
        views_text += " views"

    downloaded = False
    for url in (thumbnail_url, DIRECT_THUMB_FALLBACK.format(videoid=videoid)):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        async with aiofiles.open(thumb_path, "wb") as f:
                            await f.write(await resp.read())
                        downloaded = True
                        break
        except Exception:
            continue

    if not downloaded:
        return YOUTUBE_IMG_URL

    try:
        src = Image.open(thumb_path).convert("RGBA")

        pct = max(0, min(100, int(progress_percent or 0))) / 100.0
        total_s = _to_seconds(duration_text)
        if is_live or not total_s:
            t_left, t_right = "LIVE", ""
        else:
            t_left = _fmt_time(total_s * pct)
            t_right = _fmt_time(max(0, total_s - total_s * pct))

        bg = _draw_glass_player(
            src, title, channel, t_left, t_right, pct if total_s else 0.0, is_live=bool(is_live or not total_s),
        )

        if SHOW_CREDITS:
            draw = ImageDraw.Draw(bg)
            credit_font = ImageFont.truetype(FONT_INFO, 28)
            dw = credit_font.getlength(DEV_TEXT)
            draw.text((GW - 30 - dw, 30), DEV_TEXT, font=credit_font, fill=CREDIT_COLOR)
            draw.text((30, GH - 60), OWNER_TEXT, font=credit_font, fill=CREDIT_COLOR)

        bg.convert("RGB").save(cache_path, "PNG")
        print("✓ Thumbnail saved")

    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
        return YOUTUBE_IMG_URL
    finally:
        try:
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
        except Exception:
            pass

    return cache_path
