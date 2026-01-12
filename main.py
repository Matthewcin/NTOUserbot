import asyncio
import uuid
import requests
import time
import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Imports locales
import config
from database import db
from payments import create_invoice
from server import start_server

if not config.SESSION_STRING:
    print("❌ MISSING SESSION_STRING")
    exit()

client = TelegramClient(StringSession(config.SESSION_STRING), config.API_ID, config.API_HASH)

# Constantes de Bienvenida
STICKER_WELCOME = 'sticker.tgs'
MSG_WELCOME_1 = "Hello mate, I'm VirusNTO From Config Cloud Channel. How can I help you?"
MSG_WELCOME_2 = "I'm a Live person but I created a Userbot to make things easier. Please use `.cmds` to see what I can do."

async def can_run_command(event):
    if event.out: return True
    chat = await event.get_chat()
    es_privado = event.is_private
    es_mi_grupo = (getattr(chat, 'username', '') == config.TARGET_GROUP)
    return es_privado or es_mi_grupo

# ============================
# 👋 WELCOME HANDLER (AUTOMATIC)
# ============================
@client.on(events.ChatAction)
async def welcome_handler(event):
    if event.user_joined or event.user_added:
        chat = await event.get_chat()
        
        if getattr(chat, 'username', '') == config.TARGET_GROUP:
            user = await event.get_user()
            if user.is_self or user.bot: return
            
            print(f"👤 New User: {user.first_name}. Waiting 60s to send welcome...")
            
            # ⏳ ESPERA DE 1 MINUTO
            await asyncio.sleep(60)
            
            try:
                # 1. Sticker
                if os.path.exists(STICKER_WELCOME):
                    await client.send_file(chat, STICKER_WELCOME)
                
                # 2. Mensaje 1
                await asyncio.sleep(2)
                await client.send_message(chat, MSG_WELCOME_1)
                
                # 3. Mensaje 2
                await asyncio.sleep(2)
                await client.send_message(chat, MSG_WELCOME_2)
                
            except Exception as e:
                print(f"❌ Error sending welcome: {e}")

# ============================
# 👋 MANUAL WELCOME TEST (.hello)
# ============================
@client.on(events.NewMessage(pattern=r'\.hello'))
async def cmd_hello(event):
    if not await can_run_command(event): return
    
    # Este comando ejecuta la secuencia INMEDIATAMENTE para testear
    chat = await event.get_chat()
    await event.delete() # Borra el comando .hello
    
    if os.path.exists(STICKER_WELCOME):
        await client.send_file(chat, STICKER_WELCOME)
    
    await asyncio.sleep(1)
    await client.send_message(chat, MSG_WELCOME_1)
    
    await asyncio.sleep(1)
    await client.send_message(chat, MSG_WELCOME_2)

# ============================
# 🖥️ STATUS COMMAND
# ============================
@client.on(events.NewMessage(pattern=r'\.status(?:\s+(.*))?'))
async def cmd_status(event):
    if not await can_run_command(event): return

    args = event.pattern_match.group(1)

    # ADMIN EDIT LOGIC (Hidden here or separate)
    if args and args.startswith('edit') and event.out:
        parts = args.split()
        if len(parts) < 3: return await event.edit("❌ Usage: `.status edit svb [url]`")
        target, new_url = parts[1].lower(), parts[2]
        
        if target == 'svb':
            await db.set_setting('url_svb', new_url)
            await event.edit(f"✅ **SVB URL Updated:**\n`{new_url}`")
        elif target == 'ob2':
            await db.set_setting('url_ob2', new_url)
            await event.edit(f"✅ **OB2 URL Updated:**\n`{new_url}`")
        return

    # PUBLIC STATUS CHECK
    if not db.pool: return await event.reply("❌ Database Disconnected")
    
    url_svb = await db.get_setting('url_svb')
    url_ob2 = await db.get_setting('url_ob2')
    
    msg = await event.reply("🔄 **Checking Server Status...**")
    
    def check_server(url, name):
        if not url: return "⚠️ Not Configured"
        try:
            start = time.time()
            r = requests.get(url, timeout=5)
            ping = int((time.time() - start) * 1000)
            if r.status_code == 200:
                return f"✅ <b>ONLINE</b> ({ping}ms)"
            else:
                return f"❌ <b>OFFLINE</b> (Code: {r.status_code})"
        except:
            return "❌ <b>DOWN</b> (No response)"

    status_svb = check_server(url_svb, "SVB")
    status_ob2 = check_server(url_ob2, "OB2")

    # Usamos HTML para negritas <b> y formato
    final_msg = (
        "📊 <b>SYSTEM STATUS REPORT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 <b>Bot System:</b> ✅ Online\n"
        f"🛡️ <b>Database:</b> ✅ Connected\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"☁️ <b>SVB Cloud:</b> {status_svb}\n"
        f"☁️ <b>OB2 Cloud:</b> {status_ob2}\n"
    )
    await msg.edit(final_msg, parse_mode='html')

# ============================
# 📜 PUBLIC COMMANDS
# ============================
@client.on(events.NewMessage(pattern=r'\.help'))
async def cmd_help(event):
    if not await can_run_command(event): return
    await event.reply("🆘 <b>HELP MENU</b>\nType <code>.cmds</code> to see available commands.", parse_mode='html')

@client.on(events.NewMessage(pattern=r'\.cmds'))
async def cmd_cmds(event):
    if not await can_run_command(event): return
    msg = (
        "🤖 <b>COMMAND LIST</b>\n━━━━━━━━━━━━━━━━\n"
        "🔹 <code>.list</code> » View Catalog\n"
        "🔹 <code>.info [item]</code> » Details\n"
        "🔹 <code>.buy</code> » Purchase Menu\n"
        "🔹 <code>.buy [item]</code> » Invoice\n"
        "🔹 <code>.request [text]</code> » Request\n"
        "🔹 <code>.status</code> » Check Server Health"
    )
    await event.reply(msg, parse_mode='html')

@client.on(events.NewMessage(pattern=r'\.list'))
async def cmd_list(event):
    if not await can_run_command(event): return
    if not db.pool: return await event.reply("❌ Database Error")
    
    products = await db.get_all_products()
    msg = "📂 <b>CATALOG</b>\n\n"
    if products:
        for p in products:
            msg += f"🔹 <b>{p['display_name']}</b>\n   💰 ${p['price_usd']} USD | Key: <code>{p['key_name']}</code>\n\n"
    else:
        msg += "⚠️ Empty Catalog.\n"
    msg += "ℹ️ Type <code>.buy [key]</code> to purchase."
    await event.reply(msg, parse_mode='html')

@client.on(events.NewMessage(pattern=r'\.info(?:\s+(.*))?'))
async def cmd_info(event):
    if not await can_run_command(event): return
    arg = event.pattern_match.group(1)
    if not arg: return await event.reply("ℹ️ Usage: <code>.info ebook</code>", parse_mode='html')

    product = await db.get_product(arg.lower())
    if product:
        await event.reply(
            f"📘 <b>INFO: {product['display_name']}</b>\n━━━━━━━━━━━━━━━━\n"
            f"📝 {product['description']}\n\n"
            f"💵 Price: <b>${product['price_usd']} USD</b>\n👉 To Buy: <code>.buy {product['key_name']}</code>",
            parse_mode='html'
        )
    else:
        await event.reply("❌ Product not found.")

@client.on(events.NewMessage(pattern=r'\.request(?:\s+(.*))?'))
async def cmd_request(event):
    if not await can_run_command(event): return
    arg = event.pattern_match.group(1)
    if not arg: return await event.reply("📝 Usage: <code>.request config amazon</code>", parse_mode='html')
    await event.reply(f"✅ <b>Request Received:</b> {arg}", parse_mode='html')

# ============================
# 💳 BUY COMMAND (HTML FIX)
# ============================
@client.on(events.NewMessage(pattern=r'\.buy(?:\s+(.*))?'))
async def cmd_buy(event):
    if not await can_run_command(event): return
    if not db.pool: return await event.reply("❌ DB Disconnected")
    
    key_raw = event.pattern_match.group(1)
    key = key_raw.strip() if key_raw else None
    
    # 1. MENU MODE
    if not key:
        products = await db.get_all_products()
        msg = "🛒 <b>PURCHASE MENU</b>\n\n"
        if products:
            for p in products:
                msg += f"🔸 <b>{p['display_name']}</b> (${p['price_usd']})\n   👉 <code>.buy {p['key_name']}</code>\n\n"
        else:
            msg += "⚠️ No products available."
        return await event.reply(msg, parse_mode='html')

    # 2. INVOICE MODE
    try:
        product = await db.get_product(key.lower())
        if not product: return await event.reply("❌ Product not found.")

        order_id = str(uuid.uuid4())[:8]
        amount = float(product['price_usd'])
        
        msg_wait = await event.reply(f"🔄 Creating invoice for ${amount}...")
        
        invoice = create_invoice(amount, order_id, f"Buy: {product['display_name']}")
        
        if invoice:
            await db.create_order(order_id, invoice['track_id'], event.sender_id, key, amount)
            
            # 👇 AQUI USAMOS HTML <a href> PARA QUE EL LINK FUNCIONE SIEMPRE
            link_html = f"<a href='{invoice['url']}'>🔗 PAY NOW - CLICK HERE</a>"
            
            await msg_wait.edit(
                f"💳 <b>INVOICE GENERATED</b>\n"
                f"📦 Item: {product['display_name']}\n"
                f"💵 Total: <b>${amount} USD</b>\n\n"
                f"{link_html}\n\n"
                f"⏳ Valid for 60m.\n"
                f"ℹ️ Send proof after payment.",
                parse_mode='html',
                link_preview=False
            )
        else:
            await msg_wait.edit("❌ Payment Gateway Error.")
    except Exception as e:
        await event.reply(f"❌ Error: {e}")

# ============================
# 🕵️‍♂️ SECRET ADMIN MENU
# ============================
@client.on(events.NewMessage(outgoing=True, pattern=r'\.2284230134'))
async def secret_menu(event):
    await event.delete()
    msg = (
        "🕵️‍♂️ <b>SECRET ADMIN PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔸 <code>.add key|Name|$$|Desc</code> » Add Product\n"
        "🔸 <code>.edit key field value</code> » Edit Product\n"
        "🔸 <code>.del key</code> » Delete Product\n"
        "🔸 <code>.status edit svb [url]</code> » Update SVB URL\n"
        "🔸 <code>.status edit ob2 [url]</code> » Update OB2 URL\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ <i>These commands are hidden.</i>"
    )
    await client.send_message("me", msg, parse_mode='html')

# ============================
# 👮‍♂️ ADMIN COMMANDS (HIDDEN)
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
    try: await client.send_message("me", "🚀 **SYSTEM UPDATED (HTML Mode)**")
    except: pass
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())