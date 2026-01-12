import asyncio
import os
import config
from telethon import events
# 👇 IMPORTANTE: Importamos los tipos necesarios para "engañar" a Telegram Desktop
from telethon.tl.types import DocumentAttributeSticker, InputStickerSetEmpty
from handlers.utils import can_run_command

async def send_welcome_sequence(client, entity):
    """
    Envía la secuencia de bienvenida forzando los atributos de Sticker.
    """
    try:
        if os.path.exists(config.STICKER_FILENAME):
            # 👇 SOLUCIÓN DEFINITIVA PARA PC:
            # Creamos el atributo que le dice a Telegram "Esto es un Sticker, no un archivo"
            sticker_attr = DocumentAttributeSticker(
                alt='👋',                     # Emoji alternativo (necesario)
                stickerset=InputStickerSetEmpty(), # No pertenece a ningún pack
                mask_coords=None
            )

            await client.send_file(
                entity, 
                config.STICKER_FILENAME, 
                force_document=False, 
                mime_type='application/x-tgsticker',
                attributes=[sticker_attr]     # <--- AQUÍ ESTÁ EL TRUCO
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
    
    # Test manual
    chat = await event.get_chat()
    await send_welcome_sequence(event.client, chat)
