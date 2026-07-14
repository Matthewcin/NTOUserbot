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
    if len(args) < 2: return
    conf = await db.get_config_by_name(args[1].strip())
    if not conf: return
    updated_str = conf['updated_at'].strftime("%Y-%m-%d") if conf.get('updated_at') else "Unknown"
    msg = (f"⚙️ **CONFIG INFO**\n🏷️ **Name:** `{conf['name']}`\n📊 **Status:** {conf['status']}\n\n"
           f"📑 **Capture:** {conf.get('capture', 'None')}\n🔒 **TLS:** {conf.get('requires_tls', 'No')}\n"
           f"🌐 **Proxies:** {conf.get('proxies_admitted', 'Any')}\n📅 **Update:** {updated_str}")
    await event.reply(msg)

async def handler_setinfo(event):
    if not await can_run_command(event): return
    args = event.message.text.split(maxsplit=1)
    parts = [p.strip() for p in args[1].split('|')]
    if len(parts) == 5:
        await db.set_config_info(*parts)
        await event.edit("✅ Info updated.")