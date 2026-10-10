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


def help_pannel(_, START: Union[bool, int] = None):
    first = [InlineKeyboardButton(text=_["CLOSE_BUTTON"], callback_data="close")]
    second = [
        InlineKeyboardButton(
            text=_["BACK_BUTTON"],
            callback_data="settingsback_helper",
        ),
    ]

    mark = second if START else first

    upl = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=_["H_B_25"],
                    callback_data="help_callback hb1",
                ),
                InlineKeyboardButton(
                    text=_["H_B_26"],
                    callback_data="help_callback hb2",
                ),
                InlineKeyboardButton(
                    text=_["H_B_28"],
                    callback_data="help_callback hb3",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=_["H_B_27"],
                    callback_data="help_callback hb4",
                ),
                InlineKeyboardButton(
                    text=_["H_B_31"],
                    callback_data="help_callback hb5",
                ),
                InlineKeyboardButton(
                    text=_["H_B_29"],
                    callback_data="help_callback hb6",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=_["H_B_33"],
                    callback_data="help_callback hb7",
                ),
                InlineKeyboardButton(
                    text=_["H_B_30"],
                    callback_data="help_callback hb8",
                ),
                InlineKeyboardButton(
                    text=_["H_B_32"],
                    callback_data="help_callback hb9",
                ),
            ],

            [
                InlineKeyboardButton(
                    text="• ᴡᴇʟᴄᴏᴍᴇ •",
                    callback_data="wel_cb",
                ),
                InlineKeyboardButton(
                    text="• ɴɪɢʜᴛᴍᴏᴅᴇ •",
                    callback_data="night_cb",
                ),
            ],

            mark,
        ]
    )
    return upl


def help_back_markup(_):
    upl = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=_["BACK_BUTTON"],
                    callback_data=f"settings_back_helper",
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
