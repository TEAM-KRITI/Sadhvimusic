# -----------------------------------------------
# 🔸 CharviMusic Project
# 🔹 Developed & Maintained by: Charvi Bots
# 📅 Copyright © 2022 – All Rights Reserved
# -----------------------------------------------

import random

from pyrogram import filters, enums
from ShiviMusic import app

from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ChatPermissions,
)

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ShiviMusic.utils.nightmodedb import (
    nightdb,
    nightmode_on,
    nightmode_off,
    get_nightchats,
)


# =======================================================
# CHAT PERMISSIONS
# =======================================================

CLOSE_CHAT = ChatPermissions(
    can_send_messages=False,
    can_send_media_messages=False,
    can_send_polls=False,
    can_change_info=False,
    can_add_web_page_previews=False,
    can_pin_messages=False,
    can_invite_users=False
)

OPEN_CHAT = ChatPermissions(
    can_send_messages=True,
    can_send_media_messages=True,
    can_send_polls=True,
    can_change_info=True,
    can_add_web_page_previews=True,
    can_pin_messages=True,
    can_invite_users=True
)


# =======================================================
# NIGHTMODE BUTTONS
# =======================================================

buttons = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "๏ 𝐄ηαвℓє ๏",
                callback_data="add_night"
            ),
            InlineKeyboardButton(
                "๏ 𝐃ιѕαвℓє ๏",
                callback_data="rm_night"
            )
        ]
    ]
)


# =======================================================
# ADD BOT BUTTON
# =======================================================

NIGHT_MSG_BUTTONS = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "𝐀∂∂ 𝐌є 𝐈η 𝐘συя 𝐆яσυρ",
                url=f"https://t.me/{app.username}?startgroup=true"
            )
        ]
    ]
)


# =======================================================
# NIGHTMODE COMMAND
# =======================================================

@app.on_message(filters.command("nightmode") & filters.group)
async def _nightmode(_, message):

    return await message.reply_photo(
        photo="https://n.uguu.se/PbzKsnAJ.jpg",

        caption=(
            "**⚙️ 𝐍ιɢнтмσ∂є 𝐒єттιηɢѕ**\n\n"
            "**𝐂ℓι¢к тнє 𝐁υттσηѕ 𝐁єℓσω тσ 𝐂σηтяσℓ "
            "𝐍ιɢнтмσ∂є 𝐒єттιηɢѕ 𝐅σя тнιѕ 𝐆яσυρ.**"
        ),

        parse_mode=enums.ParseMode.MARKDOWN,
        reply_markup=buttons
    )


# =======================================================
# NIGHTMODE CALLBACK
# =======================================================

@app.on_callback_query(
    filters.regex("^(add_night|rm_night)$")
)
async def nightcb(_, query: CallbackQuery):

    data = query.data
    chat_id = query.message.chat.id
    user_id = query.from_user.id

    check_night = await nightdb.find_one(
        {"chat_id": chat_id}
    )

    administrators = []

    async for m in app.get_chat_members(
        chat_id,
        filter=enums.ChatMembersFilter.ADMINISTRATORS
    ):
        administrators.append(m.user.id)

    if user_id not in administrators:
        return await query.answer(
            "❌ 𝐎ηℓу 𝐀∂мιηѕ 𝐂αη 𝐔ѕє 𝐓нιѕ 𝐂σммαη∂!",
            show_alert=True
        )

    # ===================================================
    # ENABLE
    # ===================================================

    if data == "add_night":

        if check_night:

            await query.message.edit_caption(
                caption=(
                    "**🌕 𝐍ιɢнтмσ∂є 𝐈ѕ 𝐀ℓяєα∂у "
                    "𝐄ηαвℓє∂ 𝐈η 𝐓нιѕ 𝐆яσυρ.**"
                ),
                parse_mode=enums.ParseMode.MARKDOWN,
                reply_markup=buttons
            )

        else:

            await nightmode_on(chat_id)

            await query.message.edit_caption(
                caption=(
                    "**✅ 𝐍ιɢнтмσ∂є 𝐀¢тιναтє∂!**\n\n"
                    "**𝐓нιѕ 𝐆яσυρ 𝐖ιℓℓ 𝐀υтσмαтι¢αℓℓу "
                    "𝐋σ¢к 𝐀т 𝟏𝟐:𝟎𝟎 𝐀𝐌 & 𝐔ηℓσ¢к 𝐀т "
                    "𝟎𝟔:𝟎𝟎 𝐀𝐌 [𝐈𝐒𝐓].**"
                ),
                parse_mode=enums.ParseMode.MARKDOWN,
                reply_markup=buttons
            )

    # ===================================================
    # DISABLE
    # ===================================================

    elif data == "rm_night":

        if check_night:

            await nightmode_off(chat_id)

            await query.message.edit_caption(
                caption="**❌ 𝐍ιɢнтмσ∂є 𝐃єα¢тιναтє∂!**",
                parse_mode=enums.ParseMode.MARKDOWN,
                reply_markup=buttons
            )

        else:

            await query.message.edit_caption(
                caption=(
                    "**🌑 𝐍ιɢнтмσ∂є 𝐈ѕ 𝐀ℓяєα∂у "
                    "𝐓υяηє∂ 𝐎ƒƒ.**"
                ),
                parse_mode=enums.ParseMode.MARKDOWN,
                reply_markup=buttons
            )

    await query.answer()


# =======================================================
# GOOD NIGHT
# =======================================================

async def start_nightmode():

    schats = await get_nightchats()

    for chat in schats:

        chat_id = int(chat["chat_id"])

        try:

            group = await app.get_chat(chat_id)

            group_name = group.title or "𝐔ηкησωη 𝐆яσυρ"

            await app.send_photo(
                chat_id,

                photo="https://d.uguu.se/agsYnJwN.jpg",

                caption=(
                    "**🌌 𝐆σσ∂ 𝐍ιɢнт 𝐄νєяуσηє!**\n"
                    "**━─────────────────━**\n\n"

                    "**✨ 𝐓ιмє тσ 𝐓υяη 𝐎ƒƒ 𝐘συя 𝐒¢яєєηѕ "
                    "αη∂ 𝐂αт¢н 𝐒σмє 𝐏єα¢єƒυℓ 𝐃яєαмѕ. "
                    "𝐌αу 𝐘συя 𝐒ℓєєρ 𝐁є 𝐒ωєєт αη∂ "
                    "𝐑єѕтƒυℓ.**\n\n"

                    "**🔒 𝐆яσυρ 𝐈ѕ 𝐍σω 𝐂ℓσѕє∂.**\n\n"

                    "**• 𝐍σ 𝐌єѕѕαɢєѕ 𝐂αη 𝐁є 𝐒єηт "
                    "𝐔ηтιℓ 𝐌σяηιηɢ. 𝐒єє 𝐘συ 𝐀ℓℓ "
                    "𝐓σмσяяσω!**\n\n"

                    # GROUP DETAILS
                    f"**👥 𝐆яσυρ 𝐍αмє : {group_name}**\n"
                    f"**🆔 𝐆яσυρ 𝐈𝐃 : `{chat_id}`**\n\n"

                    # POWERED BY
                    "**⚡ 𝐏σωєяє∂ 𝐁у : "
                    "[𝐊ιятι 𝐌υѕι¢](https://t.me/annu_updates)**"
                ),

                parse_mode=enums.ParseMode.MARKDOWN,
                reply_markup=NIGHT_MSG_BUTTONS
            )

            await app.set_chat_permissions(
                chat_id,
                CLOSE_CHAT
            )

        except Exception as e:

            print(
                f"Unable to close group {chat_id}: {e}"
            )


# =======================================================
# GOOD MORNING
# =======================================================

async def close_nightmode():

    schats = await get_nightchats()

    for chat in schats:

        chat_id = int(chat["chat_id"])

        try:

            group = await app.get_chat(chat_id)

            group_name = group.title or "𝐔ηкησωη 𝐆яσυρ"

            await app.send_photo(
                chat_id,

                photo="https://d.uguu.se/CPlUJSEp.jpg",

                caption=(
                    "**🌅 𝐆σσ∂ 𝐌σяηιηɢ 𝐄νєяуσηє..!**\n"
                    "**━─────────────────━**\n\n"

                    "**✨ 𝐀 𝐁єαυтιƒυℓ 𝐍єω 𝐃αу 𝐇αѕ "
                    "𝐀яяινє∂. 𝐌αу 𝐓нιѕ 𝐃αу 𝐁яιηɢ "
                    "𝐄η∂ℓєѕѕ 𝐎ρρσятυηιтιєѕ, 𝐉σу, αη∂ "
                    "𝐒υ¢¢єѕѕ тσ 𝐘συя 𝐋ιƒє.**\n\n"

                    "**🔓 𝐆яσυρ 𝐈ѕ 𝐍σω 𝐎ρєη.**\n\n"

                    "**• 𝐅єєℓ 𝐅яєє тσ 𝐂нαт, 𝐒нαяє, αη∂ "
                    "𝐒тαу 𝐏σѕιтινє!**\n\n"

                    # GROUP DETAILS
                    f"**👥 𝐆яσυρ 𝐍αмє : {group_name}**\n"
                    f"**🆔 𝐆яσυρ 𝐈𝐃 : `{chat_id}`**\n\n"

                    # POWERED BY
                    "**⚡ 𝐏σωєяє∂ 𝐁у : "
                    "[𝐊ιятι 𝐌υѕι¢](https://t.me/annu_updates)**"
                ),

                parse_mode=enums.ParseMode.MARKDOWN,
                reply_markup=NIGHT_MSG_BUTTONS
            )

            await app.set_chat_permissions(
                chat_id,
                OPEN_CHAT
            )

        except Exception as e:

            print(
                f"Unable to open group {chat_id}: {e}"
            )


# =======================================================
# SCHEDULER
# =======================================================

scheduler = AsyncIOScheduler(
    timezone="Asia/Kolkata"
)

# 11:59 PM
scheduler.add_job(
    start_nightmode,
    trigger="cron",
    hour=23,
    minute=59
)

# 06:01 AM
scheduler.add_job(
    close_nightmode,
    trigger="cron",
    hour=6,
    minute=1
)

scheduler.start()


# =======================================================
# ©️ 2025-26 CharviMusic
# =======================================================
