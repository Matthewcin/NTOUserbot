import asyncio
import os
import config
from telethon import events
from handlers.utils import can_run_command

async def send_welcome_sequence(client, chat):
    try:
        if os.path.exists(config.STICKER_FILENAME):
            await client.send_file(chat, config.STICKER_FILENAME)
        
        await asyncio.sleep(1)
        await client.send_message(chat, config.MSG_WELCOME_1)
        
        await asyncio.sleep(1)
        await client.send_message(chat, config.MSG_WELCOME_2)
    except Exception as e:
        print(f"Error welcome: {e}")

async def handler_welcome(event):
    if event.user_joined or event.user_added:
        chat = await event.get_chat()
        if getattr(chat, 'username', '') == config.TARGET_GROUP:
            user = await event.get_user()
            if user.is_self or user.bot: return
            
            print(f"👤 New User: {user.first_name}. Waiting 60s...")
            await asyncio.sleep(60)
            await send_welcome_sequence(event.client, chat)

async def handler_hello(event):
    if not await can_run_command(event): return
    await event.delete()
    await send_welcome_sequence(event.client, await event.get_chat())
