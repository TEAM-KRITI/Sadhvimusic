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
    r, g, b = colorsys.hsv_to_rgb(hue, random.uniform(0.45, 0.8), random.uniform(0.85, 1.0))
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


def _draw_player(bg, accent, accent2, src, title, sub, title_color, t_left, t_right, progress):
    """iPhone-style 'now playing' card. Colours come from accent/accent2 (new every call)."""
    # ---- background: blurred cover + colour wash (changes every time) ----
    wash = Image.new("RGBA", (W, H))
    wd = ImageDraw.Draw(wash)
    for y in range(H):
        t = y / (H - 1)
        wd.line([(0, y), (W, y)], fill=(*_mix(accent, accent2, t), 150))
    bg = Image.alpha_composite(bg, wash)

    # ---- card shadow ----
    cm = _rr_mask(CARD, CARD_R)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.putalpha(cm.filter(ImageFilter.GaussianBlur(26)).point(lambda v: int(v * 0.55)))
    sh2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh2.paste(shadow, (0, 16))
    bg = Image.alpha_composite(bg, sh2)

    # ---- frosted glass card ----
    glass = bg.filter(ImageFilter.GaussianBlur(28))
    tint = Image.new("RGBA", (W, H), (*_mix(accent, (20, 20, 28), 0.55), 120))
    glass = Image.alpha_composite(glass, tint)
    bg.paste(glass, (0, 0), cm)

    # ---- everything shape-like drawn at 2x then downsampled ----
    ov = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)

    def S(v): return int(v * SS)

    od.rounded_rectangle([S(v) for v in CARD], radius=S(CARD_R), outline=(255, 255, 255, 70), width=S(2))

    white = (255, 255, 255, 255)
    soft = (255, 255, 255, 105)

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
    od.rounded_rectangle([S(_X(467)), S(hy - 3), S(_X(571)), S(hy + 3)], radius=S(3), fill=(255, 255, 255, 200))

    ov = ov.resize((W, H), Image.LANCZOS)
    bg = Image.alpha_composite(bg, ov)

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
    draw = ImageDraw.Draw(bg)
    f_title = ImageFont.truetype(FONT_INFO, 31)
    f_hi    = ImageFont.truetype(FONT_INFO, 28)
    f_sub   = ImageFont.truetype(FONT_INFO, 26)
    f_time  = ImageFont.truetype(FONT_INFO, 20)

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
    draw.text((TXT_X, _Y(138) + 8), sub, font=f_sub, fill=(255, 255, 255, 190), anchor="lm")

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


async def get_thumb(videoid: str, progress_percent: int = 0, use_cache: bool = True, user_name: str = "Badnam") -> str:
    # user_name is kept only so existing callers don't break.
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

        # blurred, darkened background from the song cover
        bg = ImageOps.fit(src, (W, H), Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(40))
        bg = Image.alpha_composite(bg, Image.new("RGBA", (W, H), (0, 0, 0, 120)))

        accent2 = _accent2(accent)
        sub = f"{channel} — {views_text}"
        pct = max(0, min(100, int(progress_percent or 0))) / 100.0
        total_s = _to_seconds(duration_text)
        t_left = _fmt_time(total_s * pct) if total_s else "0:00"
        t_right = duration_text

        bg = _draw_player(
            bg, accent, accent2, src, title, sub, _next_title_color(accent),
            t_left, t_right, pct if total_s else 0.0,
        )

        # credits (fixed yellow)
        draw = ImageDraw.Draw(bg)
        credit_font = ImageFont.truetype(FONT_INFO, 24)
        owner_font  = ImageFont.truetype(FONT_INFO, 25)
        dw = credit_font.getlength(DEV_TEXT)
        draw.text((W - 25 - dw + 1, 30 + 1), DEV_TEXT, font=credit_font, fill=(0, 0, 0, 140))
        draw.text((W - 25 - dw, 30), DEV_TEXT, font=credit_font, fill=CREDIT_COLOR)
        draw.text((25 + 1, 672 + 1), OWNER_TEXT, font=owner_font, fill=(0, 0, 0, 140))
        draw.text((25, 672), OWNER_TEXT, font=owner_font, fill=CREDIT_COLOR)

        bg.convert("RGB").save(cache_path, "PNG")
        print(f"✓ Thumbnail saved with colour RGB{accent}")

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
