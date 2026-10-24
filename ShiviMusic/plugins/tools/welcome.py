# Welcome message + welcome card PNG for new group members.
#   /welcome         -> status
#   /welcome on|off  -> enable / disable in this group (admins only)
#   /welcome test    -> send a test welcome for yourself and show any error (admins only)
import asyncio
import html
import os
import time
import traceback

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus, ChatType, ParseMode
from pyrogram.types import ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import BANNED_USERS, OWNER_ID
from ShiviMusic import app
from ShiviMusic.core.mongo import mongodb
from ShiviMusic.logging import LOGGER
from ShiviMusic.misc import SUDOERS
from ShiviMusic.utils.welcome_card import welcomepic

welcomedb = mongodb.welcome_settings

# NOTE: must NOT be "cache/" - the bot's send_photo wrapper treats "cache/..." as a song
# thumbnail and sends text only when /thumb is off in that chat.
WELCOME_DIR = "welcome_tmp"
os.makedirs(WELCOME_DIR, exist_ok=True)
MAX_PER_EVENT = 5          # one "add 20 people" event should not flood the chat
DELETE_AFTER = 120         # seconds - welcome message is deleted automatically (0 = never)
_bg_tasks = set()          # keep references so delete tasks are not garbage collected
_recent = {}               # (chat_id, user_id) -> time; stops double welcome (service msg + member update)
DEDUPE_SECONDS = 60


def _claim(chat_id: int, user_id: int) -> bool:
    """True only for the first of the two join signals (service message / chat_member update)."""
    now = time.time()
    for k in [k for k, t in _recent.items() if now - t > DEDUPE_SECONDS]:
        _recent.pop(k, None)
    if (chat_id, user_id) in _recent:
        return False
    _recent[(chat_id, user_id)] = now
    return True


async def _delete_later(msg, delay):
    try:
        await asyncio.sleep(delay)
        await msg.delete()
    except Exception:
        pass


def _schedule_delete(msg):
    if not msg or DELETE_AFTER <= 0:
        return
    task = asyncio.create_task(_delete_later(msg, DELETE_AFTER))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)


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
    path = os.path.join(WELCOME_DIR, f"pf_{user.id}_{stamp}.jpg")
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
    body = (
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
    return f"<b>{body}</b>"          # whole message in bold


def _buttons(user, with_view=True):
    rows = []
    if with_view:
        link = f"https://t.me/{user.username}" if user.username else f"tg://user?id={user.id}"
        rows.append([InlineKeyboardButton("🦚 ᴠɪᴇᴡ ɴᴇᴡ ᴍᴇᴍʙᴇʀ 🦚", url=link)])
    bot_user = getattr(app, "username", None)
    if bot_user:
        rows.append([InlineKeyboardButton("🪈 ᴋɪᴅɴᴀᴘ ᴍᴇ 🪈", url=f"https://t.me/{bot_user}?startgroup=true")])
    return InlineKeyboardMarkup(rows) if rows else None


async def _send(chat_id, caption, user, image=None):
    """Send image (or plain text when image is None). Retries without the profile button
    for users whose privacy settings reject tg://user buttons."""
    for with_view in (True, False):
        try:
            if image:
                return await app.send_photo(chat_id, photo=image, caption=caption,
                                            reply_markup=_buttons(user, with_view), parse_mode=ParseMode.HTML)
            return await app.send_message(chat_id, caption, reply_markup=_buttons(user, with_view),
                                          parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        except Exception as e:
            if with_view and "BUTTON" in str(e).upper():
                continue
            raise


async def _send_welcome(chat, user, report_to: Message = None):
    """report_to=<Message> (used by /welcome test) also posts any error into the chat."""
    try:
        count = await app.get_chat_members_count(chat.id)
    except Exception:
        count = "?"
    caption = _caption(user, chat, count)

    photo_path = await _download_photo(user)
    card_path = os.path.join(WELCOME_DIR, f"welcome_{chat.id}_{user.id}_{int(time.time() * 1000)}.png")
    card = None
    errors = []
    sent = None
    try:
        loop = asyncio.get_running_loop()
        full = " ".join(x for x in (user.first_name, user.last_name) if x)
        card = await loop.run_in_executor(None, welcomepic, photo_path, full, user.id, user.username, card_path)
    except Exception as e:
        errors.append(f"card: {type(e).__name__}: {e}")
        LOGGER(__name__).error(f"[WELCOME] card failed:\n{traceback.format_exc()}")

    try:
        try:
            sent = await _send(chat.id, caption, user, card or photo_path)     # 1) card PNG (or profile photo if card failed)
        except Exception as e:
            errors.append(f"send card: {type(e).__name__}: {e}")
            LOGGER(__name__).error(f"[WELCOME] send card failed in {chat.id}: {type(e).__name__}: {e}")
            try:
                sent = await _send(chat.id, caption, user, photo_path)        # 2) plain profile photo
            except Exception as e2:
                errors.append(f"send photo: {type(e2).__name__}: {e2}")
                sent = await _send(chat.id, caption, user, None)              # 3) text only
    except Exception as e3:
        errors.append(f"send text: {type(e3).__name__}: {e3}")
        LOGGER(__name__).error(f"[WELCOME] send failed in {chat.id}: {type(e3).__name__}: {e3}")
    finally:
        for f in (photo_path, card):
            try:
                if f and os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass
    _schedule_delete(sent)               # auto-delete after DELETE_AFTER seconds
    if report_to is not None and errors:
        try:
            await report_to.reply_text("⚠️ welcome debug:\n" + "\n".join(html.escape(x)[:300] for x in errors),
                                     parse_mode=ParseMode.HTML)
        except Exception:
            pass


@app.on_message(filters.new_chat_members & filters.group, group=7)
async def welcome_new_members(_, message: Message):
    try:
        if not await _is_on(message.chat.id):
            return
        me_id = getattr(app, "id", None) or (app.me.id if getattr(app, "me", None) else None)
        users = [u for u in message.new_chat_members if not u.is_bot and u.id != me_id][:MAX_PER_EVENT]
        LOGGER(__name__).info(f"[WELCOME] service msg in {message.chat.id}: {[u.id for u in users]}")
        for u in users:
            if _claim(message.chat.id, u.id):
                await _send_welcome(message.chat, u)
    except Exception:
        LOGGER(__name__).error(f"[WELCOME] handler error:\n{traceback.format_exc()}")


# Fallback: Telegram does NOT send the "X joined" service message in big groups, when joins are
# hidden, or when the user came through a join request. A bot that is admin still gets this update.
@app.on_chat_member_updated(group=8)
async def welcome_member_update(_, update: ChatMemberUpdated):
    try:
        if update.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return
        new, old = update.new_chat_member, update.old_chat_member
        if not new or not new.user or new.status != ChatMemberStatus.MEMBER:
            return
        if old and old.status not in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED):
            return                                   # promoted / restricted / unrestricted, not a join
        user = new.user
        me_id = getattr(app, "id", None) or (app.me.id if getattr(app, "me", None) else None)
        if user.is_bot or user.id == me_id:
            return
        if not await _is_on(update.chat.id):
            return
        LOGGER(__name__).info(f"[WELCOME] member update in {update.chat.id}: {user.id}")
        if _claim(update.chat.id, user.id):
            await _send_welcome(update.chat, user)
    except Exception:
        LOGGER(__name__).error(f"[WELCOME] member-update error:\n{traceback.format_exc()}")


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
    if arg == "test":
        if not message.from_user:
            return await message.reply_text("ᴛᴇsᴛ ɴᴇᴇᴅs ᴀ ɴᴏʀᴍᴀʟ (ɴᴏᴛ ᴀɴᴏɴʏᴍᴏᴜs) ᴀᴅᴍɪɴ.")
        _claim(message.chat.id, message.from_user.id)
        return await _send_welcome(message.chat, message.from_user, report_to=message)
    state = "ᴏɴ ✅" if await _is_on(message.chat.id) else "ᴏғғ ❌"
    await message.reply_text(
        f"ᴡᴇʟᴄᴏᴍᴇ ɪs {state}\n\nᴜsᴀɢᴇ: <code>/welcome on</code> | <code>/welcome off</code> | <code>/welcome test</code>",
        parse_mode=ParseMode.HTML,
    )
