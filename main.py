import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from keep_alive import start_server

# ==========================================
# ⚙️ CONFIGURACIÓN (VARIABLES DE ENTORNO)
# ==========================================
API_ID = int(os.getenv('API_ID', '32541501'))
API_HASH = os.getenv('API_HASH', '66f7a1c72eac5d25705ef1d35275ca4f'))
SESSION_STRING = os.getenv('SESSION_STRING') 

# TU CONFIGURACIÓN
TARGET_GROUP = 'myConfigCloud'
MY_USER_LINK = 'https://t.me/Virusnto' # Tu usuario para que te hagan clic
STICKER_WELCOME = 'sticker.tgs' 

# ==========================================
# 🚀 INICIO DEL CLIENTE
# ==========================================
if not SESSION_STRING:
    print("❌ Error: Falta SESSION_STRING")
    exit()

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==========================================
# 🛠️ FUNCIONES DE AYUDA
# ==========================================
async def check_permissions(event):
    """Verifica si el comando se usa en Privado o en el Grupo permitido."""
    chat = await event.get_chat()
    es_privado = event.is_private
    es_mi_grupo = (getattr(chat, 'username', '') == TARGET_GROUP)
    return es_privado or es_mi_grupo

# ==========================================
# 👋 BIENVENIDA AUTOMÁTICA
# ==========================================
@client.on(events.ChatAction)
async def welcome_handler(event):
    if event.user_joined or event.user_added:
        chat = await event.get_chat()
        if getattr(chat, 'username', '') == TARGET_GROUP:
            user = await event.get_user()
            if user.is_self or user.bot: return
            
            print(f"👤 {user.first_name} entró. Esperando 3 min...")
            await asyncio.sleep(180)
            
            try:
                msg = (
                    f"¡Hola {user.first_name}! 👋\n"
                    "Bienvenido a **myConfigCloud**.\n\n"
                    "Usa los siguientes comandos para interactuar:\n"
                    "🔹 `.list` - Ver catálogo\n"
                    "🔹 `.buy` - Comprar acceso\n"
                    "🔹 `.info` - Más detalles\n\n"
                    f"💬 **[CONTACTAR DUEÑO]({MY_USER_LINK})**"
                )
                if os.path.exists(STICKER_WELCOME):
                    await client.send_file(user.id, STICKER_WELCOME)
                await client.send_message(user.id, msg)
            except Exception:
                pass

# ==========================================
# 🟢 COMANDO: .STATUS
# ==========================================
@client.on(events.NewMessage(pattern=r'\.status'))
async def cmd_status(event):
    if not await check_permissions(event): return
    
    await event.reply(
        "🟢 **SYSTEM ONLINE**\n"
        "━━━━━━━━━━━━━━━━\n"
        "⚡ **Latency:** 24ms\n"
        "🛡️ **Security:** Encrypted\n"
        "👤 **Owner:** Online\n"
        "━━━━━━━━━━━━━━━━"
    )

# ==========================================
# 📂 COMANDO: .LIST / .CONFIGS / .CLOUD
# ==========================================
@client.on(events.NewMessage(pattern=r'\.(list|configs|cloud)'))
async def cmd_list(event):
    if not await check_permissions(event): return

    await event.reply(
        "📂 **CATÁLOGO DISPONIBLE**\n\n"
        "Selecciona un producto para ver detalles:\n\n"
        "1️⃣ **EBOOK (Guía Exclusiva)**\n"
        "   └─ *Precio: $75 USD*\n"
        "   └─ Comando: `.info ebook`\n\n"
        "2️⃣ **CONFIG CLOUD (OpenBullet)**\n"
        "   └─ *Acceso a configs privadas*\n"
        "   └─ Comando: `.info cloud`\n\n"
        "👇 **ACCIONES RÁPIDAS**\n"
        f"💳 **[COMPRAR AHORA]({MY_USER_LINK})**"
    )

# ==========================================
# ℹ️ COMANDO: .INFO [ARGUMENTO]
# ==========================================
@client.on(events.NewMessage(pattern=r'\.info(?:\s+(.*))?'))
async def cmd_info(event):
    if not await check_permissions(event): return
    
    arg = event.pattern_match.group(1) # Captura lo que escriben después de .info
    
    if not arg:
        # Si no ponen argumento, mostramos ayuda
        await event.reply("ℹ️ **Uso:** `.info ebook` o `.info cloud`")
        return

    arg = arg.lower()

    if "ebook" in arg:
        await event.reply(
            "📘 **INFO: EBOOK EXCLUSIVO**\n"
            "━━━━━━━━━━━━━━━━\n"
            "Aprende a crear tus propias configs y bots.\n\n"
            "✅ **Contenido:**\n"
            "• Introducción a OpenBullet\n"
            "• Bypassing de seguridad\n"
            "• Captura de APIs\n\n"
            "💰 **Precio:** $75 USD (Lifetime)\n"
            f"👉 **[COMPRAR EBOOK]({MY_USER_LINK})**"
        )
    elif "cloud" in arg or "config" in arg:
        await event.reply(
            "☁️ **INFO: CONFIG CLOUD**\n"
            "━━━━━━━━━━━━━━━━\n"
            "Acceso a mi nube privada de configuraciones.\n\n"
            "✅ **Características:**\n"
            "• Actualizaciones diarias\n"
            "• +50 Sitios soportados\n"
            "• Soporte 24/7\n\n"
            f"👉 **[SOLICITAR ACCESO]({MY_USER_LINK})**"
        )
    else:
        await event.reply("❌ Producto no encontrado. Usa `.list` para ver el catálogo.")

# ==========================================
# 💳 COMANDO: .BUY [ARGUMENTO]
# ==========================================
@client.on(events.NewMessage(pattern=r'\.buy(?:\s+(.*))?'))
async def cmd_buy(event):
    if not await check_permissions(event): return

    arg = event.pattern_match.group(1)
    
    if not arg:
        await event.reply(
            "💳 **¿QUÉ DESEAS COMPRAR?**\n\n"
            "Escribe el comando específico:\n"
            "• `.buy ebook` ($75 USD)\n"
            "• `.buy cloud` (Consultar)\n\n"
            "O contáctame directo:\n"
            f"👤 **[HABLAR CONMIGO]({MY_USER_LINK})**"
        )
        return

    arg = arg.lower()
    
    if "ebook" in arg:
        await event.reply(
            "💳 **PROCESO DE COMPRA: EBOOK**\n"
            "━━━━━━━━━━━━━━━━\n"
            "💵 **Total:** $75 USD\n"
            "🪙 **Métodos:** USDT (TRC20), BTC, LTC\n\n"
            "⚠️ **Nota:** Para evitar estafas, no envíes dinero sin confirmación.\n\n"
            f"📩 **[ENVIAR MENSAJE PARA PAGAR]({MY_USER_LINK})**"
        )
    elif "cloud" in arg:
        await event.reply(
            "💳 **PROCESO DE COMPRA: CLOUD**\n"
            "━━━━━━━━━━━━━━━━\n"
            "El acceso a la Cloud es limitado.\n\n"
            f"📩 **[CONSULTAR DISPONIBILIDAD]({MY_USER_LINK})**"
        )

# ==========================================
# 📝 COMANDO: .REQUEST [ACCOUNT/CONFIG]
# ==========================================
@client.on(events.NewMessage(pattern=r'\.request(?:\s+(.*))?'))
async def cmd_request(event):
    if not await check_permissions(event): return

    arg = event.pattern_match.group(1)
    sender = await event.get_sender()
    
    if not arg:
        await event.reply("📝 **Uso:** `.request config netflix` o `.request account amazon`")
        return

    # Logica visual: Confirmamos al usuario que recibimos la petición
    # Como es tu cuenta personal, tú verás el mensaje original en tu chat de todos modos.
    await event.reply(
        f"✅ **SOLICITUD RECIBIDA**\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👤 **Usuario:** {sender.first_name}\n"
        f"📦 **Pedido:** {arg}\n\n"
        "He anotado tu solicitud. Si es viable, la añadiré a la Cloud pronto."
    )

# ==========================================
# 🏁 EJECUCIÓN
# ==========================================
if __name__ == '__main__':
    print("🌍 Iniciando Web Server...")
    start_server()
    print("🚀 Userbot Activo y escuchando comandos...")
    client.start()
    client.run_until_disconnected()
