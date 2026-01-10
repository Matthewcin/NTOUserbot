import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from keep_alive import start_server

# ==========================================
# ⚙️ CONFIGURACIÓN DESDE RENDER
# ==========================================
# Usamos os.getenv para leer las variables de Render
API_ID = int(os.getenv('API_ID', '32541501'))
API_HASH = os.getenv('API_HASH', '66f7a1c72eac5d25705ef1d35275ca4f')
SESSION_STRING = os.getenv('SESSION_STRING')

# Configuración del bot
TARGET_GROUP = 'myConfigCloud'
STICKER_PATH = 'sticker.tgs'
WELCOME_MSG = "¡Hola! 👋 Vi que te uniste a mi Cloud. Si necesitas precios o info, escribe .info aquí mismo."

# ==========================================
# 🚀 INICIO CON STRING SESSION
# ==========================================

if not SESSION_STRING:
    print("❌ Error: No encontré la SESSION_STRING en las variables de entorno.")
    exit()

# Iniciamos el cliente usando la cadena de texto en lugar de un archivo .session
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

@client.on(events.ChatAction)
async def welcome_handler(event):
    if event.user_joined or event.user_added:
        chat = await event.get_chat()
        if chat.username == TARGET_GROUP:
            user = await event.get_user()
            if user.is_self or user.bot: return
            
            print(f"👤 {user.first_name} entró. Esperando 3 minutos...")
            await asyncio.sleep(180)
            
            try:
                # Nota: Si el archivo sticker.tgs no existe en Render, esto fallará.
                # Asegúrate de subirlo al repo.
                if os.path.exists(STICKER_PATH):
                    await client.send_file(user.id, STICKER_PATH)
                await client.send_message(user.id, WELCOME_MSG)
                print(f"✅ DM enviado a {user.first_name}")
            except Exception as e:
                print(f"❌ Error enviando DM: {e}")

@client.on(events.NewMessage(incoming=True, pattern=r'\.info'))
async def public_commands(event):
    chat = await event.get_chat()
    es_privado = event.is_private
    es_mi_grupo = (chat.username == TARGET_GROUP)
    
    if es_privado or es_mi_grupo:
        await event.reply("☁️ **Info de myConfigCloud**\n\n• Proxys Residenciales\n• Configs OpenBullet\n\nEscríbeme para comprar.")

# ==========================================
# 🏁 EJECUCIÓN
# ==========================================
if __name__ == '__main__':
    print("🌍 Iniciando Web Server...")
    start_server()
    
    print("🚀 Iniciando Userbot...")
    client.start()
    client.run_until_disconnected()
