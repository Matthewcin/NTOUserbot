from telethon import events
from database import db

# ==========================================
# 👤 COMANDOS DE USUARIO
# ==========================================

async def handler_request(event):
    # Comando: .request DisneyPlus
    text = event.message.text
    args = text.split()
    
    if len(args) != 2:
        await event.reply("❌ **Uso:** `.request [Servicio]` (Solo una palabra)\nEj: `.request Disney`")
        return

    service = args[1].strip()
    user = await event.get_sender()
    user_id = user.id
    # Intentar obtener username, si no tiene poner 'NoUser'
    username = getattr(user, 'username', 'NoUser') or 'NoUser'

    # Guardar en DB
    success, _ = await db.add_request(user_id, username, service)

    if not success:
        await event.reply("❌ Tienes demasiadas peticiones pendientes (Máx 5). Espera a que atendamos las tuyas.")
        return

    # Calcular posición
    position = await db.get_user_position(user_id)
    
    if position == 1:
        # Si es el primero en la fila (o el siguiente inmediato)
        msg = (
            f"✅ **{service} Request Received!**\n\n"
            f"🚀 **You're Next!** (Queue #1)\n"
            f"Please stay online and prepare your DM."
        )
    else:
        # Si hay gente delante
        msg = (
            f"✅ **{service} Request Received!**\n\n"
            f"Your Number in Queue is **#{position}**."
        )

    await event.reply(msg)

async def handler_queue(event):
    # Comando: .queue o .q
    user = await event.get_sender()
    position = await db.get_user_position(user.id)

    if position == 0:
        await event.reply("📭 No estás en la fila de espera actualmente.")
    elif position == 1:
        await event.reply("🚀 **You're Next!** (#1)\nPrepare your DM.")
    else:
        await event.reply(f"🕒 Estás en la posición **#{position}** de la fila.")

# ==========================================
# 👮‍♂️ COMANDOS DE ADMIN (SOLO TÚ)
# ==========================================

async def handler_qlist(event):
    # Comando: .qlist - Ver la lista completa
    if not event.out: return

    rows = await db.get_queue_list()
    
    if not rows:
        await event.edit("📭 **La fila está vacía.**")
        return

    msg = "📋 **QUEUE LIST**\n\n"
    for i, row in enumerate(rows):
        u_link = f"tg://user?id={row['user_id']}"
        display_name = row['username'] if row['username'] != 'NoUser' else f"ID:{row['user_id']}"
        msg += f"**#{i+1}** - {row['service_name']} | <a href='{u_link}'>{display_name}</a>\n"
    
    await event.edit(msg, parse_mode='html')

async def handler_qa(event):
    # Comando: .qa - Aceptar (Accept) el siguiente request
    if not event.out: return

    # 1. Verificar si ya hay uno en proceso
    current = await db.get_processing_request()
    if current:
        await event.edit(f"⚠️ Ya estás atendiendo una petición: **{current['service_name']}** (User: {current['user_id']}).\nTermínala con `.qend` antes.")
        return

    # 2. Tomar el siguiente de la DB
    req = await db.pop_next_request()
    
    if not req:
        await event.edit("📭 No hay peticiones pendientes en la fila.")
        return

    # 3. Notificar al Admin (Tú)
    user_link = f"tg://user?id={req['user_id']}"
    # Si tiene username, el link lleva al chat, si no, usa el ID
    chat_url = f"https://t.me/{req['username']}" if req['username'] != 'NoUser' else user_link
    
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
        # Si el usuario tiene privado bloqueado
        await event.respond(f"⚠️ No pude enviar DM al usuario {req['user_id']} (Privacidad).")

async def handler_qend(event):
    # Comandos: .qend success | .qend fail [razón] | .qend question [msg]
    if not event.out: return

    args = event.message.text.split(maxsplit=2)
    if len(args) < 2:
        await event.edit("❌ Uso: `.qend success` | `.qend fail [motivo]` | `.qend question [texto]`")
        return

    action = args[1].lower()

    # Obtener request que se está procesando
    req = await db.get_processing_request()
    if not req:
        await event.edit("❌ No hay ninguna petición activa. Usa `.qa` para tomar una.")
        return

    # --- CASO SUCCESS (FINALIZAR CON ÉXITO) ---
    if action == "success":
        await db.finish_request(req['id'], 'completed')
        
        # 1. Avisar al usuario actual
        try:
            await event.client.send_message(req['user_id'], 
                f"✅ **Request Completed!**\n\nYour request for **{req['service_name']}** is done. Enjoy!"
            )
        except: pass

        # 2. Mensaje final para ti
        await event.edit(f"✅ **Done.** Request #{req['id']} marked as success.")
        
        # 3. Revisar quién es el siguiente en la fila y notificar
        next_req_list = await db.get_queue_list()
        
        if next_req_list:
            top = next_req_list[0] # El siguiente en la fila
            
            # Avisar al Admin (Mensaje guardado o en el chat actual)
            await event.client.send_message('me', 
                f"🔔 **NEXT UP:** {top['service_name']} requested by {top['username']}\n"
                f"Use `.qa` to start processing it."
            )
            
            # Avisar al usuario que ahora es el #1 (Feature Extra)
            try:
                await event.client.send_message(top['user_id'],
                    "🚀 **You are next!**\nYour request is now #1 in the queue. Get ready!"
                )
            except: pass

        else:
            await event.client.send_message('me', "🎉 Queue is empty! Good job.")

    # --- CASO FAIL (FINALIZAR CON ERROR) ---
    elif action == "fail":
        reason = args[2] if len(args) > 2 else "Unavailable"
        await db.finish_request(req['id'], 'failed')
        
        try:
            await event.client.send_message(req['user_id'], 
                f"❌ **Request Failed**\n\nService: {req['service_name']}\nReason: {reason}"
            )
        except: pass
            
        await event.edit(f"🗑 **Request Dropped.** User notified.")

    # --- CASO QUESTION (PREGUNTAR ALGO) ---
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
            await event.edit("❌ No se pudo enviar mensaje al usuario (Privacidad).")

    else:
        await event.edit("❌ Acción desconocida. Usa success, fail o question.")
