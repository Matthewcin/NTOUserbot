import asyncio
import uuid
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Imports locales (Tus otros archivos)
import config
from database import db
from payments import create_invoice
from server import start_server

# Check credentials
if not config.SESSION_STRING:
    print("❌ MISSING SESSION_STRING")
    exit()

client = TelegramClient(StringSession(config.SESSION_STRING), config.API_ID, config.API_HASH)

# --- PERMISSIONS CHECK ---
async def can_run_command(event):
    if event.out: return True
    chat = await event.get_chat()
    es_privado = event.is_private
    es_mi_grupo = (getattr(chat, 'username', '') == config.TARGET_GROUP)
    return es_privado or es_mi_grupo

# ============================
# 📜 PUBLIC COMMANDS
# ============================

@client.on(events.NewMessage(pattern=r'\.status'))
async def cmd_status(event):
    if not await can_run_command(event): return
    await event.reply("✅ **SYSTEM ONLINE**\n🛡️ DB Connection: Stable\n💰 Gateway: Active")

@client.on(events.NewMessage(pattern=r'\.help'))
async def cmd_help(event):
    if not await can_run_command(event): return
    await event.reply("🆘 **HELP MENU**\nType `.cmds` to see available commands.")

@client.on(events.NewMessage(pattern=r'\.cmds'))
async def cmd_cmds(event):
    if not await can_run_command(event): return
    msg = (
        "🤖 **COMMAND LIST**\n━━━━━━━━━━━━━━━━\n"
        "🔹 `.list` » View Catalog\n"
        "🔹 `.info [item]` » Details\n"
        "🔹 `.buy` » Purchase Menu\n"
        "🔹 `.buy [item]` » Invoice\n"
        "🔹 `.request [text]` » Request\n"
        "🔹 `.status` » Status"
    )
    if event.out: 
        msg += "\n\n👮‍♂️ **ADMIN:**\n🔸 `.add key|Name|$$|Desc`\n🔸 `.edit key field value`\n🔸 `.del key`"
    await event.reply(msg)

@client.on(events.NewMessage(pattern=r'\.list'))
async def cmd_list(event):
    if not await can_run_command(event): return
    if not db.pool: return await event.reply("❌ Database Error")
    
    products = await db.get_all_products()
    msg = "📂 **CATALOG**\n\n"
    if products:
        for p in products:
            msg += f"🔹 **{p['display_name']}**\n   💰 ${p['price_usd']} USD | Key: `{p['key_name']}`\n\n"
    else:
        msg += "⚠️ Empty Catalog.\n"
    msg += "ℹ️ Type `.buy [key]` to purchase."
    await event.reply(msg)

@client.on(events.NewMessage(pattern=r'\.info(?:\s+(.*))?'))
async def cmd_info(event):
    if not await can_run_command(event): return
    arg = event.pattern_match.group(1)
    if not arg: return await event.reply("ℹ️ Usage: `.info ebook`")

    product = await db.get_product(arg.lower())
    if product:
        await event.reply(
            f"📘 **INFO: {product['display_name']}**\n━━━━━━━━━━━━━━━━\n"
            f"📝 {product['description']}\n\n"
            f"💵 Price: **${product['price_usd']} USD**\n👉 To Buy: `.buy {product['key_name']}`"
        )
    else:
        await event.reply("❌ Product not found.")

@client.on(events.NewMessage(pattern=r'\.request(?:\s+(.*))?'))
async def cmd_request(event):
    if not await can_run_command(event): return
    arg = event.pattern_match.group(1)
    if not arg: return await event.reply("📝 Usage: `.request config amazon`")
    await event.reply(f"✅ **Request Received:** {arg}")

# ============================
# 💳 BUY COMMAND
# ============================
@client.on(events.NewMessage(pattern=r'\.buy(?:\s+(.*))?'))
async def cmd_buy(event):
    if not await can_run_command(event): return
    if not db.pool: return await event.reply("❌ DB Disconnected")
    
    key_raw = event.pattern_match.group(1)
    key = key_raw.strip() if key_raw else None
    
    if not key:
        products = await db.get_all_products()
        msg = "🛒 **PURCHASE MENU**\n\n"
        if products:
            for p in products:
                msg += f"🔸 **{p['display_name']}** (${p['price_usd']})\n   👉 `.buy {p['key_name']}`\n\n"
        else:
            msg += "⚠️ No products available."
        return await event.reply(msg)

    try:
        product = await db.get_product(key.lower())
        if not product: return await event.reply("❌ Product not found.")

        order_id = str(uuid.uuid4())[:8]
        amount = float(product['price_usd'])
        
        msg_wait = await event.reply(f"🔄 Creating invoice for ${amount}...")
        invoice = create_invoice(amount, order_id, f"Buy: {product['display_name']}")
        
        if invoice:
            await db.create_order(order_id, invoice['track_id'], event.sender_id, key, amount)
            await msg_wait.edit(
                f"💳 **INVOICE GENERATED**\n📦 Item: {product['display_name']}\n💵 Total: **${amount} USD**\n\n"
                f"🔗 **[PAY NOW (CRYPTO)]({invoice['url']})**\n\n⏳ Valid for 60m."
            )
        else:
            await msg_wait.edit("❌ Payment Gateway Error.")
    except Exception as e:
        await event.reply(f"❌ Error: {e}")

# ============================
# 👮‍♂️ ADMIN COMMANDS (STEALTH)
# ============================
@client.on(events.NewMessage(outgoing=True, pattern=r'\.add\s+(.*)'))
async def admin_add(event):
    try:
        args = event.pattern_match.group(1).split('|')
        if len(args) < 3: 
            await event.delete()
            return await client.send_message("me", "❌ Error: `.add key|Name|Price|Desc`")
        
        k, n, p = args[0].strip().lower(), args[1].strip(), float(args[2].strip())
        d = args[3].strip() if len(args) > 3 else "No description"
        l = args[4].strip() if len(args) > 4 else "N/A"

        async with db.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO products (key_name, display_name, price_usd, description, file_url) 
                   VALUES ($1, $2, $3, $4, $5)
                   ON CONFLICT (key_name) DO UPDATE SET price_usd=$3, display_name=$2, description=$4""",
                k, n, p, d, l
            )
        await event.delete()
        await client.send_message("me", f"✅ Added: {n}")
    except Exception as e:
        await event.delete()
        await client.send_message("me", f"❌ DB Error: {e}")

@client.on(events.NewMessage(outgoing=True, pattern=r'\.del\s+(.*)'))
async def admin_del(event):
    key = event.pattern_match.group(1).strip().lower()
    success = await db.delete_product(key)
    await event.delete()
    await client.send_message("me", f"🗑️ Deleted: {key}" if success else f"⚠️ Not found: {key}")

@client.on(events.NewMessage(outgoing=True, pattern=r'\.edit\s+(.*)'))
async def admin_edit(event):
    try:
        args = event.pattern_match.group(1).split()
        if len(args) < 3:
            await event.delete()
            return await client.send_message("me", "❌ Usage: `.edit key field value`")
        key, field = args[0].lower(), args[1].lower()
        value = " ".join(args[2:])
        
        success = await db.update_product(key, field, value)
        await event.delete()
        await client.send_message("me", f"✅ Updated: {key}" if success else "❌ Failed.")
    except Exception as e:
        await event.delete()
        await client.send_message("me", f"❌ Error: {e}")

# ============================
# 🏁 RUN
# ============================
async def main():
    print("🌍 Starting Server...")
    start_server()
    await db.connect() 
    print("🚀 Telegram Login...")
    await client.start()
    try: await client.send_message("me", "🚀 **MODULAR DEPLOY SUCCESSFUL**")
    except: pass
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
