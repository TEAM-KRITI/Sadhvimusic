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
AB_INTERVAL_MIN = 240  # 240 min = 4 ghante -> 24 ghante mein 6 broadcast
AB_TARGET = "chats"  # "chats" | "users" | "both"
AB_SEND_ON_RESTART = True  # bot restart/start hote hi 1 message turant jaye
AB_LINK = "https://t.me/kirti_bots"  # Kirti Bots ka link

# Photo ka link (ya file_id). Photo nahi chahiye to "" kar do.
AB_PHOTO = config.START_IMG_URL

# Message (HTML allowed: <b>bold</b>, <i>italic</i>, <a href="...">link</a>)
AB_TEXT = f"""<b>🎵 ᴍᴜsɪᴄ ʙᴏᴛ ᴋᴀ ᴍᴀᴢᴀ ʟᴏ!</b>

ʜᴀᴍᴀʀᴇ ʙᴏᴛ sᴇ ɢʀᴏᴜᴘ ᴠᴄ ᴍᴇ ʜɪɢʜ ǫᴜᴀʟɪᴛʏ ɢᴀᴀɴᴇ ʙᴀᴊᴀᴏ 🔥

» ʏᴏᴜᴛᴜʙᴇ, sᴘᴏᴛɪғʏ, ᴀᴘᴘʟᴇ, sᴏᴜɴᴅᴄʟᴏᴜᴅ sᴀʙ sᴜᴘᴘᴏʀᴛ
» ᴀᴜᴛᴏᴘʟᴀʏ, ǫᴜᴇᴜᴇ, sᴇᴇᴋ, sᴘᴇᴇᴅ ᴄᴏɴᴛʀᴏʟ
» ᴏɴʟʏ /play ʟɪᴋʜᴏ ᴀᴜʀ ᴍᴜsɪᴄ ᴇɴᴊᴏʏ ᴋᴀʀᴏ

💬 sᴜᴘᴘᴏʀᴛ : <a href="{config.SUPPORT_CHAT}">ᴊᴏɪɴ ʜᴇʀᴇ</a>
📢 ᴜᴘᴅᴀᴛᴇs : <a href="{AB_LINK}">ᴋɪʀᴛɪ ʙᴏᴛs</a>

<i>ᴍᴀᴅᴇ ʙʏ <a href="{AB_LINK}">ᴋɪʀᴛɪ ʙᴏᴛs</a></i>"""
# ---------------------------------------------------------------

abdb = mongodb.autobroadcast
_KEY = {"_id": "state"}
_lock = asyncio.Lock()


async def _last_sent() -> int:
    data = await abdb.find_one(_KEY) or {}
    return int(data.get("last_sent", 0))


async def _mark_sent():
    await abdb.update_one(_KEY, {"$set": {"last_sent": int(time.time())}}, upsert=True)


def _buttons():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ ᴀᴅᴅ ᴍᴇ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ",
                    url=f"https://t.me/{app.username}?startgroup=true",
                )
            ],
            [InlineKeyboardButton("ᴋɪʀᴛɪ ʙᴏᴛs", url=AB_LINK)],
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


async def _broadcast() -> tuple:
    async with _lock:
        await _mark_sent()
        targets = []
        if AB_TARGET in ("chats", "both"):
            targets += [int(c["chat_id"]) for c in await get_served_chats()]
        if AB_TARGET in ("users", "both"):
            targets += [int(u["user_id"]) for u in await get_served_users()]

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
    sent, failed = await _broadcast()
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
