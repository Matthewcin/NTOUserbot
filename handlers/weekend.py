import datetime
from telethon import events

notified_users = {}

async def handler_weekend_autoresponder(event):
    if not getattr(event, 'is_private', True):
        return

    now = datetime.datetime.now()
    weekday = now.weekday()

    if weekday not in [5, 6]:
        return

    user_id = event.sender_id
    today_str = now.strftime("%Y-%m-%d")

    if notified_users.get(user_id) == today_str:
        return

    notified_users[user_id] = today_str

    msg = (
        "Hey! This is an automated message from CoronaBot.\n\n"
        "I just wanted to let you know that I don't work on weekends. "
        "I take this time to rest from IRL work, studying, and to spend time with my family\n\n"
        "If it's something urgent, leave your message and I'll try to get back to you as soon as possible.\n\n"
        "Thanks for understanding!"
    )

    await event.reply(msg)
