# ===========================================================
# ©️ 2025-26 All Rights Reserved by Purvi Bots (Im-Notcoder) 🚀
#
# This source code is under MIT License 📜
# ❌ Unauthorized forking, importing, or using this code
#    without giving proper credit will result in legal action ⚠️
#
# 📩 DM for permission : @TheSigmaCoder
# ===========================================================

import asyncio
import glob
import os
import random
import re

import yt_dlp
from py_yt import VideosSearch

from ShiviMusic.utils.region import filter_by_region, get_seed_region

# =========================================================
# PER-CHAT PLAY HISTORY (in-memory, session based)
# Used only to make sure autoplay never repeats a song it
# already played for that chat.
# =========================================================
_HISTORY_LIMIT = 100
_KEEP_ON_RESET = 15  # history reset par bhi itne latest songs yaad rahenge
_played_history: dict[int, list[str]] = {}
_played_titles: dict[int, list[str]] = {}

_NOISE = re.compile(
    r"\(.*?\)|\[.*?\]|official|video|audio|lyrics?|lyrical|full song|"
    r"hd|4k|with lyrics|song|music|\bft\b.*|\bfeat\b.*",
    re.IGNORECASE,
)


def _title_key(title) -> str:
    """Same song ke alag-alag uploads (lyrics/official/audio) ko ek hi key do."""
    if not title:
        return ""
    t = _NOISE.sub(" ", str(title).lower())
    t = re.sub(r"[^\w\s]", " ", t)
    return " ".join(t.split())


def remember_played(chat_id: int, vidid: str, title: str = None):
    if vidid:
        hist = _played_history.setdefault(chat_id, [])
        if vidid in hist:
            hist.remove(vidid)
        hist.append(vidid)
        if len(hist) > _HISTORY_LIMIT:
            del hist[: len(hist) - _HISTORY_LIMIT]
    key = _title_key(title)
    if key:
        th = _played_titles.setdefault(chat_id, [])
        if key in th:
            th.remove(key)
        th.append(key)
        if len(th) > _HISTORY_LIMIT:
            del th[: len(th) - _HISTORY_LIMIT]


def _history(chat_id: int) -> list:
    return _played_history.get(chat_id, [])


def _titles(chat_id: int) -> list:
    return _played_titles.get(chat_id, [])


def clear_history(chat_id: int):
    """Poori history nahi, sirf purani hatao - latest songs repeat na hon."""
    hist = _played_history.get(chat_id)
    if hist:
        _played_history[chat_id] = hist[-_KEEP_ON_RESET:]
    th = _played_titles.get(chat_id)
    if th:
        _played_titles[chat_id] = th[-_KEEP_ON_RESET:]


def _is_played(chat_id: int, vidid: str, title: str, seed_vidid: str, skip_history: bool) -> bool:
    if seed_vidid and vidid == seed_vidid:
        return True  # abhi bajne wala/bajaya hua gaana kabhi nahi
    if skip_history:
        return False
    if vidid in _history(chat_id):
        return True
    key = _title_key(title)
    return bool(key) and key in _titles(chat_id)


def _extract_candidates(results, chat_id: int, skip_history: bool, seed_vidid: str = None):
    candidates = []
    for video in results:
        vidid = video.get("id")
        title = video.get("title")
        link = video.get("link")
        duration = video.get("duration")
        if not (vidid and title and link and duration):
            continue
        if _is_played(chat_id, vidid, title, seed_vidid, skip_history):
            continue
        thumbs = video.get("thumbnails") or []
        thumb = thumbs[0].get("url", "").split("?")[0] if thumbs else None
        ch = video.get("channel") or {}
        channel = ch.get("name", "") if isinstance(ch, dict) else str(ch)
        candidates.append(
            {
                "vidid": vidid,
                "title": title,
                "channel": channel,
                "link": link,
                "duration_min": duration,
                "thumb": thumb,
            }
        )
    return candidates


# =========================================================
# ASHOK-STYLE: YouTube Mix playlist ("RD" + videoID)
# Genuinely YouTube's own "related songs" algorithm — much
# better variety than a plain title-text search, which often
# just returns covers/remixes of the same song.
# =========================================================

def _cookie_file():
    folder = os.path.join(os.getcwd(), "ShiviMusic", "assets")
    txt_files = glob.glob(os.path.join(folder, "*.txt"))
    if not txt_files:
        return None
    return random.choice(txt_files)


def _fetch_mix_sync(video_id: str, limit: int = 20) -> list:
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
        "playlistend": limit,
        "no_warnings": True,
    }
    cookiefile = _cookie_file()
    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile
    url = f"https://www.youtube.com/watch?v={video_id}&list=RD{video_id}"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return (info or {}).get("entries") or []


def _extract_mix_candidates(entries, chat_id: int, skip_history: bool, seed_vidid: str = None):
    candidates = []
    for e in entries or []:
        if not e:
            continue
        vidid = e.get("id")
        title = e.get("title")
        if not (vidid and title):
            continue
        if _is_played(chat_id, vidid, title, seed_vidid, skip_history):
            continue
        duration = e.get("duration")
        if isinstance(duration, (int, float)):
            m, s = divmod(int(duration), 60)
            duration_min = f"{m}:{s:02d}"
        else:
            duration_min = str(duration) if duration else "Live"
        candidates.append(
            {
                "vidid": vidid,
                "title": title,
                "channel": e.get("channel") or e.get("uploader") or "",
                "link": f"https://www.youtube.com/watch?v={vidid}",
                "duration_min": duration_min,
                "thumb": e.get("thumbnail")
                or f"https://i.ytimg.com/vi/{vidid}/hqdefault.jpg",
            }
        )
    return candidates


async def _fetch_mix_candidates(chat_id: int, seed_vidid: str, region=None) -> list:
    """
    Seed ka Mix -> country filter. Unlimited songs ke liye: agar seed ka Mix
    khatam ho gaya (sab played/filtered), to pichhle played songs ko seed bana
    kar naye Mix fetch karta hai, aur last me history reset karta hai.
    """
    loop = asyncio.get_event_loop()
    seeds = [seed_vidid]
    recent = [v for v in _history(chat_id) if v != seed_vidid]
    random.shuffle(recent)
    seeds += recent[:3]

    last_entries = []
    for seed in seeds:
        try:
            entries = await loop.run_in_executor(None, _fetch_mix_sync, seed, 30)
        except Exception as e:
            print(f"[AUTOPLAY MIX ERROR] {e}")
            continue
        last_entries = entries or last_entries
        candidates = _extract_mix_candidates(entries, chat_id, False, seed_vidid)
        candidates = filter_by_region(candidates, region)
        if candidates:
            return candidates

    if last_entries:
        # Sab kuch already played -> history reset karke dobara try karo,
        # taaki autoplay kabhi stall na ho
        clear_history(chat_id)
        return filter_by_region(
            _extract_mix_candidates(last_entries, chat_id, False, seed_vidid), region
        )
    return []


def _pick(candidates: list) -> dict:
    # Pehle same language/country wale (rank 0/1) me se random, warna baaki
    best = [c for c in candidates if c.get("rank", 0) <= 1] or candidates
    return random.choice(best)


async def fetch_autoplay_track(chat_id: int, seed_title: str, seed_vidid: str = None):
    """
    Primary: seed video ka YouTube "Mix"/radio playlist ("RD" + videoID),
    phir country filter (same country ke songs hi), phir random pick.
    Fallback: title-text search (wo bhi country filter ke saath).
    """
    region = await get_seed_region(seed_vidid, seed_title)

    if seed_vidid:
        mix_candidates = await _fetch_mix_candidates(chat_id, seed_vidid, region)
        if mix_candidates:
            return _pick(mix_candidates)

    if not seed_title:
        return None

    query = f"{seed_title}"
    try:
        search = VideosSearch(query, limit=20)
        data = await search.next()
        results = data.get("result", []) if isinstance(data, dict) else []
    except Exception as e:
        print(f"[AUTOPLAY SEARCH ERROR] {e}")
        return None

    if not results:
        return None

    candidates = filter_by_region(
        _extract_candidates(results, chat_id, False, seed_vidid), region
    )

    if not candidates:
        clear_history(chat_id)
        candidates = filter_by_region(
            _extract_candidates(results, chat_id, False, seed_vidid), region
        )

    if not candidates:
        return None

    return _pick(candidates)

# ===========================================================
# ©️ 2025-26 All Rights Reserved by Purvi Bots (Im-Notcoder) 😎
#
# 🧑‍💻 Developer : t.me/TheSigmaCoder
# 🔗 Source link : GitHub.com/Im-Notcoder/Shivi-V2
# 📢 Telegram channel : t.me/Purvi_Bots
# ===========================================================
