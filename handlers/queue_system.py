from telethon import events
from database import db

# ==========================================
# 👤 COMANDOS DE USUARIO
# ==========================================

async def handler_request(event):
    # .request DisneyPlus
    text = event.message.text
    args = text.split()
    
    if len(args) != 2:
        await event.reply("❌ **Uso:** `.request [Servicio]` (Solo una palabra)\nEj: `.request Disney`")
        return

    service = args[1].strip()
    user = await event.get_sender()
    user_id = user.id
    username = getattr(user, 'username', 'NoUser') or 'NoUser'

    # Guardar en DB
    success, current_count = await db.add_request(user_id, username, service)

    if not success:
        await event.reply("❌ Tienes demasiadas peticiones pendientes (Máx 5). Espera a que atendamos las tuyas.")
        return

    # Calcular posición
    position = await db.get_user_position(user_id)
    
    if position == 1:
        msg = f"✅ **{service} Request Received!**\n\n🚀 **You're Next!** (Queue #1)\nPlease wait for an admin DM."
    else:
        msg = f"✅ **{service} Request Received!**\n\nYour Number in Queue is **#{position}**."

    await event.reply(msg)

async def handler_queue(event):
    # .q o .queue
    user = await event.get_sender()
    position = await db.get_user_position(user.id)

    if position == 0:
        await event.reply("📭 No estás en la fila de espera actualmente.")
    elif position == 1:
        await event.reply("🚀 **You're Next!** (#1)\nPrepare your DM.")
    else:
        await event.reply(f"clock: Estás en la posición **#{position}** de la fila.")

# ==========================================
# 👮‍♂️ COMANDOS DE ADMIN (SOLO TÚ)
# ==========================================

async def handler_qlist(event):
    # .qlist - Ver la lista completa
    if not event.out: return

    rows = await db.get_queue_list()
    
    if not rows:
        await event.edit("📭 **La fila está vacía.**")
        return

    msg = "📋 **QUEUE LIST**\n\n"
    for i, row in enumerate(rows):
        u_link = f"tg://user?id={row['user_id']}"
        msg += f"**#{i+1}** - {row['service_name']} | <a href='{u_link}'>{row['username']}</a>\n"
    
    await event.edit(msg, parse_mode='html')

async def handler_qa(event):
    # .qa - Aceptar el siguiente
    if not event.out: return

    # 1. Verificar si ya hay uno en proceso
    current = await db.get_processing_request()
    if current:
        await event.edit(f"⚠️ Ya estás atendiendo una petición: **{current['service_name']}** (User: {current['user_id']}).\nTermínala con `.qend` antes.")
        return

    # 2. Tomar el siguiente
    req = await db.pop_next_request()
    
    if not req:
        await event.edit("📭 No hay peticiones pendientes en la fila.")
        return

    # 3. Notificar al Admin (Tú)
    user_link = f"tg://user?id={req['user_id']}"
    chat_url = f"tg://resolve?domain={req['username']}" if req['username'] != 'NoUser' else user_link
    
    await event.edit(
        f"👨‍💻 **ACCEPTING REQUEST**\n\n"
        f"📦 **Service:** {req['service_name']}\n"
        f"👤 **User:** <a href='{user_link}'>{req['username']}</a> (ID: {req['user_id']})\n"
        f"🔗 **DM Link:** <a href='{chat_url}'>[CLICK TO CHAT]</a>",
        parse_mode='html'
    )

    # 4. Notificar al Usuario por DM
    try:
        await event.client.send_message(req['user_id'], 
            "👨‍💻 **Your request has been taken!**\n\n"
            "Please stay online. I will contact you shortly if I have questions."
        )
    except:
        await event.respond(f"⚠️ No pude enviar DM al usuario {req['user_id']} (Privacidad o bloqueo).")

async def handler_qend(event):
    # .qend success / .qend fail [razón] / .qend question [msg]
    if not event.out: return

    args = event.message.text.split(maxsplit=2)
    action = args[1].lower() if len(args) > 1 else ""

    # Obtener request actual
    req = await db.get_processing_request()
    if not req:
        await event.edit("❌ No hay ninguna petición activa (`processing`). Usa `.qa` primero.")
        return

    # --- SUCCESS ---
    if action == "success":
        await db.finish_request(req['id'], 'completed')
        
        # Avisar al usuario
        try:
            await event.client.send_message(req['user_id'], 
                f"✅ **Request Completed!**\n\nYour request for **{req['service_name']}** is done. Enjoy!"
            )
        except:
            pass

        # Mensaje final para ti
        await event.edit(f"✅ **Done.** Request #{req['id']} marked as success.")
        
        # Mostrar el SIGUIENTE en Saved Messages
        next_req = await db.get_queue_list()
        if next_req:
            top = next_req[0]
            await event.client.send_message('me', 
                f"🔔 **NEXT UP:** {top['service_name']} from {top['username']}\nUse `.qa` to take it."
            )
        else:
            await event.client.send_message('me', "🎉 Queue is empty! Good job.")

    # --- FAIL ---
    elif action == "fail":
        reason = args[2] if len(args) > 2 else "Unavailable"
        await db.finish_request(req['id'], 'failed')
        
        try:
            await event.client.send_message(req['user_id'], 
                f"❌ **Request Failed**\n\nService: {req['service_name']}\nReason: {reason}"
            )
        except:
            pass
            
        await event.edit(f"🗑 **Request Dropped.** User notified.")

    # --- QUESTION ---
    elif action == "question":
        if len(args) < 3:
            await event.edit("❌ Escribe la pregunta: `.qend question ¿Tienes VPN?`")
            return
        
        question = args[2]
        try:
            await event.client.send_message(req['user_id'], 
                f"❓ **Support Question**\n\nRegarding your request for {req['service_name']}:\n_\"{question}\"_"
            )
            await event.edit(f"✉️ Pregunta enviada al usuario.")
        except:
            await event.edit("❌ No se pudo enviar mensaje al usuario.")

    else:
        await event.edit("❌ Uso: `.qend success` | `.qend fail [razón]` | `.qend question [msg]`")
