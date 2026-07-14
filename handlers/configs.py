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
    
    text = "🌐 **CONFIG CLOUD STATUS**\n\n"
    
    for cat in order:
        if cat in grouped:
            text += f"📂 **{cat}**\n"
            for item in grouped[cat]:
                price_tag = f" - {item['price']}" if item['price'] else ""
                text += f"{item['status']} {item['name']}{price_tag}\n"
            text += "\n"
            
    for cat in grouped:
        if cat not in order:
            text += f"📂 **{cat}**\n"
            for item in grouped[cat]:
                price_tag = f" - {item['price']}" if item['price'] else ""
                text += f"{item['status']} {item['name']}{price_tag}\n"
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

async def handler_addcfg(event):
    if not await can_run_command(event): return
    args = event.message.text.split(maxsplit=2)
    if len(args) < 3:
        await event.edit("❌ Use: `.addcfg <GROUP> <NAME> [PRICE]`\nEx: `.addcfg STREAMING Disney+`")
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
        await event.edit(f"✅ Added **{name}** to **{category}**.")
        await sync_list_message(event)
    else:
        await event.edit(f"❌ Error.")

async def handler_delcfg(event):
    if not await can_run_command(event): return
    args = event.message.text.split(maxsplit=2)
    if len(args) < 3:
        await event.edit("❌ Use: `.delcfg <GROUP> <NAME>`")
        return

    category = args[1]
    name = args[2]

    if await db.del_config(category, name):
        await event.edit(f"🗑 Deleted **{name}** from **{category}**.")
        await sync_list_message(event)
    else:
        await event.edit(f"❌ Config not found.")

async def handler_cfgstatus(event):
    if not await can_run_command(event): return
    args = event.message.text.split()
    if len(args) < 4:
        await event.edit("❌ Use: `.cfgstatus <GROUP> <NAME> <STATUS>`")
        return

    category = args[1]
    status_key = args[-1].lower()
    name = " ".join(args[2:-1]) 

    if status_key not in STATUS_MAP:
        await event.edit("❌ Invalid Status.")
        return

    new_emoji = STATUS_MAP[status_key]

    if await db.update_config_status(category, name, new_emoji):
        await event.edit(f"✅ Status updated.")
        await sync_list_message(event)
    else:
        await event.edit(f"❌ Config not found.")

async def handler_editcfg(event):
    if not await can_run_command(event): return
    args = event.message.text.split()
    if len(args) < 4:
        await event.edit("❌ Use: `.editcfg <GROUP> <NAME> <PRICE>`")
        return

    category = args[1]
    price = args[-1]
    name = " ".join(args[2:-1])

    if await db.update_config_price(category, name, price):
        await event.edit(f"✅ Price updated.")
        await sync_list_message(event)
    else:
        await event.edit(f"❌ Config not found.")

    async def handler_cfg_info(event):
        if not await can_run_command(event): return
    
    args = event.message.text.split(maxsplit=1)
    if len(args) < 2:
        msg = await event.reply("❌ **Usage:** `.cfg [Config Name]`\nEx: `.cfg Disney+`")
        if event.out: await event.delete()
        return

    search_term = args[1].strip()
    
    # Buscamos la config en la base de datos
    conf = await db.get_config_by_name(search_term)
    
    if not conf:
        msg = await event.reply(f"❌ Config not found for: `{search_term}`")
        if event.out: await event.delete()
        return

    # Formatear las fechas para que se vean limpias (YYYY-MM-DD)
    updated_str = conf['updated_at'].strftime("%Y-%m-%d") if conf.get('updated_at') else "Unknown"

    # Construir el mensaje
    msg = (
        f"⚙️ **CONFIG INFORMATION**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ **Name:** `{conf['name']}`\n"
        f"📂 **Category:** {conf['category']}\n"
        f"📊 **Status:** {conf['status']}\n"
        f"🛒 **Price:** {conf['price'] if conf['price'] else 'Free/Included'}\n\n"
        f"📑 **Capture:** {conf.get('capture', 'None')}\n"
        f"🔒 **Requires TLS:** {conf.get('requires_tls', 'No')}\n"
        f"📜 **Login Rules:** {conf.get('login_rules', 'None')}\n"
        f"🌐 **Proxies Admitted:** {conf.get('proxies_admitted', 'Any')}\n\n"
        f"📅 **Latest Update:** {updated_str}\n"
    )

    if event.out:
        await event.edit(msg)
    else:
        await event.reply(msg)