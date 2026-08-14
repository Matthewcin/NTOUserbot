from telethon import events
from datetime import datetime
from database import db

# MAPA DE ESTADOS (Colores)
STATUS_MAP = {
    'working': '🟢',
    'ok': '🟢',
    'fix': '🟠',
    'needsfix': '🟠',
    'updated': '🔵',
    'fixed': '🔵',
    'dead': '🔴',
    'rip': '🔴',
    'checking': '⚪',
    'check': '⚪',
    'remade': '🟣',
    'new': '🟣'
}

# --- FUNCIÓN DE GENERACIÓN Y SINCRONIZACIÓN DE LA LISTA MAESTRA ---
async def generate_config_list_text():
    configs = await db.get_all_configs()
    if not configs: 
        return "📁 **Config List is Empty**"
    
    grouped = {}
    for conf in configs:
        cat = conf['category']
        if cat not in grouped: 
            grouped[cat] = []
        grouped[cat].append(conf)
        
    order = ['STREAMING', 'GAMING', 'EDUCATION', 'ADULT', 'FOOD', 'VPN', 'SHOP', 'UNSORTED', 'PRIVATE']
    
    text = f"🌐 **CONFIG CLOUD STATUS**\n🕒 {datetime.now().strftime('%d/%m %H:%M')}\n\n"
    text += "ℹ️ *Use `.cfg <Name>` para ver detalles técnicos.*\n\n"
    
    # Renderizar categorías ordenadas
    for cat in order:
        if cat in grouped:
            text += f"📂 **{cat}**\n"
            items = grouped[cat]
            for i, item in enumerate(items):
                is_last = (i == len(items) - 1)
                prefix = "└" if is_last else "├"
                price_tag = f" — `{item['price']}`" if item['price'] else ""
                text += f"{prefix} {item['status']} {item['name']}{price_tag}\n"
            text += "\n"
            
    # Renderizar categorías personalizadas extra
    for cat in grouped:
        if cat not in order:
            text += f"📂 **{cat}**\n"
            items = grouped[cat]
            for i, item in enumerate(items):
                is_last = (i == len(items) - 1)
                prefix = "└" if is_last else "├"
                price_tag = f" — `{item['price']}`" if item['price'] else ""
                text += f"{prefix} {item['status']} {item['name']}{price_tag}\n"
            text += "\n"
            
    text += "📝 **Legend:**\n🟢 Working | 🔴 Not Working | 🟠 To Fix | 🔵 Fixed | 🟣 Remade | ⚪ Checking"
    return text

async def sync_list_message(event):
    chat_id = event.chat_id
    topic_id = getattr(event.message, 'reply_to_msg_id', None)
    
    msg_data = await db.get_list_message(chat_id)
    new_text = await generate_config_list_text()
    
    if msg_data and msg_data.get('message_id'):
        try:
            await event.client.edit_message(chat_id, msg_data['message_id'], new_text, parse_mode='markdown')
            return True
        except Exception:
            pass
            
    sent_msg = await event.client.send_message(chat_id, new_text, reply_to=topic_id, parse_mode='markdown')
    await db.set_list_message(chat_id, sent_msg.id, topic_id=topic_id)
    return True


# --- 1. COMANDO .CFGLIST ---
async def handler_cfglist(event):
    if not event.out: return
    await event.delete()
    await sync_list_message(event)


# --- 2. COMANDO .CFGSYNC ---
async def handler_cfgsync(event):
    if not event.out: return
    try:
        await sync_list_message(event)
        await event.edit("✅ **Cloud list synchronized successfully!**")
    except Exception as e:
        await event.edit(f"❌ **Error:** {str(e)}")


# --- 3. COMANDO .ADDCFG ---
async def handler_addcfg(event):
    if not event.out: return
    
    match = event.pattern_match
    if not match or len(match.groups()) < 1:
        await event.edit("❌ Use: `.addcfg <GROUP> <NAME> [PRICE]`\nEx: `.addcfg STREAMING Disney+`")
        return

    raw_args = match.group(1).strip()
    args = raw_args.split(maxsplit=1)
    if len(args) < 2:
        await event.edit("❌ Use: `.addcfg <GROUP> <NAME> [PRICE]`")
        return

    category = args[0].upper()
    remaining = args[1]
    
    parts = remaining.rsplit(' ', 1)
    name = remaining
    price = ""

    if len(parts) > 1:
        possible_price = parts[1]
        if '$' in possible_price or 'USD' in possible_price.upper() or possible_price.isdigit():
            name = parts[0]
            price = parts[1]

    if await db.add_config(category, name, price):
        await event.edit(f"✅ Added **{name}** to **{category}**.")
        try:
            await sync_list_message(event)
        except Exception:
            pass
    else:
        await event.edit(f"❌ Error. Maybe **{name}** already exists in **{category}**?")


# --- 4. COMANDO .DELCFG ---
async def handler_delcfg(event):
    if not event.out: return
    
    match = event.pattern_match
    if not match or len(match.groups()) < 1:
        await event.edit("❌ Use: `.delcfg <GROUP> <NAME>`")
        return

    raw_args = match.group(1).strip()
    args = raw_args.split(maxsplit=1)
    if len(args) < 2:
        await event.edit("❌ Use: `.delcfg <GROUP> <NAME>`")
        return

    category = args[0]
    name = args[1]

    if await db.del_config(category, name):
        await event.edit(f"🗑 Deleted **{name}** from **{category}**.")
        try:
            await sync_list_message(event)
        except Exception:
            pass
    else:
        await event.edit(f"❌ Config **{name}** not found in **{category}**.")


# --- 5. COMANDO .CFGSTATUS ---
async def handler_cfgstatus(event):
    if not event.out: return
    
    match = event.pattern_match
    if not match or len(match.groups()) < 1:
        await event.edit("❌ Use: `.cfgstatus <GROUP> <NAME> <STATUS>`")
        return

    args = match.group(1).strip().split()
    if len(args) < 3:
        await event.edit(
            "❌ Use: `.cfgstatus <GROUP> <NAME> <STATUS>`\n"
            "Status: working, fix, dead, check, updated, remade"
        )
        return

    category = args[0]
    status_key = args[-1].lower()
    name = " ".join(args[1:-1])

    if status_key not in STATUS_MAP:
        await event.edit("❌ Invalid Status. Use: working, fix, dead, check, updated, remade")
        return

    new_emoji = STATUS_MAP[status_key]

    if await db.update_config_status(category, name, new_emoji):
        await event.edit(f"✅ Status updated for **{name}**: {new_emoji}")
        try:
            await sync_list_message(event)
        except Exception:
            pass
    else:
        await event.edit(f"❌ Config **{name}** not found in **{category}**.")


# --- 6. COMANDO .EDITCFG (Precio) ---
async def handler_editcfg(event):
    if not event.out: return
    
    match = event.pattern_match
    if not match or len(match.groups()) < 1:
        await event.edit("❌ Use: `.editcfg <GROUP> <NAME> <PRICE>`")
        return

    args = match.group(1).strip().split()
    if len(args) < 3:
        await event.edit("❌ Use: `.editcfg <GROUP> <NAME> <PRICE>`")
        return

    category = args[0]
    price = args[-1]
    name = " ".join(args[1:-1])

    if await db.update_config_price(category, name, price):
        await event.edit(f"✅ Price updated for **{name}**: {price}")
        try:
            await sync_list_message(event)
        except Exception:
            pass
    else:
        await event.edit(f"❌ Config **{name}** not found.")


# --- 7. COMANDO .CFG (Información detallada con árbol de capturas) ---
async def handler_cfg_info(event):
    match = event.pattern_match
    if not match or len(match.groups()) < 1:
        msg = await event.reply("❌ **Usage:** `.cfg [Config Name]`\nEx: `.cfg Disney+`")
        if event.out: await event.delete()
        return

    search_term = match.group(1).strip()
    conf = await db.get_config_by_name(search_term)
    
    if not conf:
        msg = await event.reply(f"❌ Config not found for: `{search_term}`")
        if event.out: await event.delete()
        return

    # Lógica de árbol para las capturas
    raw_capture = conf.get('capture', 'None')
    capture_tree = ""
    if raw_capture and raw_capture != 'None':
        captures = [c.strip() for c in raw_capture.split(',')]
        for i, cap in enumerate(captures):
            prefix = "└" if (i == len(captures) - 1) else "├"
            capture_tree += f"\n  {prefix} {cap}"
    else:
        capture_tree = " None"

    updated_str = conf['updated_at'].strftime("%Y-%m-%d") if conf.get('updated_at') else "Unknown"

    msg = (
        f"⚙️ **CONFIG INFORMATION**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ **Name:** `{conf['name']}`\n"
        f"📂 **Category:** {conf['category']}\n"
        f"📊 **Status:** {conf['status']}\n"
        f"🛒 **Price:** {conf['price'] if conf['price'] else 'Included in Cloud'}\n\n"
        f"📑 **Capture:** {capture_tree}\n\n"
        f"🔒 **Requires TLS:** {conf.get('requires_tls', 'No')}\n"
        f"📜 **Login Rules:** {conf.get('login_rules', 'None')}\n"
        f"🌐 **Proxies Admitted:** {conf.get('proxies_admitted', 'Any')}\n\n"
        f"📅 **Latest Update:** {updated_str}\n"
    )

    if event.out:
        await event.edit(msg)
    else:
        await event.reply(msg)


# --- 8. COMANDO .SETINFO (Admin para configurar detalles extra) ---
async def handler_setinfo(event):
    if not event.out: return
    
    match = event.pattern_match
    if not match or len(match.groups()) < 1:
        await event.edit("❌ Use: `.setinfo <NAME> | <CAPTURE> | <TLS> | <RULES> | <PROXIES>`")
        return

    args = match.group(1).strip().split('|')
    if len(args) < 5:
        await event.edit("❌ Format error. Use:\n`.setinfo NAME | capture1, cap2 | Yes/No | Rules | Any/Residential`")
        return

    name = args[0].strip()
    capture = args[1].strip()
    requires_tls = args[2].strip()
    login_rules = args[3].strip()
    proxies_admitted = args[4].strip()

    success = await db.update_config_extra_info(name, capture, requires_tls, login_rules, proxies_admitted)
    if success:
        await event.edit(f"✅ Extra info updated successfully for **{name}**.")
    else:
        await event.edit(f"❌ Config **{name}** not found.")


# --- 9. COMANDO .CFGALL ---
async def handler_cfgall(event):
    if not event.out: return
    # Comando de utilidad general si lo manejas aparte
    await event.edit("⚙️ Config All executed.")
