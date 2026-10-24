# Welcome message + welcome card PNG for new group members.
#   /welcome        -> status
#   /welcome on|off -> enable / disable in this group (admins only)
import asyncio
import html
import os
import time

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus, ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import BANNED_USERS, OWNER_ID
from ShiviMusic import app
from ShiviMusic.core.mongo import mongodb
from ShiviMusic.logging import LOGGER
from ShiviMusic.misc import SUDOERS
from ShiviMusic.utils.welcome_card import welcomepic

welcomedb = mongodb.welcome_settings
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)
MAX_PER_EVENT = 5          # one "add 20 people" event should not flood the chat


async def _is_on(chat_id: int) -> bool:
    try:
        data = await welcomedb.find_one({"chat_id": chat_id})
    except Exception:
        return True
    return data.get("on", True) if data else True


async def _set_on(chat_id: int, value: bool):
    await welcomedb.update_one({"chat_id": chat_id}, {"$set": {"on": value}}, upsert=True)


async def _is_admin(message: Message) -> bool:
    if not message.from_user:                       # anonymous admin
        return bool(message.sender_chat and message.sender_chat.id == message.chat.id)
    uid = message.from_user.id
    if uid == OWNER_ID or uid in SUDOERS:
        return True
    try:
        m = await app.get_chat_member(message.chat.id, uid)
        return m.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR)
    except Exception:
        return False


async def _download_photo(user):
    """Profile photo -> local path, or None."""
    stamp = int(time.time() * 1000)
    path = os.path.join(CACHE_DIR, f"pf_{user.id}_{stamp}.jpg")
    try:
        if user.photo:
            got = await app.download_media(user.photo.big_file_id, file_name=path)
            if got:
                return got
    except Exception:
        pass
    try:
        async for p in app.get_chat_photos(user.id, limit=1):
            got = await app.download_media(p.file_id, file_name=path)
            if got:
                return got
    except Exception:
        pass
    return None


def _caption(user, chat, count):
    full = " ".join(x for x in (user.first_name, user.last_name) if x).strip() or "User"
    name = f'<a href="tg://user?id={user.id}">{html.escape(full)}</a>'
    title = html.escape((chat.title or "ᴛʜɪs ᴄʜᴀᴛ")[:40])
    uname = f"@{user.username}" if user.username else "ɴᴏ ᴜsᴇʀɴᴀᴍᴇ"
    return (
        "🦚❁—✦ ʀᴀᴅʜᴇ ʀᴀᴅʜᴇ ✦—❁🦚\n"
        f"ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ {title} 💗💌🪈\n"
        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"🌸 ɴᴀᴍᴇ ➪ {name}\n"
        f"🦋 ɪᴅ ➪ <code>{user.id}</code>\n"
        f"💙 ᴜsᴇʀ ➪ {uname}\n"
        f"👥 ᴍᴇᴍʙᴇʀs ➪ {count}\n"
        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        "❁──────✧❁✦❁✧──────❁\n"
        "🌙 ᴋʀɪsʜɴᴀ ʙʟᴇssɪɴɢs ᴀʟᴡᴀʏs\n"
        "💫 sᴘʀᴇᴀᴅ ʟᴏᴠᴇ ᴇᴠᴇʀʏᴡʜᴇʀᴇ\n"
        "🦚 ✧ ᴊᴀɪ sʜʀᴇᴇ ᴋʀɪsʜɴᴀ ✧ 🦚"
    )


def _buttons(user, with_view=True):
    rows = []
    if with_view:
        link = f"https://t.me/{user.username}" if user.username else f"tg://user?id={user.id}"
        rows.append([InlineKeyboardButton("🦚 ᴠɪᴇᴡ ɴᴇᴡ ᴍᴇᴍʙᴇʀ 🦚", url=link)])
    bot_user = getattr(app, "username", None)
    if bot_user:
        rows.append([InlineKeyboardButton("🪈 ᴋɪᴅɴᴀᴘ ᴍᴇ 🪈", url=f"https://t.me/{bot_user}?startgroup=true")])
    return InlineKeyboardMarkup(rows) if rows else None


async def _send_welcome(message: Message, user):
    chat = message.chat
    try:
        count = await app.get_chat_members_count(chat.id)
    except Exception:
        count = "?"
    caption = _caption(user, chat, count)

    photo_path = await _download_photo(user)
    card_path = os.path.join(CACHE_DIR, f"welcome_{chat.id}_{user.id}_{int(time.time() * 1000)}.png")
    card = None
    try:
        loop = asyncio.get_running_loop()
        full = " ".join(x for x in (user.first_name, user.last_name) if x)
        card = await loop.run_in_executor(None, welcomepic, photo_path, full, user.id, user.username, card_path)
    except Exception as e:
        LOGGER(__name__).warning(f"[WELCOME] card failed: {type(e).__name__}: {e}")

    try:
        for with_view in (True, False):      # retry without the profile button (privacy restricted users)
            try:
                if card:
                    await app.send_photo(chat.id, photo=card, caption=caption,
                                         reply_markup=_buttons(user, with_view), parse_mode=ParseMode.HTML)
                else:
                    await app.send_message(chat.id, caption, reply_markup=_buttons(user, with_view),
                                           parse_mode=ParseMode.HTML, disable_web_page_preview=True)
                break
            except Exception as e:
                if with_view and "BUTTON" in str(e).upper():
                    continue
                raise
    except Exception as e:
        LOGGER(__name__).warning(f"[WELCOME] send failed in {chat.id}: {type(e).__name__}: {e}")
    finally:
        for f in (photo_path, card):
            try:
                if f and os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass


@app.on_message(filters.new_chat_members & filters.group, group=7)
async def welcome_new_members(_, message: Message):
    try:
        if not await _is_on(message.chat.id):
            return
        me_id = app.me.id if getattr(app, "me", None) else None
        users = [u for u in message.new_chat_members if not u.is_bot and u.id != me_id][:MAX_PER_EVENT]
        for u in users:
            await _send_welcome(message, u)
    except Exception as e:
        LOGGER(__name__).warning(f"[WELCOME] handler error: {type(e).__name__}: {e}")


@app.on_message(filters.command(["welcome"]) & filters.group & ~BANNED_USERS)
async def welcome_toggle(_, message: Message):
    if not await _is_admin(message):
        return await message.reply_text("ᴏɴʟʏ ᴀᴅᴍɪɴs ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ.")
    arg = message.command[1].lower() if len(message.command) > 1 else ""
    if arg in ("on", "enable", "yes"):
        await _set_on(message.chat.id, True)
        return await message.reply_text("✅ ᴡᴇʟᴄᴏᴍᴇ ᴍᴇssᴀɢᴇ ᴇɴᴀʙʟᴇᴅ.")
    if arg in ("off", "disable", "no"):
        await _set_on(message.chat.id, False)
        return await message.reply_text("❌ ᴡᴇʟᴄᴏᴍᴇ ᴍᴇssᴀɢᴇ ᴅɪsᴀʙʟᴇᴅ.")
    state = "ᴏɴ ✅" if await _is_on(message.chat.id) else "ᴏғғ ❌"
    await message.reply_text(f"ᴡᴇʟᴄᴏᴍᴇ ɪs {state}\n\nᴜsᴀɢᴇ: <code>/welcome on</code> | <code>/welcome off</code>",
                             parse_mode=ParseMode.HTML)

