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
# GUEST MESSAGE
# ==========================================================

ADD_ME_PROMO_TEXT = (
    "❖ <a href=\"https://t.me/{username}\">˹{name}˼ ♪</a> — "
    "<b>𝐘꯭ᴏ꯭ᴜ꯭ʀ 𝐏꯭ʀ꯭ᴇ꯭ᴍ꯭ɪ꯭ᴜ꯭ᴍ 𝐌꯭ᴜ꯭s꯭ɪ꯭ᴄ 𝐒꯭ᴛ꯭ʀ꯭ᴇ꯭ᴀ꯭ᴍ꯭ᴇ꯭ʀ 𝐁꯭ᴏ꯭ᴛ 🍂</b>\n\n"

    "<blockquote>"
    "<b>▸ 𝐅꯭ᴀ꯭s꯭ᴛ ꯭༭꯭ • 𝐋꯭ᴀ꯭ɢ ꯭༭꯭ 𝐅꯭ʀ꯭ᴇ꯭ᴇ ꯭༭꯭ • 𝐍꯭ᴏ ꯭༭꯭ 𝐀꯭ᴅ꯭s 🍂</b>\n"
    "<b>▸ 𝐀꯭ᴜ꯭ᴛ꯭ᴏ-𝐏꯭ʟ꯭ᴀ꯭ʏ ꯭༭꯭ • 𝐀꯭ᴜ꯭ᴅ꯭ɪ꯭ᴏ ꯭༭꯭ • 𝐕꯭ɪ꯭ᴅ꯭ᴇ꯭ᴏ 🎥</b>"
    "</blockquote>\n\n"

    "<b>◼️ 𝐀꯭ᴅ꯭ᴅ</b> "
    "<a href=\"https://t.me/{username}\">˹{name}˼ ♪</a> "
    "<b>𝐓꯭ᴏ 𝐘꯭ᴏ꯭ᴜ꯭ʀ 𝐆꯭ʀ꯭ᴏ꯭ᴜ꯭ᴘ ꯭༭꯭ & 𝐄꯭ɴ꯭ᴊ꯭ᴏ꯭ʏ 𝐇꯭ɪ꯭ɢ꯭ʜ 𝐐꯭ᴜ꯭ᴀ꯭ʟ꯭ɪ꯭ᴛ꯭ʏ 𝐒꯭ᴏ꯭ɴ꯭ɢ ❄️</b>"
)


# ==========================================================
# BUTTONS
# ==========================================================

def _add_me_markup(username: str):

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="✙ 𝐀꯭ᴅ꯭ᴅ 𝐌꯭ᴇ ꯭༭꯭ 𝐈꯭ɴ 𝐘꯭ᴏ꯭ᴜ꯭ʀ 𝐆꯭ʀ꯭ᴏ꯭ᴜ꯭ᴘ ✙",
                    url=f"https://t.me/{username}?startgroup=true",
                )
            ]
        ]
    )


# ==========================================================
# GUEST MODE
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
        # GET BOT INFORMATION
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
        # CREATE MESSAGE
        # --------------------------------------------------

        promo_text = ADD_ME_PROMO_TEXT.format(
            name=name,
            username=username,
        )

        # --------------------------------------------------
        # KEYBOARD
        # --------------------------------------------------

        keyboard = _add_me_markup(username)

        # --------------------------------------------------
        # INLINE RESULT
        # --------------------------------------------------

        result = InlineQueryResultArticle(
            title=f"❖ 𝐌꯭ᴜ꯭s꯭ɪ꯭ᴄ 𝐁꯭ᴏ꯭ᴛ ♪",
            description=f"@{username} • 𝐀꯭ᴅ꯭ᴅ 𝐌꯭ᴇ ꯭༭꯭ 𝐈꯭ɴ 𝐘꯭ᴏ꯭ᴜ꯭ʀ 𝐆꯭ʀ꯭ᴏ꯭ᴜ꯭ᴘ 🎶",
            thumb_url="https://files.catbox.moe/qv2ob4.jpg",

            input_message_content=InputTextMessageContent(
                message_text=promo_text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            ),

            reply_markup=keyboard,
        )

        # --------------------------------------------------
        # ANSWER GUEST QUERY
        # --------------------------------------------------

        await app.answer_guest_query(
            guest_query_id,
            result=result,
        )

    except Exception as e:

        print(
            f"Guest Mode Error: {type(e).__name__}: {e}"
        )
