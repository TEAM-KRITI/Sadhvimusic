# ======================================================
# ©️ 2025-26 All Rights Reserved by Kirti 😎
#
# 🧑‍💻 Developer : t.me/lll_APNA_BADNAM_BABY_lll
# 🔗 Source link : https://github.com/Badnam019
# 📢 Telegram channel : t.me/lll_APNA_BADNAM_BABY_lll
# ======================================================

from typing import Union
from ShiviMusic import app
from ShiviMusic.utils.formatters import time_to_seconds
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ButtonStyle


def queue_markup(
    _,
    DURATION,
    CPLAY,
    videoid,
    played: Union[bool, int] = None,
    dur: Union[bool, int] = None,
):
    not_dur = [
        [
            InlineKeyboardButton(
                text="𝐐꯭ᴜ꯭ᴇ꯭ᴜ꯭ᴇ ꯭༭꯭ 𝐋꯭ɪ꯭s꯭ᴛ",
                callback_data=f"GetQueued {CPLAY}|{videoid}",
                style=ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                text="𝐂꯭ʟ꯭ᴏ꯭s꯭ᴇ",
                callback_data="close",
                style=ButtonStyle.DANGER,
            ),
        ]
    ]

    dur = [
        [
            InlineKeyboardButton(
                text=f"𝐓꯭ɪ꯭ᴍ꯭ᴇ ꯭༭꯭ {played} / {dur}",
                callback_data="GetTimer",
                style=ButtonStyle.SUCCESS,
            )
        ],
        [
            InlineKeyboardButton(
                text="𝐐꯭ᴜ꯭ᴇ꯭ᴜ꯭ᴇ ꯭༭꯭ 𝐋꯭ɪ꯭s꯭ᴛ",
                callback_data=f"GetQueued {CPLAY}|{videoid}",
                style=ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                text="𝐂꯭ʟ꯭ᴏ꯭s꯭ᴇ",
                callback_data="close",
                style=ButtonStyle.DANGER,
            ),
        ],
    ]

    upl = InlineKeyboardMarkup(
        not_dur if DURATION == "Unknown" else dur
    )

    return upl


def queue_back_markup(_, CPLAY):
    upl = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="𝐁꯭ᴀ꯭ᴄ꯭ᴋ",
                    callback_data=f"queue_back_timer {CPLAY}",
                    style=ButtonStyle.PRIMARY,
                ),
                InlineKeyboardButton(
                    text="𝐂꯭ʟ꯭ᴏ꯭s꯭ᴇ",
                    callback_data="close",
                    style=ButtonStyle.DANGER,
                ),
            ]
        ]
    )

    return upl


def aq_markup(_, chat_id):
    buttons = [
        [
            InlineKeyboardButton(
                text="𝐉꯭ᴏ꯭ɪ꯭ɴ ꯭𝐍꯭ᴏ꯭ᴡ",
                url="https://t.me/kirti_bots",
                style=ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                text="𝐆꯭ʀ꯭ᴏ꯭ᴜ꯭ᴘ 𝐂꯭ʜ꯭ᴀ꯭ᴛ",
                url="https://t.me/kirti_bots_support",
                style=ButtonStyle.SUCCESS,
            ),
        ],
        [
            InlineKeyboardButton(
                text="𝐂꯭ʟ꯭ᴏ꯭s꯭ᴇ",
                callback_data="close",
                style=ButtonStyle.DANGER,
            )
        ],
    ]

    return buttons


# ======================================================
# ©️ 2025-26 All Rights Reserved by Kirti 😎
#
# 🧑‍💻 Developer : t.me/lll_APNA_BADNAM_BABY_lll
# 🔗 Source link : https://github.com/Badnam019
# 📢 Telegram channel : t.me/lll_APNA_BADNAM_BABY_lll
# ======================================================
