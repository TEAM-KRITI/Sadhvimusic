# Anonymous admin support
# Jab koi admin "Remain Anonymous" ON karke command deta hai to message.from_user = None
# aur message.sender_chat = group khud hota hai. Telegram ke hisaab se aisa message
# sirf group ka admin hi bhej sakta hai, isliye usko admin maan ke command chala dete hain.
from pyrogram.types import User

ANON_ADMIN_ID = 1087968824  # Telegram ka official "GroupAnonymousBot" id


def make_anon_admin(client, message) -> bool:
    """Anonymous admin ho to message.from_user set kar deta hai aur True return karta hai.
    Linked channel ya dusre channel ke messages ke liye False (unko allow nahi karte)."""
    sc = getattr(message, "sender_chat", None)
    if not sc or sc.id != message.chat.id:
        return False
    message.from_user = User(
        id=ANON_ADMIN_ID,
        is_bot=True,
        first_name="Anonymous Admin",
        client=client,
    )
    message.is_anon_admin = True
    return True


def is_anon_admin(message) -> bool:
    return bool(getattr(message, "is_anon_admin", False))
