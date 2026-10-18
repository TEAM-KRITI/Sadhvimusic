# ===========================================================
# ©️ 2025-26 All Rights Reserved by Purvi Bots (Im-Notcoder) 🚀
# 
# This source code is under MIT License 📜
# ❌ Unauthorized forking, importing, or using this code
#    without giving proper credit will result in legal action ⚠️
# 
# 📩 DM for permission : @TheSigmaCoder
# ===========================================================

from typing import Union

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ShiviMusic import app


def _btn(text, data):
    return InlineKeyboardButton(text=text, callback_data=data)


def help_pannel(_, START: Union[bool, int] = None):
    """Main help menu : 3x3 grid + BACK (screenshot jaisa)."""
    back_data = "settingsback_helper" if START else "close"
    back_text = "• ʙᴀᴄᴋ •" if START else _["CLOSE_BUTTON"]
    upl = InlineKeyboardMarkup(
        [
            [_btn("ᴀᴅᴍɪη", "help_callback hb1"), _btn("ᴀᴜᴛʜ", "help_callback hb2"), _btn("ᴄ-ᴘʟᴀʏ", "help_callback hb3")],
            [_btn("ʟᴏᴏᴘ", "help_callback hb4"), _btn("ᴘʟᴀʏ", "help_callback hb5"), _btn("sʜᴜғғɪʟᴇ", "help_callback hb6")],
            [_btn("sᴇᴇᴋ", "help_callback hb7"), _btn("sᴘᴇᴇᴅ", "help_callback hb8"), _btn("ᴇxᴛʀᴀ", "help_extra")],
            [_btn(back_text, back_data)],
        ]
    )
    return upl


def help_extra_panel(_):
    """EXTRA page : Welcome / Night Mode / Lock / Autoplay / Home."""
    return InlineKeyboardMarkup(
        [
            [_btn("ᴡᴇʟᴄᴏᴍᴇ", "help_callback hb10"), _btn("ɴɪɢʜᴛ ᴍᴏᴅᴇ", "help_callback hb11")],
            [_btn("ʟᴏᴄᴋ", "help_callback hb12"), _btn("ᴀᴜᴛᴏᴘʟᴀʏ", "help_callback hb13")],
            [_btn("• ʙᴀᴄᴋ •", "settings_back_helper"), _btn("ʜᴏᴍᴇ", "settingsback_helper")],
        ]
    )


def help_extra_back_markup(_):
    return InlineKeyboardMarkup([[_btn(_["BACK_BUTTON"], "help_extra")]])


def help_back_markup(_):
    upl = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=_["BACK_BUTTON"],
                    callback_data="settings_back_helper",
                ),
            ]
        ]
    )
    return upl


def private_help_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_4"],
                url=f"https://t.me/{app.username}?start=help",
            ),
        ],
    ]
    return buttons

# ===========================================================
# ©️ 2025-26 All Rights Reserved by Purvi Bots (Im-Notcoder) 😎
# 
# 🧑‍💻 Developer : t.me/TheSigmaCoder
# 🔗 Source link : GitHub.com/Im-Notcoder/Shivi-V2
# 📢 Telegram channel : t.me/Purvi_Bots
# ===========================================================
