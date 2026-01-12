import asyncio
import os
import config
from telethon import events
from handlers.utils import can_run_command

async def send_welcome_sequence(client, entity):
    """
    Envía la secuencia de bienvenida.
    """
    try:
        if os.path.exists(config.STICKER_FILENAME):
            # 👇 SOLUCIÓN: Agregamos mime_type='application/x-tgsticker'
            # Esto obliga a Telegram a renderizarlo como animación sí o sí.
            await client.send_file(
                entity, 
                config.STICKER_FILENAME, 
                force_document=False, 
                mime_type='application/x-tgsticker'
            )
        else:
            print(f"⚠️ Warning: {config.STICKER_FILENAME} not found.")
        
        await asyncio.sleep(1)
        await client.send_message(entity, config.MSG_WELCOME_1)
        
        await asyncio.sleep(1)
        await client.send_message(entity, config.MSG_WELCOME_2)
    except Exception as e:
        print(f"Error welcome: {e}")

async def handler_welcome(event):
    if event.user_joined or event.user_added:
        chat = await event.get_chat()
        
        # Verificar que es el grupo correcto
        if getattr(chat, 'username', '') == config.TARGET_GROUP:
            user = await event.get_user()
            if user.is_self or user.bot: return
            
            print(f"👤 New User: {user.first_name}. Waiting 60s to DM...")
            
            # Esperar 60 segundos
            await asyncio.sleep(60)
            
            try:
                # Enviamos al privado (user)
                await send_welcome_sequence(event.client, user)
                print(f"✅ Welcome sent to PM of {user.first_name}")
            except Exception as e:
                print(f"❌ Could not DM user: {e}")

async def handler_hello(event):
    if not await can_run_command(event): return
    await event.delete()
    
    # Test manual: Enviamos al chat actual para ver si el sticker funciona
    chat = await event.get_chat()
    await send_welcome_sequence(event.client, chat)
