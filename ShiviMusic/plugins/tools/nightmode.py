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
# ᴄʜᴀᴛ ᴘєʀᴍɪꜱꜱɪᴏɴꜱ
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
# ɴɪɢʜᴛᴍᴏᴅє ʙᴜᴛᴛᴏɴꜱ
# =======================================================

buttons = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "๏ єɴᴀʙʟє ๏",
                callback_data="add_night"
            ),
            InlineKeyboardButton(
                "๏ ᴅɪꜱᴀʙʟє ๏",
                callback_data="rm_night"
            )
        ]
    ]
)


# =======================================================
# ᴀᴅᴅ ʙᴏᴛ ʙᴜᴛᴛᴏɴ
# =======================================================

NIGHT_MSG_BUTTONS = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "ᴀᴅᴅ ᴍє ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ",
                url=f"https://t.me/{app.username}?startgroup=true"
            )
        ]
    ]
)


# =======================================================
# ɴɪɢʜᴛᴍᴏᴅє ᴄᴏᴍᴍᴀɴᴅ
# =======================================================

@app.on_message(filters.command("nightmode") & filters.group)
async def _nightmode(_, message):

    return await message.reply_photo(
        photo="https://yukiapi.site/file/pABl4iKv",

        caption=(
            "**⚙️ ɴɪɢʜᴛᴍᴏᴅє ꜱєᴛᴛɪɴɢꜱ**\n\n"
            "**ᴜꜱє ᴛʜє ʙᴜᴛᴛᴏɴꜱ ʙєʟᴏᴡ.**"
        ),

        parse_mode=enums.ParseMode.MARKDOWN,
        reply_markup=buttons
    )


# =======================================================
# ɴɪɢʜᴛᴍᴏᴅє ᴄᴀʟʟʙᴀᴄᴋ
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
            "❌ ᴏɴʟʏ ᴀᴅᴍɪɴꜱ ᴄᴀɴ ᴜꜱє ᴛʜɪꜱ!",
            show_alert=True
        )

    # ===================================================
    # єɴᴀʙʟє
    # ===================================================

    if data == "add_night":

        if check_night:

            await query.message.edit_caption(
                caption="**🌕 ɴɪɢʜᴛᴍᴏᴅє ɪꜱ ᴀʟʀєᴀᴅʏ ᴏɴ.**",
                parse_mode=enums.ParseMode.MARKDOWN,
                reply_markup=buttons
            )

        else:

            await nightmode_on(chat_id)

            await query.message.edit_caption(
                caption=(
                    "**✅ ɴɪɢʜᴛᴍᴏᴅє ᴏɴ!**\n\n"
                    "**🔒 12:00 ᴀᴍ  •  🔓 06:00 ᴀᴍ [ɪꜱᴛ]**"
                ),
                parse_mode=enums.ParseMode.MARKDOWN,
                reply_markup=buttons
            )

    # ===================================================
    # ᴅɪꜱᴀʙʟє
    # ===================================================

    elif data == "rm_night":

        if check_night:

            await nightmode_off(chat_id)

            await query.message.edit_caption(
                caption="**❌ ɴɪɢʜᴛᴍᴏᴅє ᴏꜰꜰ!**",
                parse_mode=enums.ParseMode.MARKDOWN,
                reply_markup=buttons
            )

        else:

            await query.message.edit_caption(
                caption="**🌑 ɴɪɢʜᴛᴍᴏᴅє ɪꜱ ᴀʟʀєᴀᴅʏ ᴏꜰꜰ.**",
                parse_mode=enums.ParseMode.MARKDOWN,
                reply_markup=buttons
            )

    await query.answer()


# =======================================================
# ɢᴏᴏᴅ ɴɪɢʜᴛ
# =======================================================

async def start_nightmode():

    schats = await get_nightchats()

    for chat in schats:

        chat_id = int(chat["chat_id"])

        try:

            group = await app.get_chat(chat_id)

            group_name = group.title or "ᴜɴᴋɴᴏᴡɴ ɢʀᴏᴜᴘ"

            await app.send_photo(
                chat_id,

                photo="",

                caption=(
                    "**🌌 ɢᴏᴏᴅ ɴɪɢʜᴛ єᴠєʀʏᴏɴє!**\n\n"
                    "**🔒 ɢʀᴏᴜᴘ ɪꜱ ɴᴏᴡ ᴄʟᴏꜱєᴅ.**\n"
                    "**ꜱᴡєєᴛ ᴅʀєᴀᴍꜱ, ꜱєє ʏᴏᴜ ᴛᴏᴍᴏʀʀᴏᴡ!**\n\n"

                    f"**👥 {group_name}**\n"
                    f"**🆔 `{chat_id}`**\n\n"

                    "**⚡ ᴘᴏᴡєʀєᴅ ʙʏ : "
                    "[ᴋɪʀᴛɪ ᴍᴜꜱɪᴄ](https://t.me/kirti_bots)**"
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
# ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ
# =======================================================

async def close_nightmode():

    schats = await get_nightchats()

    for chat in schats:

        chat_id = int(chat["chat_id"])

        try:

            group = await app.get_chat(chat_id)

            group_name = group.title or "ᴜɴᴋɴᴏᴡɴ ɢʀᴏᴜᴘ"

            await app.send_photo(
                chat_id,

                photo="https://yukiapi.site/file/pABl4iKv",

                caption=(
                    "**🌅 ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ єᴠєʀʏᴏɴє!**\n\n"
                    "**🔓 ɢʀᴏᴜᴘ ɪꜱ ɴᴏᴡ ᴏᴘєɴ.**\n"
                    "**ʜᴀᴠє ᴀ ʙєᴀᴜᴛɪꜰᴜʟ ᴅᴀʏ!**\n\n"

                    f"**👥 {group_name}**\n"
                    f"**🆔 `{chat_id}`**\n\n"

                    "**⚡ ᴘᴏᴡєʀєᴅ ʙʏ : "
                    "[ᴋɪʀᴛɪ ᴍᴜꜱɪᴄ](https://t.me/kirti_bots)**"
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
# ꜱᴄʜєᴅᴜʟєʀ
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
