# ===========================================================
# ©️ 2025-26 All Rights Reserved by Purvi Bots (Im-Notcoder) 🚀
#
# This source code is under MIT License 📜
# ===========================================================

from pyrogram.types import InlineKeyboardButton

import config
from ShiviMusic import app


# ===========================================================
# START PANEL
# ===========================================================

def start_panel(_):

    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_1"],
                url=f"https://t.me/{app.username}?startgroup=true",
            ),
            InlineKeyboardButton(
                text=_["S_B_2"],
                url=config.SUPPORT_CHAT,
            ),
        ],
    ]

    return buttons


# ===========================================================
# PRIVATE PANEL
# ===========================================================

def private_panel(_):

    buttons = [
        [
            InlineKeyboardButton(
                text="✚ ᴀᴅᴅ ᴍᴇ ɪη ʏᴏᴜʀ ɢʀᴏᴜᴘ ✚",
                url=f"https://t.me/{app.username}?startgroup=true",
            )
        ],
        [
            InlineKeyboardButton(
                text="• ᴏᴡɴᴇʀ •",
                user_id=config.OWNER_ID,
            ),
            InlineKeyboardButton(
                text="• sᴜᴘᴘᴏʀᴛ •",
                url=config.SUPPORT_CHAT,
            ),
        ],
        [
            InlineKeyboardButton(
                text="⌜ ʜᴇʟᴘ ᴀηᴅ ᴄᴏᴍᴍᴀηᴅs ⌟",
                callback_data="settings_back_helper",
            )
        ],
    ]

    return buttons


# ===========================================================
# ©️ 2025-26 All Rights Reserved by Purvi Bots (Im-Notcoder)
#
# 🧑‍💻 Developer : t.me/TheSigmaCoder
# 🔗 Source link : GitHub.com/Im-Notcoder/Shivi-V2
# 📢 Telegram channel : t.me/Purvi_Bots
# ===========================================================
