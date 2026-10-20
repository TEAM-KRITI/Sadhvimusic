# =======================================================
# ©️ 2025-26 All Rights Reserved by Purvi Bots (Im-Notcoder) 🚀
#
# This source code is under MIT License 📜
# Unauthorized forking, importing, or using this code
# without giving proper credit will result in legal action ⚠️
#
# 📩 DM for permission : @TheSigmaCoder
# =======================================================

import asyncio
import html
import os
import time
import unicodedata
from datetime import datetime
from logging import getLogger

from motor.motor_asyncio import AsyncIOMotorClient
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from pyrogram import enums, filters
from pyrogram.types import (
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import MONGO_DB_URI
from ShiviMusic import app


LOGGER = getLogger(__name__)


# =======================================================
# DATABASE
# =======================================================

mongo = AsyncIOMotorClient(MONGO_DB_URI)

db = mongo["Wel_DB"]
welcomedb = db["welcome_toggle_system"]


async def get_welcome(chat_id: int) -> bool:
    try:
        data = await welcomedb.find_one({"chat_id": chat_id})

        if not data:
            return True

        return data.get("welcome", True)

    except Exception as e:
        LOGGER.warning(f"[WELCOME DB] get error: {e}")
        return True


async def enable_welcome(chat_id: int):
    try:
        await welcomedb.update_one(
            {"chat_id": chat_id},
            {"$set": {"welcome": True}},
            upsert=True,
        )
    except Exception as e:
        LOGGER.warning(f"[WELCOME DB] enable error: {e}")


async def disable_welcome(chat_id: int):
    try:
        await welcomedb.update_one(
            {"chat_id": chat_id},
            {"$set": {"welcome": False}},
            upsert=True,
        )
    except Exception as e:
        LOGGER.warning(f"[WELCOME DB] disable error: {e}")


# =======================================================
# TEMP STORAGE
# =======================================================

class temp:
    MELCOW = {}


# =======================================================
# ASSETS
# =======================================================

ASSETS = "ShiviMusic/assets"

FONT_BOLD = f"{ASSETS}/font.ttf"
FONT_REG = f"{ASSETS}/font2.ttf"

FALLBACK_PIC = f"{ASSETS}/upic.png"

CYAN = (0, 214, 214)


# =======================================================
# FONT HELPERS
# =======================================================

def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _fit(draw, text, path, size, max_w, min_size=24):
    while size > min_size:
        font = _font(path, size)

        try:
            width = draw.textlength(text, font=font)
        except Exception:
            width = len(text) * size

        if width <= max_w:
            return font

        size -= 2

    return _font(path, min_size)


# =======================================================
# SAFE TEXT
# =======================================================

def safe_text(text, limit=22, default="New Member"):
    """
    Image ke andar unsupported emoji/special Unicode
    se boxes aane se bachata hai.
    """

    try:
        text = unicodedata.normalize("NFKD", str(text or ""))

        text = "".join(
            ch for ch in text
            if 32 <= ord(ch) < 127
        )

        text = " ".join(text.split())

    except Exception:
        text = ""

    text = text[:limit].strip()

    return text or default


# =======================================================
# SMALL CAPS FONT
# =======================================================

_SC = dict(
    zip(
        "abcdefghijklmnopqrstuvwxyz",
        "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ",
    )
)


def sc(text: str) -> str:
    """
    Example:
    CHAT ID -> ᴄʜᴀᴛ ɪᴅ
    """

    return "".join(
        _SC.get(ch.lower(), ch)
        if ch.isalpha()
        else ch
        for ch in str(text)
    )


# =======================================================
# CIRCLE PROFILE PHOTO
# =======================================================

def circle(
    pfp,
    size=(420, 420),
    brightness_factor=1.1,
):
    pfp = pfp.resize(size).convert("RGBA")

    pfp = ImageEnhance.Brightness(
        pfp
    ).enhance(brightness_factor)

    mask = Image.new(
        "L",
        size,
        0,
    )

    ImageDraw.Draw(mask).ellipse(
        (0, 0, size[0], size[1]),
        fill=255,
    )

    pfp.putalpha(mask)

    return pfp


# =======================================================
# WELCOME IMAGE  (neon card, colours change every time)
# Generator: ShiviMusic/utils/welcome_card.py
# =======================================================

from ShiviMusic.utils.welcome_card import welcomepic, welcomepic_simple  # noqa: E402


# =======================================================
# WELCOME CAPTION
# =======================================================

def welcome_caption(
    user,
    chat_title,
):
    title = html.escape(
        safe_text(
            chat_title,
            40,
            "Group",
        )
    )

    first = html.escape(
        (user.first_name or "New Member")[:25]
    )

    if user.username:
        uname = (
            "@"
            + html.escape(
                user.username
            )
        )
    else:
        uname = "ɴᴏᴛ sᴇᴛ"

    mention = (
        f'<a href="tg://user?id={user.id}">'
        f'{first}'
        f'</a>'
    )

    return (
        f"<blockquote>"
        f"<b>⏤͟͟͞͞★ ʜᴇʟʟᴏ ᴅᴇᴀʀ "
        f"ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ : {title}</b>"
        f"</blockquote>\n\n"

        f"<u><b>❖ ᴜsᴇʀ sʜᴏʀᴛ ɪɴғᴏ</b></u>\n\n"

        f"<blockquote>"
        f"<b>➻ ɴᴀᴍᴇ »</b> {mention}\n"
        f"<b>➻ ᴄʜᴀᴛ_ɪᴅ »</b> "
        f"<code>{user.id}</code>\n"
        f"<b>➻ ᴜ_ɴᴀᴍᴇ »</b> {uname}"
        f"</blockquote>\n\n"

        f"<blockquote>"
        f"<b>➻ ᴛʜᴀɴᴋs ғᴏʀ ᴊᴏɪɴɪɴɢ ᴜs ⚡️~!</b>\n"
        f"❅─────✧❅✦❅✧─────❅"
        f"</blockquote>"
    )


# =======================================================
# /WELCOME COMMAND
# =======================================================

@app.on_message(
    filters.command("welcome")
    & filters.group
)
async def welcome_cmd(_, message: Message):

    if not message.from_user:
        return

    chat = message.chat
    chat_id = chat.id

    try:
        member = await app.get_chat_member(
            chat_id,
            message.from_user.id,
        )

    except Exception:
        return

    if member.status not in (
        enums.ChatMemberStatus.ADMINISTRATOR,
        enums.ChatMemberStatus.OWNER,
    ):
        return await message.reply_text(
            "» **𝐎꯭ɴ꯭ʟ꯭ʏ ꯭༭꯭ "
            "𝐀꯭ᴅ꯭ᴍ꯭ɪ꯭ɴ꯭s ꯭༭꯭ "
            "𝐂꯭ᴀ꯭ɴ ꯭༭꯭ "
            "𝐇꯭ᴀ꯭ɴ꯭ᴅ꯭ʟ꯭ᴇ ꯭༭꯭ "
            "𝐖꯭ᴇ꯭ʟ꯭ᴄ꯭ᴏ꯭ᴍ꯭ᴇ ꯭༭꯭ "
            "𝐒꯭ʏ꯭s꯭ᴛ꯭ᴇ꯭ᴍ**"
        )

    state = await get_welcome(
        chat_id
    )

    status = (
        "𝐄꯭ɴ꯭ᴀ꯭ʙ꯭ʟ꯭ᴇ꯭ᴅ"
        if state
        else "𝐃꯭ɪ꯭s꯭ᴀ꯭ʙ꯭ʟ꯭ᴇ꯭ᴅ"
    )

    btn = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "𝐄꯭ɴ꯭ᴀ꯭ʙ꯭ʟ꯭ᴇ",
                    callback_data=f"wlc_on_{chat_id}",
                ),
                InlineKeyboardButton(
                    "𝐃꯭ɪ꯭s꯭ᴀ꯭ʙ꯭ʟ꯭ᴇ",
                    callback_data=f"wlc_off_{chat_id}",
                ),
            ]
        ]
    )

    await message.reply_text(
        f"» 𝐂꯭ᴜ꯭ʀ꯭ʀ꯭ᴇ꯭ɴ꯭ᴛ꯭ʟ꯭ʏ "
        f"༭꯭ 𝐖꯭ᴇ꯭ʟ꯭ᴄ꯭ᴏ꯭ᴍ꯭ᴇ "
        f"༭꯭ 𝐒꯭ᴛ꯭ᴀ꯭ᴛ꯭ᴜ꯭s "
        f"**{status}** "
        f"༭꯭ 𝐈꯭ɴ "
        f"༭꯭ **{html.escape(chat.title)}**",
        reply_markup=btn,
    )


# =======================================================
# WELCOME TOGGLE CALLBACK
# =======================================================

@app.on_callback_query(
    filters.regex(r"^wlc_(on|off)_")
)
async def welcome_toggle(_, query):

    try:
        data = query.data.split("_")

        action = data[1]
        chat_id = int(data[2])

    except Exception:
        return await query.answer(
            "Invalid request!",
            show_alert=True,
        )

    try:
        member = await app.get_chat_member(
            chat_id,
            query.from_user.id,
        )

    except Exception:
        return await query.answer(
            "Unable to verify admin!",
            show_alert=True,
        )

    if member.status not in (
        enums.ChatMemberStatus.ADMINISTRATOR,
        enums.ChatMemberStatus.OWNER,
    ):
        return await query.answer(
            "𝐘꯭ᴏ꯭ᴜ ꯭༭꯭ 𝐀꯭ʀ꯭ᴇ ꯭༭꯭ "
            "𝐍꯭ᴏ꯭ᴛ ꯭༭꯭ 𝐀꯭ᴅ꯭ᴍ꯭ɪ꯭ɴ 🥺",
            show_alert=True,
        )

    if action == "on":

        await enable_welcome(
            chat_id
        )

        new_status = "𝐄꯭ɴ꯭ᴀ꯭ʙ꯭ʟ꯭ᴇ꯭ᴅ"

    else:

        await disable_welcome(
            chat_id
        )

        new_status = "𝐃꯭ɪ꯭s꯭ᴀ꯭ʙ꯭ʟ꯭ᴇ꯭ᴅ"

    try:
        chat = await app.get_chat(
            chat_id
        )

        chat_title = html.escape(
            chat.title or "Group"
        )

    except Exception:
        chat_title = "Group"

    await query.message.edit_text(
        f"» 𝐖꯭ᴇ꯭ʟ꯭ᴄ꯭ᴏ꯭ᴍ꯭ᴇ "
        f"༭꯭ 𝐌꯭ᴇ꯭s꯭s꯭ᴀ꯭ɢ꯭ᴇ "
        f"༭꯭ **{new_status}**\n\n"
        f"𝐈꯭ɴ ༭꯭ **{chat_title}**\n"
        f"𝐁꯭ʏ ༭꯭ **{query.from_user.mention}**"
    )

    await query.answer(
        "Welcome settings updated!"
    )


# =======================================================
# CHECK NEW MEMBER
# =======================================================

def _is_new_join(
    member: ChatMemberUpdated,
) -> bool:

    new = member.new_chat_member
    old = member.old_chat_member

    if not new:
        return False

    if new.status != enums.ChatMemberStatus.MEMBER:
        return False

    if old is None:
        return True

    return old.status in (
        enums.ChatMemberStatus.LEFT,
        enums.ChatMemberStatus.BANNED,
    )


# =======================================================
# NEW MEMBER GREETING
#
# Welcome 2 raston se trigger hota hai:
#   1) chat_member update  (sirf tab aata hai jab bot ADMIN ho)
#   2) "user joined" service message (admin ke bina bhi aata hai)
# Dono ek hi function chalate hain; dedupe ki wajah se
# ek join par welcome sirf ek baar jaata hai.
# =======================================================

_RECENT = {}          # (chat_id, user_id) -> time
_RECENT_TTL = 30      # seconds


def _already_welcomed(chat_id: int, user_id: int) -> bool:
    now = time.time()

    for key in [k for k, t in _RECENT.items() if now - t > _RECENT_TTL]:
        _RECENT.pop(key, None)

    key = (chat_id, user_id)

    if key in _RECENT:
        return True

    _RECENT[key] = now
    return False


async def _download_pfp(user):
    """Profile photo download. Na mile to FALLBACK_PIC."""
    try:
        photo = user.photo

        if not photo:
            # chat_member / service updates me photo aksar nahi aati
            full = await app.get_chat(user.id)
            photo = getattr(full, "photo", None)

        if photo:
            path = await app.download_media(
                photo.big_file_id,
                file_name=f"pp_{user.id}.png",
            )

            if path and os.path.exists(path):
                return path

    except Exception as e:
        LOGGER.info(f"[WELCOME] pfp download failed: {e}")

    return FALLBACK_PIC


async def _send_welcome(chat, user):
    pic = None
    welcomeimg = None

    try:
        chat_id = chat.id

        if user.is_bot:
            return

        if not await get_welcome(chat_id):
            return

        if _already_welcomed(chat_id, user.id):
            return

        pic = await _download_pfp(user)

        # previous welcome delete
        old = temp.MELCOW.pop(f"welcome-{chat_id}", None)

        if old:
            try:
                await old.delete()
            except Exception:
                pass

        # welcome image (blocking PIL work -> executor)
        loop = asyncio.get_running_loop()

        welcomeimg = None

        for gen in (welcomepic, welcomepic_simple):
            try:
                welcomeimg = await loop.run_in_executor(
                    None,
                    gen,
                    pic,
                    user,
                    chat.title or "Group",
                    user.id,
                    user.username,
                )
                break
            except Exception:
                LOGGER.exception(f"[WELCOME] {gen.__name__} failed")

        caption = welcome_caption(user, chat.title or "Group")

        bot_username = getattr(app, "username", None)

        markup = None

        if bot_username:
            markup = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⊚ ᴧᴅᴅ ᴍᴇ ᴛᴏ ʏᴏυʀ ᴄʜᴧᴛ ⊚",
                            url=f"https://t.me/{bot_username}?startgroup=true",
                        )
                    ]
                ]
            )

        msg = None

        if welcomeimg:
            try:
                msg = await app.send_photo(
                    chat_id=chat_id,
                    photo=welcomeimg,
                    caption=caption,
                    parse_mode=enums.ParseMode.HTML,
                    reply_markup=markup,
                )
            except Exception:
                LOGGER.exception("[WELCOME] send_photo (png) failed")

                try:
                    from PIL import Image as _Img

                    jpg = welcomeimg.rsplit(".", 1)[0] + ".jpg"
                    _Img.open(welcomeimg).convert("RGB").save(jpg, quality=92)

                    try:
                        msg = await app.send_photo(
                            chat_id=chat_id,
                            photo=jpg,
                            caption=caption,
                            parse_mode=enums.ParseMode.HTML,
                            reply_markup=markup,
                        )
                    finally:
                        try:
                            os.remove(jpg)
                        except Exception:
                            pass

                except Exception:
                    LOGGER.exception("[WELCOME] send_photo (jpg) failed")

        if msg is None:
            # fallback: text-only welcome
            msg = await app.send_message(
                chat_id=chat_id,
                text=caption,
                parse_mode=enums.ParseMode.HTML,
                reply_markup=markup,
                disable_web_page_preview=True,
            )

        temp.MELCOW[f"welcome-{chat_id}"] = msg

        async def delete_welcome():
            await asyncio.sleep(130)

            try:
                await msg.delete()
            except Exception:
                pass

            if temp.MELCOW.get(f"welcome-{chat_id}") is msg:
                temp.MELCOW.pop(f"welcome-{chat_id}", None)

        asyncio.create_task(delete_welcome())

    except Exception as e:
        LOGGER.warning(f"[WELCOME ERROR] {type(e).__name__}: {e}")

    finally:
        for file_path in (welcomeimg, pic):
            if file_path and file_path != FALLBACK_PIC:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception:
                    pass


@app.on_chat_member_updated(filters.group, group=-3)
async def greet_new_member(_, member: ChatMemberUpdated):
    try:
        if not _is_new_join(member):
            return

        await _send_welcome(member.chat, member.new_chat_member.user)

    except Exception as e:
        LOGGER.warning(f"[WELCOME] member update error: {type(e).__name__}: {e}")


@app.on_message(filters.new_chat_members & filters.group, group=-3)
async def greet_new_member_msg(_, message: Message):
    try:
        for user in message.new_chat_members or []:
            await _send_welcome(message.chat, user)

    except Exception as e:
        LOGGER.warning(f"[WELCOME] service msg error: {type(e).__name__}: {e}")


# =======================================================
# ©️ 2025-26 All Rights Reserved by Purvi Bots (Im-Notcoder)
#
# 🧑‍💻 Developer : t.me/TheSigmaCoder
# 🔗 Source : GitHub.com/Im-Notcoder/Sonali-MusicV2
# 📢 Telegram : t.me/Purvi_Bots
# =======================================================
