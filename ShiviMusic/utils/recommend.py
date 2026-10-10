# ===========================================================
# 🎧 RECOMMENDATIONS — queue khatam hone par "tap below to play
# next track" wala message (Previous + 5 songs + Random AI track)
#
# ✅ Country filter: sirf usi country ke songs (utils/region.py)
# ✅ "More" button: unlimited songs (pool khatam ho to naye Mix se refill)
# ===========================================================

import asyncio
import collections
import itertools
import random
import re
import time

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from py_yt import VideosSearch

from ShiviMusic.utils.autoplay import (
    _extract_candidates,
    _extract_mix_candidates,
    _fetch_mix_sync,
    _history,
)
from ShiviMusic.utils.region import (
    filter_by_region,
    get_seed_region,
    region_label,
)

_NOISE = re.compile(
    r"\((.*?)\)|\[(.*?)\]|\b(?:official|video|audio|lyrical|lyrics|full song|"
    r"hd|4k|music video)\b|\bfeat\.?.*$",
    re.I,
)


def short_title(title: str, limit: int = 30) -> str:
    t = _NOISE.sub("", title or "")
    t = re.sub(r"\s*[|\-–—].*$", lambda m: m.group(0) if len(t) <= limit else "", t)
    t = re.sub(r"\s+", " ", t).strip(" -|")
    t = t or (title or "")
    return (t[: limit - 1] + "…") if len(t) > limit else t


async def _search_fallback(seed_vidid: str, seed_title: str, n: int) -> list:
    """yt_dlp Mix fail (cookies/bot-check) ho to title search se recommendations."""
    try:
        if not seed_title:
            res = await VideosSearch(
                f"https://www.youtube.com/watch?v={seed_vidid}", limit=1
            ).next()
            items = res.get("result", []) if isinstance(res, dict) else []
            seed_title = items[0]["title"] if items else ""
        if not seed_title:
            return []
        res = await VideosSearch(seed_title, limit=20).next()
        items = res.get("result", []) if isinstance(res, dict) else []
    except Exception as e:
        print(f"[RECOMMEND SEARCH ERROR] {type(e).__name__}: {e}")
        return []
    cands = _extract_candidates(items, 0, skip_history=True)
    return [c for c in cands if c["vidid"] != seed_vidid][:n]


_MIX_BAD_UNTIL = 0.0  # Mix fail/timeout ho to kuch der skip (bot-check me atakna nahi)


async def _mix_candidates(seed_vidid: str) -> list:
    global _MIX_BAD_UNTIL
    if time.time() < _MIX_BAD_UNTIL:
        return []
    loop = asyncio.get_event_loop()
    try:
        entries = await asyncio.wait_for(
            loop.run_in_executor(None, _fetch_mix_sync, seed_vidid, 50), 15
        )
    except Exception as e:
        print(f"[RECOMMEND] Mix fail/timeout ({type(e).__name__}: {e}) -> 10 min search mode")
        _MIX_BAD_UNTIL = time.time() + 600
        return []
    cands = _extract_mix_candidates(entries, 0, skip_history=True)
    return [c for c in cands if c["vidid"] != seed_vidid]


async def _fetch_pool(seed_vidid: str, seed_title: str, region) -> list:
    """Seed ka Mix (+ search fallback), country filter ke saath."""
    cands = filter_by_region(await _mix_candidates(seed_vidid), region)

    if len(cands) < 5:
        have = {c["vidid"] for c in cands}
        extra = await _search_fallback(seed_vidid, seed_title, 25)
        extra = [c for c in extra if c["vidid"] not in have]
        cands += filter_by_region(extra, region)
    return cands


async def _search_many(queries: list, region) -> list:
    """Kai searches ek saath (title/channel based), merge + country filter."""

    async def _one(q):
        try:
            res = await asyncio.wait_for(VideosSearch(q, limit=20).next(), 12)
            items = res.get("result", []) if isinstance(res, dict) else []
            return _extract_candidates(items, 0, skip_history=True)
        except Exception as e:
            print(f"[RECOMMEND SEARCH] '{q[:30]}' fail: {type(e).__name__}: {e}")
            return []

    lists = await asyncio.gather(*[_one(q) for q in queries if q])
    merged, seen = [], set()
    for group in itertools.zip_longest(*lists):  # round-robin: variety
        for c in group:
            if c and c["vidid"] not in seen:
                seen.add(c["vidid"])
                merged.append(c)
    return filter_by_region(merged, region)


# ---------------------------------------------------------
# Per-chat state: queue (agle tracks), shown (dikha chuke), region
# ---------------------------------------------------------
_STATE: dict = {}
_SHOWN_LIMIT = 300
_REGION_KEEP_SECS = 30 * 60  # itni der tak purana country filter carry hota hai


def _new_state() -> dict:
    return {"seed": None, "region": (None, None), "queue": [], "shown": [],
            "last": [], "meta": {}, "title": None, "ts": 0}


def _st(chat_id: int) -> dict:
    return _STATE.setdefault(chat_id, _new_state())


def _refill_queries(st: dict, seed_title: str) -> list:
    """Pool khatam hone par naye searches: seed title, dikhaye gaye songs ke
    titles aur sabse common channels (same artist ke aur songs)."""
    meta = st["meta"]
    shown = [v for v in st["shown"] if v in meta]
    qs = [seed_title or st["title"]]
    for v in random.sample(shown, min(3, len(shown))):
        qs.append(meta[v]["title"])
    chans = [m["channel"] for m in meta.values() if m.get("channel")]
    for ch, _ in collections.Counter(chans).most_common(2):
        qs.append(ch)
    out = []
    for q in qs:
        if q and q not in out:
            out.append(q)
    return out[:6]


async def get_more_recommendations(
    chat_id: int, seed_vidid: str, n: int = 5, seed_title: str = None
) -> list:
    """
    "More" button: agle n tracks (same country). Pool khatam ho jaye to naye
    searches/Mix se refill hota hai -> unlimited songs.
    """
    st = _st(chat_id)
    if st["seed"] != seed_vidid:  # state lost (restart) ya naya seed
        keep_title = seed_title or st["title"]
        st.clear()
        st.update(_new_state())
        st.update(seed=seed_vidid, title=keep_title)
        st["region"] = await get_seed_region(seed_vidid, seed_title)

    title = seed_title or st["title"]
    blocked = set(st["shown"]) | set(_history(chat_id)) | {seed_vidid}

    def _add(pool):
        queued = {c["vidid"] for c in st["queue"]}
        for c in pool:
            if c["vidid"] not in blocked and c["vidid"] not in queued:
                st["queue"].append(c)
                st["meta"][c["vidid"]] = {"title": c["title"], "channel": c.get("channel", "")}
                queued.add(c["vidid"])

    async def _refill():
        if len(st["queue"]) < n:
            _add(await _fetch_pool(seed_vidid, title, st["region"]))
        if len(st["queue"]) < n:
            _add(await _search_many(_refill_queries(st, title), st["region"]))

    await _refill()

    if not st["queue"]:
        # Sab kuch dikha chuke -> naya round (sirf abhi wale 5 hatao)
        print("[RECOMMEND] pool khatam -> naya round")
        st["shown"] = list(st["last"])
        blocked = {seed_vidid} | set(st["last"])
        await _refill()

    items, st["queue"] = st["queue"][:n], st["queue"][n:]
    st["last"] = [c["vidid"] for c in items]
    st["shown"] = (st["shown"] + st["last"])[-_SHOWN_LIMIT:]
    st["ts"] = time.time()
    print(f"[RECOMMEND] more -> {len(items)} tracks, queue left {len(st['queue'])}")
    return items


async def fetch_recommendations(
    seed_vidid: str, n: int = 5, seed_title: str = None, chat_id: int = None
) -> list:
    if not seed_vidid:
        return []
    region = await get_seed_region(seed_vidid, seed_title)

    if chat_id is None:
        return (await _fetch_pool(seed_vidid, seed_title, region))[:n]

    st = _st(chat_id)
    old_region, old_ts = st["region"], st["ts"]
    # Naye song ka country pata na chale to pichhla country filter rakho
    # (taaki chain me doosre country ke songs na ghus jaayein)
    if not region[0] and old_region[0] and time.time() - old_ts < _REGION_KEEP_SECS:
        region = old_region
    st.clear()
    st.update(_new_state())
    st.update(seed=seed_vidid, region=region, title=seed_title)
    return await get_more_recommendations(chat_id, seed_vidid, n, seed_title)


def recommend_text(prev_title: str, region=None) -> str:
    label = region_label(region)
    region_line = f"\n<b>🌍 ʀᴇɢɪᴏɴ :</b> <code>{label}</code>" if label else ""
    return (
        "<b>❖ ǫᴜᴇᴜᴇ ᴇɴᴅᴇᴅ</b>\n"
        "<blockquote>"
        f"<b>👑 ᴘʀᴇᴠɪᴏᴜs :</b> <code>{(prev_title or '—')[:40]}…</code>"
        f"{region_line}\n"
        "<b>💡 ᴛᴀᴘ ʙᴇʟᴏᴡ ᴛᴏ ᴘʟᴀʏ ɴᴇxᴛ ᴛʀᴀᴄᴋ</b>"
        "</blockquote>"
    )


def recommend_markup(tracks: list, seed_vidid: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                f"👑 {short_title(t['title'])}",
                callback_data=f"RecPlay {t['vidid']}",
            )
        ]
        for t in tracks
    ]
    rows.append(
        [
            InlineKeyboardButton(
                "🔄 ᴍᴏʀᴇ ʟɪᴋᴇ ᴛʜɪs",
                callback_data=f"RecMore {seed_vidid}",
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                "ᴘʟᴀʏ ʀᴀɴᴅᴏᴍ ᴀɪ ᴛʀᴀᴄᴋ",
                callback_data=f"RecRand {seed_vidid}",
            )
        ]
    )
    rows.append([InlineKeyboardButton("• ᴄʟᴏsᴇ •", callback_data="close")])
    return InlineKeyboardMarkup(rows)


async def send_recommendations(app, original_chat_id: int, popped: dict) -> bool:
    """Queue khatam hone par call.py / skip.py se call hota hai."""
    try:
        seed = popped.get("vidid")
        print(f"[RECOMMEND] queue ended, seed={seed}, chat={original_chat_id}")
        tracks = await fetch_recommendations(
            seed, seed_title=popped.get("title"), chat_id=original_chat_id
        )
        if not tracks:
            print("[RECOMMEND] koi track nahi mila (yt_dlp/cookies/network check karo)")
            return False
        await app.send_message(
            original_chat_id,
            recommend_text(popped.get("title"), _st(original_chat_id)["region"]),
            reply_markup=recommend_markup(tracks, seed),
        )
        print(f"[RECOMMEND] {len(tracks)} tracks bhej diye")
        return True
    except Exception as e:
        print(f"[RECOMMEND ERROR] {type(e).__name__}: {e}")
        return False
