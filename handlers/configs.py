from telethon import events
from database import db
from handlers.utils import can_run_command

STATUS_MAP = {
    'working': '🟢', 'ok': '🟢',
    'fix': '🟠', 'needsfix': '🟠',
    'updated': '🔵', 'fixed': '🔵',
    'dead': '🔴', 'rip': '🔴',
    'checking': '⚪', 'check': '⚪',
    'remade': '🟣', 'new': '🟣'
}

async def generate_config_list_text():
    configs = await db.get_all_configs()
    if not configs: return "📁 **Config List is Empty**"
    
    grouped = {}
    for conf in configs:
        cat = conf['category']
        if cat not in grouped: grouped[cat] = []
        grouped[cat].append(conf)
        
    order = ['STREAMING', 'GAMING', 'EDUCATION', 'ADULT', 'FOOD', 'VPN', 'SHOP', 'UNSORTED', 'PRIVATE']
    
    text = "🌐 **CONFIG CLOUD DYNAMIC LIST**\n\n"
    
    for cat in order:
        if cat in grouped:
            text += f"📂 **{cat}**\n"
            # Iteramos sobre la lista para saber cuál es el último elemento
            items = grouped[cat]
            for i, item in enumerate(items):
                is_last = (i == len(items) - 1)
                prefix = "└" if is_last else "├"
                
                price_tag = f" - {item['price']}" if item['price'] else ""
                text += f"{prefix} {item['status']} {item['name']}{price_tag}\n"
            text += "\n"
            
    text += "📝 **Legend:**\n🟢 Working | 🔴 Not Working | 🟠 To Fix\n🔵 Fixed/Updated | 🟣 Remade | ⚪ Checking"
    return text

async def sync_list_message(event):
    chat_id = event.chat_id
    msg_data = await db.get_list_message(chat_id)
    new_text = await generate_config_list_text()
    if msg_data:
        try:
            await event.client.edit_message(chat_id, msg_data['message_id'], new_text, parse_mode='markdown')
            return True
        except: pass
    reply_to = event.message.reply_to_msg_id if event.is_reply else None
    sent_msg = await event.client.send_message(chat_id, new_text, reply_to=reply_to, parse_mode='markdown')
    await db.set_list_message(chat_id, sent_msg.id)

async def handler_cfgsync(event):
    if not await can_run_command(event): return
    await sync_list_message(event)
    await event.delete()

async def handler_cfglist(event):
    if not event.out: return
    await sync_list_message(event)
    await event.delete()

async def handler_addcfg(event):
    if not await can_run_command(event): return
    args = event.message.text.split(maxsplit=2)
    if len(args) < 3:
        await event.edit("❌ Use: `.addcfg <GROUP> <NAME> [PRICE]`")
        return
    category = args[1].upper()
    remaining = args[2]
    parts = remaining.rsplit(' ', 1)
    name = remaining
    price = ""
    if len(parts) > 1:
        possible_price = parts[1]
        if '$' in possible_price or 'USD' in possible_price.upper() or possible_price.isdigit():
            name = parts[0]
            price = parts[1]
    if await db.add_config(category, name, price):
        await event.edit(f"✅ Added **{name}**.")
        await sync_list_message(event)

async def handler_delcfg(event):
    if not await can_run_command(event): return
    args = event.message.text.split(maxsplit=2)
    if len(args) < 3: return
    if await db.del_config(args[1], args[2]):
        await event.edit("🗑 Deleted.")
        await sync_list_message(event)

async def handler_cfgstatus(event):
    if not await can_run_command(event): return
    args = event.message.text.split()
    category, status_key, name = args[1], args[-1].lower(), " ".join(args[2:-1])
    if status_key in STATUS_MAP and await db.update_config_status(category, name, STATUS_MAP[status_key]):
        await event.edit("✅ Status updated.")
        await sync_list_message(event)

async def handler_editcfg(event):
    if not await can_run_command(event): return
    args = event.message.text.split()
    category, price, name = args[1], args[-1], " ".join(args[2:-1])
    if await db.update_config_price(category, name, price):
        await event.edit("✅ Price updated.")
        await sync_list_message(event)

async def handler_cfg_info(event):
    if not await can_run_command(event): return
    
    args = event.message.text.split(maxsplit=1)
    if len(args) < 2:
        msg = await event.reply("❌ **Usage:** `.cfg [Config Name]`\nEx: `.cfg Disney+`")
        if event.out: await event.delete()
        return

    search_term = args[1].strip()
    conf = await db.get_config_by_name(search_term)
    
    if not conf:
        msg = await event.reply(f"❌ Config not found for: `{search_term}`")
        if event.out: await event.delete()
        return

    # Lógica para convertir "captura1, captura 2, captura 3" en árbol
    raw_capture = conf.get('capture', 'None')
    capture_tree = ""
    if raw_capture and raw_capture != 'None':
        # Separamos por coma y limpiamos espacios
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

async def handler_setinfo(event):
    if not await can_run_command(event): return
    args = event.message.text.split(maxsplit=1)
    parts = [p.strip() for p in args[1].split('|')]
    if len(parts) == 5:
        await db.set_config_info(*parts)
        await event.edit("✅ Info updated.")

async def handler_cfgall(event):
    if not await can_run_command(event): return
    args = event.message.text.split()
    if len(args) < 2:
        await event.edit("❌ Use: `.cfgall <STATUS>`\nEx: `.cfgall check`")
        return
        
    status_key = args[1].lower()
    if status_key not in STATUS_MAP:
        await event.edit("❌ Invalid Status.")
        return
        
    new_emoji = STATUS_MAP[status_key]
    
    # Actualizamos todas las filas de la DB
    async with db.pool.acquire() as conn:
        await conn.execute("UPDATE configs SET status = $1", new_emoji)
        
    await event.edit(f"✅ All configs updated to {new_emoji}.")
    await sync_list_message(event)        