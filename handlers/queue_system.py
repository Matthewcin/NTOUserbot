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
        await event.reply("❌ **Uso:** `.request [Config / Account / Combo / Help]` (One Word Only!)\nEx: `.request DisneyPlus`")
        return

    service = args[1].strip()
    user = await event.get_sender()
    user_id = user.id
    # Intentar obtener username, si no tiene poner 'NoUser'
    username = getattr(user, 'username', 'NoUser') or 'NoUser'

    # Guardar en DB
    success, _ = await db.add_request(user_id, username, service)

    if not success:
        await event.reply("❌ You Have Too Many Requests Pending!" (Max 5). Please Wait.")
        return

    # Calcular posición
    position = await db.get_user_position(user_id)
    
    if position == 1:
        # Si es el primero en la fila (o el siguiente inmediato)
        msg = (
            f"✅ **{service} Request Received!**\n\n"
            f"🚀 **You're Next!** (Queue #1)\n"
            f"Please stay online, I'll be there Soon."
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
        await event.reply("📭 You're not in Queue.")
    elif position == 1:
        await event.reply("🚀 **You're Next!** (#1)\nPlease Check your DM Soon.")
    else:
        await event.reply(f"🕒 Your Position is **#{position}**.")

# ==========================================
# 👮‍♂️ COMANDOS DE ADMIN (SOLO TÚ)
# ==========================================

async def handler_qlist(event):
    # Comando: .qlist - Ver la lista completa
    if not event.out: return

    rows = await db.get_queue_list()
    
    if not rows:
        await event.edit("📭 **Queue is Empty.**")
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
        await event.edit(f"⚠️ You're Making a Request Already: **{current['service_name']}** (User: {current['user_id']}).\nClose it With `.qend` before.")
        return

    # 2. Tomar el siguiente de la DB
    req = await db.pop_next_request()
    
    if not req:
        await event.edit("📭 There's not Pending Requests.")
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
            "👀 **Your request has been taken!**\n\n"
            "Please stay online. I will contact you shortly if I have questions."
        )
    except:
        # Si el usuario tiene privado bloqueado
        await event.respond(f"⚠️ Unexpected Error Sending DM to {req['user_id']} (Private).")

async def handler_qend(event):
    # Comandos: .qend success | .qend fail [razón] | .qend question [msg]
    if not event.out: return

    args = event.message.text.split(maxsplit=2)
    if len(args) < 2:
        await event.edit("❌ Use: `.qend success` | `.qend fail [reason]` | `.qend question [text]`")
        return

    action = args[1].lower()

    # Obtener request que se está procesando
    req = await db.get_processing_request()
    if not req:
        await event.edit("❌ There's no Active Requests. Use `.qa` to take One.")
        return

    # --- CASO SUCCESS (FINALIZAR CON ÉXITO) ---
    if action == "success":
        await db.finish_request(req['id'], 'completed')
        
        # 1. Avisar al usuario actual
        try:
            await event.client.send_message(req['user_id'], 
                f"✅ **Request Completed!**\n\nYour request for **{req['service_name']}** is done.!"
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
            await event.edit("❌ Write a Question: `.qend question ¿Do you have VPN? / ¿Can you send any account for testing?`")
            return
        
        question = args[2]
        try:
            await event.client.send_message(req['user_id'], 
                f"❓ **Support Question**\n\nRegarding your request for {req['service_name']}:\n_\"{question}\"_"
            )
            await event.edit(f"✉️ Question has been Sent to The User.")
        except:
            await event.edit("❌ Message can't be sent (Privacy).")

    else:
        await event.edit("❌ Unknown Command. Use success, fail or question.")
