import asyncio
from telethon import TelegramClient, events

# ==========================================
# ⚙️ TUS CREDENCIALES
# ==========================================
API_ID = 32541501
API_HASH = '66f7a1c72eac5d25705ef1d35275ca4f'

# ==========================================
# 🎯 CONFIGURACIÓN
# ==========================================
TARGET_GROUP = 'myConfigCloud' 
STICKER_PATH = '773947703670342104.tgs' 
WELCOME_MSG = "¡Hola! 👋 Vi que te uniste a mi Cloud. Si necesitas precios o info, escribe .info aquí mismo."

# ==========================================
# 🤖 INICIO
# ==========================================
client = TelegramClient('mi_sesion_personal', API_ID, API_HASH)

print(f"🚀 Userbot Privado Iniciado. Escuchando en: {TARGET_GROUP} y DMs.")

# ---------------------------------------------------------
# 1️⃣ SALUDO POR PRIVADO (DM)
# ---------------------------------------------------------
@client.on(events.ChatAction)
async def welcome_handler(event):
    if event.user_joined or event.user_added:
        chat = await event.get_chat()
        
        # Solo si se unen a TU grupo específico
        if chat.username == TARGET_GROUP:
            user = await event.get_user()
            
            # Evitamos saludarnos a nosotros mismos o a bots
            if user.is_self or user.bot:
                return

            print(f"👤 {user.first_name} entró. Esperando 3 minutos para enviar DM...")
            
            # ⏳ ESPERA DE 3 MINUTOS
            await asyncio.sleep(180)
            
            try:
                # Enviamos mensaje AL USUARIO (user.id), no al chat
                await client.send_file(user.id, STICKER_PATH)
                await client.send_message(user.id, WELCOME_MSG)
                print(f"✅ DM enviado a {user.first_name}")
            except Exception as e:
                print(f"❌ No se pudo enviar DM a {user.first_name} (Quizás tiene privacidad activada): {e}")

# ---------------------------------------------------------
# 2️⃣ COMANDOS PÚBLICOS (Para la gente)
# ---------------------------------------------------------
# Este decorador permite que OTROS usen tus comandos (incoming=True)
@client.on(events.NewMessage(incoming=True, pattern=r'\.info'))
async def public_commands(event):
    """
    Ejemplo de comando (.info) que la gente puede usar.
    Solo funciona en Privado O en tu Grupo de Cloud.
    """
    chat = await event.get_chat()
    sender = await event.get_sender()
    
    # 🕵️‍♂️ FILTRO DE SEGURIDAD
    # Permitir si es chat privado (DM) O si es tu grupo específico
    es_privado = event.is_private
    es_mi_grupo = (chat.username == TARGET_GROUP)
    
    if es_privado or es_mi_grupo:
        # Aquí pones la respuesta de tu comando
        await event.reply(
            "☁️ **Info de myConfigCloud**\n\n"
            "• Dispongo de proxys residenciales.\n"
            "• Configuraciones OpenBullet.\n"
            "• Scripts a medida.\n\n"
            "Escríbeme al privado para comprar."
        )
        print(f"✅ Comando .info ejecutado por {sender.first_name} en {chat.title if not es_privado else 'Privado'}")
    else:
        # Si alguien lo intenta usar en otro grupo, el bot lo ignora
        return

# ---------------------------------------------------------
# 3️⃣ TUS COMANDOS DE ADMIN (Solo tú)
# ---------------------------------------------------------
@client.on(events.NewMessage(outgoing=True, pattern=r'\.ping'))
async def admin_ping(event):
    await event.edit("🏓 Pong! El bot está activo.")

with client:
    client.run_until_disconnected()
