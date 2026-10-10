# ============================================================
# 🎧 ᴠɪᴅᴇᴏ ᴄʜᴀᴛ sʏsᴛᴇᴍ
# ============================================================

from pyrogram import filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from ShiviMusic import app


# ============================================================
# 🔘 ʙᴜᴛᴛᴏɴs
# ============================================================

async def get_buttons(client):

    me = await client.get_me()

    username = me.username

    if username:
        add_url = f"https://t.me/{username}?startgroup=true"
    else:
        add_url = "https://t.me/"

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✙ ᴧᴅᴅ ᴍᴇ ✙",
                    url=add_url,
                ),
                InlineKeyboardButton(
                    "≡ ᴄʟᴏsᴇ ≡",
                    callback_data="close_vc_message",
                ),
            ]
        ]
    )


# ============================================================
# 🟢 ᴠᴄ sᴛᴀʀᴛᴇᴅ
# ============================================================

@app.on_message(filters.video_chat_started)
async def video_chat_started(client, message):

    try:
        chat_name = message.chat.title or "ᴛʜɪs ɢʀᴏᴜᴘ"

        text = (
            f"**❖ ᴠɪᴅᴇᴏ ᴄʜᴀᴛ sᴛᴀʀᴛᴇᴅ ɪɴ {chat_name}**\n\n"
            f"**▶ /play [sᴏɴɢ_ɴᴀᴍᴇ] ᴇɴᴊᴏʏ ᴍᴜsɪᴄ 🎶**"
        )

        buttons = await get_buttons(client)

        await message.reply_text(
            text,
            reply_markup=buttons,
            disable_web_page_preview=True,
        )

    except Exception as e:
        print(f"VIDEO CHAT START ERROR: {e}")


# ============================================================
# 🔴 ᴠᴄ ᴇɴᴅᴇᴅ
# ============================================================

@app.on_message(filters.video_chat_ended)
async def video_chat_ended(client, message):

    try:
        chat_name = message.chat.title or "ᴛʜɪs ɢʀᴏᴜᴘ"

        duration = 0

        if message.video_chat_ended:
            duration = message.video_chat_ended.duration or 0

        days = duration // 86400
        hours = (duration % 86400) // 3600
        minutes = (duration % 3600) // 60

        if days > 0:
            duration_text = f"{days}ᴅ {hours}ʜ"

        elif hours > 0:
            duration_text = f"{hours}ʜ {minutes}ᴍ"

        elif minutes > 0:
            duration_text = f"{minutes}ᴍ"

        else:
            duration_text = f"{duration}s"

        text = (
            f"**❖ ᴠɪᴅᴇᴏ ᴄʜᴀᴛ ᴇɴᴅᴇᴅ ɪɴ {chat_name}**\n\n"
            f"**⏰ ᴅᴜʀᴀᴛɪᴏɴ: {duration_text}**\n\n"
            f"**◆ ᴄʟᴇᴀʀᴇᴅ ᴀʟʟ Qᴜᴇᴜᴇ sᴏɴɢs 🗑**"
        )

        buttons = await get_buttons(client)

        await message.reply_text(
            text,
            reply_markup=buttons,
            disable_web_page_preview=True,
        )

    except Exception as e:
        print(f"VIDEO CHAT END ERROR: {e}")


# ============================================================
# 👥 ᴠᴄ ᴍᴇᴍʙᴇʀs ɪɴᴠɪᴛᴇᴅ
# ============================================================

@app.on_message(filters.video_chat_members_invited)
async def video_chat_members_invited(client, message):

    try:

        if not message.from_user:
            return

        if not message.video_chat_members_invited:
            return

        users = message.video_chat_members_invited.users

        if not users:
            return

        inviter_name = message.from_user.first_name or "ᴜsᴇʀ"

        inviter = (
            f"[{inviter_name}](tg://user?id={message.from_user.id})"
        )

        invited_users = []

        for user in users:

            name = user.first_name or "ᴜsᴇʀ"

            invited_users.append(
                f"[{name}](tg://user?id={user.id})"
            )

        names = ", ".join(invited_users)

        text = (
            f"**❖ {inviter} ɪɴᴠɪᴛᴇᴅ {names} ᴏɴ ᴠᴄ ⚡**\n\n"
            f"**⏤͟͟͞͞★ ᴊᴏɪɴ ғᴀsᴛ & ᴇɴᴊᴏʏ ᴍᴜsɪᴄ 🎧**"
        )

        buttons = await get_buttons(client)

        await message.reply_text(
            text,
            reply_markup=buttons,
            disable_web_page_preview=True,
        )

    except Exception as e:
        print(f"VIDEO CHAT INVITE ERROR: {e}")


# ============================================================
# ❌ ᴄʟᴏsᴇ
# ============================================================

@app.on_callback_query(
    filters.regex("^close_vc_message$")
)
async def close_vc_message(client, query):

    try:

        await query.answer(
            "ᴄʟᴏsᴇᴅ ✨"
        )

        await query.message.delete()

    except Exception as e:

        print(f"VC CLOSE ERROR: {e}")

        try:
            await query.answer(
                "ᴄᴀɴɴᴏᴛ ᴄʟᴏsᴇ ᴛʜɪs ᴍᴇssᴀɢᴇ.",
                show_alert=True,
            )
        except Exception:
            pass
