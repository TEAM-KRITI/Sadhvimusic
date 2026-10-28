from pyrogram.enums import ParseMode
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Message,
)

from ShiviMusic import app


# ==========================================================
# ɢᴜєꜱᴛ ᴍєꜱꜱᴀɢє
# ==========================================================

ADD_ME_PROMO_TEXT = (
    "❖ <a href=\"https://t.me/{username}\">˹{name}˼ ♪</a> — "
    "<b>ʏᴏᴜʀ ᴘʀєᴍɪᴜᴍ ᴍᴜꜱɪᴄ ꜱᴛʀєᴀᴍєʀ ʙᴏᴛ 🍂</b>\n\n"

    "<blockquote>"
    "<b>▸ ꜰᴀꜱᴛ ༭ • ʟᴀɢ ༭ ꜰʀєє ༭ • ɴᴏ ༭ ᴀᴅꜱ 🍂</b>\n"
    "<b>▸ ᴀᴜᴛᴏ-ᴘʟᴀʏ ༭ • ᴀᴜᴅɪᴏ ༭ • ᴠɪᴅєᴏ 🎥</b>"
    "</blockquote>\n\n"

    "<b>◼️ ᴀᴅᴅ</b> "
    "<a href=\"https://t.me/{username}\">˹{name}˼ ♪</a> "
    "<b>ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ ༭ & єɴᴊᴏʏ ʜɪɢʜ ǫᴜᴀʟɪᴛʏ ꜱᴏɴɢ ❄️</b>"
)


# ==========================================================
# ʙᴜᴛᴛᴏɴꜱ
# ==========================================================

def _add_me_markup(username: str):

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="✙ ᴀᴅᴅ ᴍє ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ ✙",
                    url=f"https://t.me/{username}?startgroup=true",
                )
            ]
        ]
    )


# ==========================================================
# ɢᴜєꜱᴛ ᴍᴏᴅє
# ==========================================================

@app.on_guest_message()
async def guest_username_mention(_, message: Message):

    guest_query_id = getattr(
        message,
        "guest_query_id",
        None,
    )

    if not guest_query_id:
        return

    try:

        # --------------------------------------------------
        # ɢєᴛ ʙᴏᴛ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ
        # --------------------------------------------------

        me = await app.get_me()

        # Full bot name
        name = me.first_name or "Music Bot"

        if me.last_name:
            name = f"{name} {me.last_name}"

        # Bot username
        username = me.username

        if not username:
            return

        # --------------------------------------------------
        # ᴄʀєᴀᴛє ᴍєꜱꜱᴀɢє
        # --------------------------------------------------

        promo_text = ADD_ME_PROMO_TEXT.format(
            name=name,
            username=username,
        )

        # --------------------------------------------------
        # ᴋєʏʙᴏᴀʀᴅ
        # --------------------------------------------------

        keyboard = _add_me_markup(username)

        # --------------------------------------------------
        # ɪɴʟɪɴє ʀєꜱᴜʟᴛ
        # --------------------------------------------------

        result = InlineQueryResultArticle(
            title="❖ ᴍᴜꜱɪᴄ ʙᴏᴛ ♪",
            description=f"@{username} • ᴀᴅᴅ ᴍє ༭ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ 🎶",
            thumb_url="https://files.catbox.moe/qv2ob4.jpg",

            input_message_content=InputTextMessageContent(
                message_text=promo_text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            ),

            reply_markup=keyboard,
        )

        # --------------------------------------------------
        # ᴀɴꜱᴡєʀ ɢᴜєꜱᴛ ǫᴜєʀʏ
        # --------------------------------------------------

        await app.answer_guest_query(
            guest_query_id,
            result=result,
        )

    except Exception as e:

        print(
            f"Guest Mode Error: {type(e).__name__}: {e}"
        )
