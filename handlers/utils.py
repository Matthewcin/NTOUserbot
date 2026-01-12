import config
from telethon import events

async def can_run_command(event):
    if event.out: return True
    chat = await event.get_chat()
    es_privado = event.is_private
    es_mi_grupo = (getattr(chat, 'username', '') == config.TARGET_GROUP)
    return es_privado or es_mi_grupo
