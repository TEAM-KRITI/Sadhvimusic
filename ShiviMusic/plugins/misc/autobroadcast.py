# ===========================================================
# Auto Broadcast - message + photo fixed in this file
# Koi command se set karne ki zarurat nahi. Neeche AB_TEXT / AB_PHOTO
# badal do, bas. Bot start hone ke baad apne aap chalta rahega.
#
# Extra commands (sudo only):
#   /abnow     - abhi turant broadcast
#   /abstatus  - settings + agla broadcast kab
# ===========================================================

import asyncio
import time

from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import config
from ShiviMusic import LOGGER, app
from ShiviMusic.core.mongo import mongodb
from ShiviMusic.misc import SUDOERS
from ShiviMusic.utils.database import get_served_chats, get_served_users

# ---------------------------------------------------------------
# ✏️ SETTINGS - yahin se sab badlo
# ---------------------------------------------------------------
AB_ENABLED = True  # False karo to auto broadcast band
AB_INTERVAL_MIN = 1440  # 1440 min = 24 ghante -> din mein sirf 1 broadcast
AB_TARGET = "both"  # "chats" | "users" | "both"  (both = group + user dono)
AB_SEND_ON_RESTART = False  # False = restart ke baad broadcast nahi jayega
AB_MIN_GAP_MIN = AB_INTERVAL_MIN  # itne minute ke andar dobara auto-broadcast nahi jayega

# Photo ka link (ya file_id). Photo nahi chahiye to "" kar do.
AB_PHOTO = config.START_IMG_URL

# "BUY TG ACCOUNT FROM HERE" button ka link - yahan apna link daalo
AB_BUY_URL = f"https://t.me/{config.OWNER_USERNAME}"

# Message - poora BOLD (HTML: <b>bold</b>, <blockquote>, <blockquote expandable>)
AB_TEXT = (
    "<blockquote><b>🎧 ʜᴇʏ ᴛʜᴇʀᴇ 👋</b></blockquote>\n"
    "<blockquote expandable><b>"
    f"✨ ᴅɪᴅ ʏᴏᴜ ᴋɴᴏᴡ? {config.BOT_NAME}...\n"
    "ᴅᴇʟɪᴠᴇʀs ᴄʀʏsᴛᴀʟ-ᴄʟᴇᴀʀ, ʜɪ-ʀᴇs ᴍᴜsɪᴄ sᴛʀᴇᴀᴍɪɴɢ ᴡɪᴛʜ ᴢᴇʀᴏ ᴅᴇʟᴀʏ, "
    "ʀɪɢʜᴛ ɪɴsɪᴅᴇ ʏᴏᴜʀ ᴛᴇʟᴇɢʀᴀᴍ ɢʀᴏᴜᴘs & ᴄʜᴀɴɴᴇʟs 🎵\n\n"
    "ғʀᴏᴍ 24/7 ɴᴏɴ-sᴛᴏᴘ sᴛʀᴇᴀᴍɪɴɢ ᴛᴏ ᴀ ʙᴜᴛᴛᴇʀ-sᴍᴏᴏᴛʜ ǫᴜᴇᴜᴇ sʏsᴛᴇᴍ, "
    "ᴇᴠᴇʀʏᴛʜɪɴɢ ɪs ʙᴜɪʟᴛ ᴛᴏ ᴋᴇᴇᴘ ʏᴏᴜʀ ᴠɪʙᴇ ᴀʟɪᴠᴇ ᴡɪᴛʜᴏᴜᴛ ᴀɴʏ ʟᴀɢ 🔥\n\n"
    "▸ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ ᴀɴᴅ ʟᴇᴛ ᴛʜᴇ ᴍᴜsɪᴄ ɴᴇᴠᴇʀ sᴛᴏᴘ 🚀"
    "</b></blockquote>"
)
# ---------------------------------------------------------------

abdb = mongodb.autobroadcast
_KEY = {"_id": "state"}
_lock = asyncio.Lock()


async def _last_sent() -> int:
    data = await abdb.find_one(_KEY) or {}
    return int(data.get("last_sent", 0))


async def _claim(force: bool = False) -> bool:
    """Atomic claim - do process/dyno ek saath chalein to bhi sirf ek hi broadcast jayega."""
    now = int(time.time())
    if force:
        await abdb.update_one(_KEY, {"$set": {"last_sent": now}}, upsert=True)
        return True
    gap = max(AB_MIN_GAP_MIN * 60, 1)
    try:
        res = await abdb.update_one(
            {"_id": "state", "$or": [{"last_sent": {"$lte": now - gap}}, {"last_sent": {"$exists": False}}]},
            {"$set": {"last_sent": now}},
            upsert=True,
        )
        return bool(res.modified_count or res.upserted_id)
    except Exception:
        # DuplicateKeyError => kisi aur ne abhi claim kar liya
        return False


def _buttons():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ ᴀᴅᴅ ᴍᴇ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ",
                    url=f"https://t.me/{app.username}?startgroup=true",
                )
            ],
            [InlineKeyboardButton("🛒 sᴏᴜᴘᴘʀᴛ ᴄʜᴀᴛ ᴋɪʀᴛɪ", url=AB_BUY_URL)],
        ]
    )


async def _send(chat_id: int):
    if AB_PHOTO:
        await app.send_photo(
            chat_id,
            AB_PHOTO,
            caption=AB_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=_buttons(),
        )
    else:
        await app.send_message(
            chat_id,
            AB_TEXT,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=_buttons(),
        )


async def _broadcast(force: bool = False) -> tuple:
    if _lock.locked():
        return 0, 0
    async with _lock:
        if not await _claim(force):
            return 0, 0
        targets = []
        if AB_TARGET in ("chats", "both"):
            targets += [int(c["chat_id"]) for c in await get_served_chats()]
        if AB_TARGET in ("users", "both"):
            targets += [int(u["user_id"]) for u in await get_served_users()]
        # duplicate hatao (ek chat/user ko ek hi baar jaye)
        targets = list(dict.fromkeys(targets))

        sent = failed = 0
        for chat_id in targets:
            try:
                await _send(chat_id)
                sent += 1
            except FloodWait as fw:
                if fw.value > 200:
                    failed += 1
                else:
                    await asyncio.sleep(fw.value)
                    try:
                        await _send(chat_id)
                        sent += 1
                    except Exception:
                        failed += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.3)

    try:
        await app.send_message(
            config.LOGGER_ID,
            f"<b>» ᴀᴜᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ ᴅᴏɴᴇ</b>\n\nsᴇɴᴛ : <code>{sent}</code>\nғᴀɪʟᴇᴅ : <code>{failed}</code>",
        )
    except Exception:
        pass
    return sent, failed


@app.on_message(filters.command("abnow") & SUDOERS)
async def ab_now(client, message):
    if _lock.locked():
        return await message.reply_text("⏳ ʙʀᴏᴀᴅᴄᴀsᴛ ᴀʟʀᴇᴀᴅʏ ʀᴜɴɴɪɴɢ.")
    m = await message.reply_text("📢 ʙʀᴏᴀᴅᴄᴀsᴛ sᴛᴀʀᴛ...")
    sent, failed = await _broadcast(force=True)
    await m.edit_text(
        f"✅ ᴅᴏɴᴇ\n\nsᴇɴᴛ : <code>{sent}</code>\nғᴀɪʟᴇᴅ : <code>{failed}</code>"
    )


@app.on_message(filters.command("abstatus") & SUDOERS)
async def ab_status(client, message):
    last = await _last_sent()
    left = max(0, int(last + AB_INTERVAL_MIN * 60 - time.time())) if last else 0
    await message.reply_text(
        "<b>» ᴀᴜᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ</b>\n\n"
        f"sᴛᴀᴛᴜs : <code>{'ON' if AB_ENABLED else 'OFF'}</code>\n"
        f"ɪɴᴛᴇʀᴠᴀʟ : <code>{AB_INTERVAL_MIN}</code> ᴍɪɴ\n"
        f"ᴛᴀʀɢᴇᴛ : <code>{AB_TARGET}</code>\n"
        f"ᴘʜᴏᴛᴏ : <code>{'yes' if AB_PHOTO else 'no'}</code>\n"
        f"ɴᴇxᴛ ɪɴ : <code>{left // 60}</code> ᴍɪɴ"
    )


async def _scheduler():
    await asyncio.sleep(30)
    if AB_ENABLED and AB_SEND_ON_RESTART:
        try:
            await _broadcast()
        except Exception as e:
            LOGGER(__name__).error(f"Auto broadcast (restart) error: {e}")
    if await _last_sent() == 0:
        await _claim(force=True)  # pehli baar: restart pe nahi bhejna, 24h ki ghadi yahin se shuru
    while True:
        try:
            if (
                AB_ENABLED
                and not _lock.locked()
                and time.time() - await _last_sent() >= AB_INTERVAL_MIN * 60
            ):
                await _broadcast()
        except Exception as e:
            LOGGER(__name__).error(f"Auto broadcast error: {e}")
        await asyncio.sleep(30)


asyncio.create_task(_scheduler())
