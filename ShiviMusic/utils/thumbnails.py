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
PLAYER_TEXT = "@Kirtiprobot"           # shown in the "Player :" part
CREDIT_COLOR = (255, 241, 0)           # yellow

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# ───────────────────────── Layout ─────────────────────────
W, H = 1280, 720
FRAME_BOX = (186, 88, 1094, 566)       # outer coloured border
FRAME_W   = 33                         # border thickness
IMG_BOX   = (FRAME_BOX[0] + FRAME_W, FRAME_BOX[1] + FRAME_W,
             FRAME_BOX[2] - FRAME_W, FRAME_BOX[3] - FRAME_W)   # 842 x 412 photo area
TITLE_Y   = 580
INFO_Y    = 625
MAX_TITLE_WIDTH = 790

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


def _draw_frame(bg, accent):
    """Soft glowing picture-frame in the accent colour."""
    x0, y0, x1, y1 = FRAME_BOX

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rectangle((x0 - 6, y0 - 6, x1 + 6, y1 + 6), fill=(*accent, 150))
    glow = glow.filter(ImageFilter.GaussianBlur(18))
    bg = Image.alpha_composite(bg, glow)

    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(frame)
    light = _mix(accent, (255, 255, 255), 0.35)
    dark = _mix(accent, (0, 0, 0), 0.35)
    # outer edge -> middle (light) -> inner edge (dark): gives the bevelled look
    for i in range(FRAME_W):
        t = i / (FRAME_W - 1)
        col = _mix(dark, light, t * 2) if t < 0.5 else _mix(light, dark, (t - 0.5) * 2)
        fd.rectangle((x0 + i, y0 + i, x1 - i, y1 - i), outline=(*col, 235), width=1)
    frame = frame.filter(ImageFilter.GaussianBlur(1.2))
    return Image.alpha_composite(bg, frame)


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
    # progress_percent / user_name are kept only so existing callers don't break.
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

        # blurred, darkened background
        bg = ImageOps.fit(src, (W, H), Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(40))
        bg = Image.alpha_composite(bg, Image.new("RGBA", (W, H), (0, 0, 0, 140)))

        # coloured frame
        bg = _draw_frame(bg, accent)

        # photo inside frame (cover-fit, no stretching)
        iw, ih = IMG_BOX[2] - IMG_BOX[0], IMG_BOX[3] - IMG_BOX[1]
        photo = ImageOps.fit(src, (iw, ih), Image.LANCZOS)
        photo = ImageEnhance.Brightness(photo).enhance(1.05)
        bg.paste(photo, (IMG_BOX[0], IMG_BOX[1]))

        draw = ImageDraw.Draw(bg)

        title_font  = ImageFont.truetype(FONT_TITLE, 36)
        hindi_font  = ImageFont.truetype(FONT_INFO, 30)
        info_font   = ImageFont.truetype(FONT_INFO, 23)
        credit_font = ImageFont.truetype(FONT_INFO, 24)
        owner_font  = ImageFont.truetype(FONT_INFO, 25)

        # title (white, centred)
        title = _clean_title(title) or "Now Playing"
        title = trim_text(title, title_font, hindi_font, MAX_TITLE_WIDTH)
        _draw_title(draw, TITLE_Y + 38, title, title_font, hindi_font, "white")

        # info line (tinted with the border colour so it matches every time)
        info_color = _mix(accent, (255, 255, 255), 0.25)
        info = f"YouTube : {views_text} | Time : {duration_text} | Player : {PLAYER_TEXT}"
        _draw_centered(draw, INFO_Y, info, info_font, info_color, shadow=False)

        # credits (fixed yellow)
        dw = credit_font.getlength(DEV_TEXT)
        draw.text((W - 25 - dw + 1, 30 + 1), DEV_TEXT, font=credit_font, fill=(0, 0, 0, 140))
        draw.text((W - 25 - dw, 30), DEV_TEXT, font=credit_font, fill=CREDIT_COLOR)
        draw.text((25 + 1, 672 + 1), OWNER_TEXT, font=owner_font, fill=(0, 0, 0, 140))
        draw.text((25, 672), OWNER_TEXT, font=owner_font, fill=CREDIT_COLOR)

        bg.convert("RGB").save(cache_path, "PNG")
        print(f"✓ Thumbnail saved with border colour RGB{accent}")

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
