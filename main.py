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
    print("CRITICAL: MISSING SESSION_STRING")
    exit()

client = TelegramClient(StringSession(config.SESSION_STRING), config.API_ID, config.API_HASH)

# ============================
# ⚙️ CONFIGURACIÓN
# ============================
STICKER_FILENAME = 'sticker.tgs'
MSG_WELCOME_1 = "Hello mate, I'm VirusNTO From Config Cloud Channel. How can I help you?"
MSG_WELCOME_2 = "I'm a Live person but I created a Userbot to make things easier. Please use .cmds to see what I can do."

async def can_run_command(event):
    if event.out: return True
    chat = await event.get_chat()
    es_privado = event.is_private
    es_mi_grupo = (getattr(chat, 'username', '') == config.TARGET_GROUP)
    return es_privado or es_mi_grupo

# ============================
# 🔌 DATABASE INTERNA
# ============================
import asyncpg
class DatabaseInternal:
    def __init__(self, db_url):
        self.db_url = db_url
        self.pool = None

    async def connect(self):
        if not self.pool:
            try:
                url_clean = self.db_url.split('?')[0]
                self.pool = await asyncpg.create_pool(url_clean, ssl='require')
                await self.init_tables()
            except Exception as e:
                print(f"DB ERROR: {e}")

    async def init_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    key_name TEXT UNIQUE NOT NULL,
                    display_name TEXT NOT NULL,
                    price_usd NUMERIC(10, 2) NOT NULL,
                    description TEXT,
                    file_url TEXT
                );
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    oxapay_track_id TEXT, 
                    user_id BIGINT,
                    product_key TEXT,
                    amount_usd NUMERIC(10, 2),
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key_name TEXT PRIMARY KEY,
                    value TEXT
                );
            """)

    async def get_product(self, key):
        if not self.pool: return None
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM products WHERE key_name = $1", key)

    async def get_all_products(self):
        if not self.pool: return []
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT * FROM products")

    async def create_order(self, order_id, track_id, user_id, product_key, amount):
        if not self.pool: return
        track_id_str = str(track_id)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO orders (order_id, oxapay_track_id, user_id, product_key, amount_usd) 
                   VALUES ($1, $2, $3, $4, $5)""",
                order_id, track_id_str, user_id, product_key, amount
            )

    async def update_product(self, key, field, value):
        if not self.pool: return False
        valid_fields = {'price': 'price_usd', 'name': 'display_name', 'desc': 'description', 'link': 'file_url'}
        if field not in valid_fields: return False
        column = valid_fields[field]
        if field == 'price':
            try: value = float(value)
            except: return False
        async with self.pool.acquire() as conn:
            query = f"UPDATE products SET {column} = $1 WHERE key_name = $2"
            res = await conn.execute(query, value, key)
            return res != "UPDATE 0"

    async def delete_product(self, key):
        if not self.pool: return False
        async with self.pool.acquire() as conn:
            res = await conn.execute("DELETE FROM products WHERE key_name = $1", key)
            return res != "DELETE 0"

    async def get_setting(self, key):
        if not self.pool: return None
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT value FROM settings WHERE key_name = $1", key)
            return row['value'] if row else None

    async def set_setting(self, key, value):
        if not self.pool: return False
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO settings (key_name, value) VALUES ($1, $2)
                ON CONFLICT (key_name) DO UPDATE SET value = $2
            """, key, value)
            return True

db = DatabaseInternal(config.DB_URL)

# ============================
# 👋 WELCOME LOGIC
# ============================
async def send_welcome_sequence(chat):
    try:
        if os.path.exists(STICKER_FILENAME):
            await client.send_file(chat, STICKER_FILENAME)
        else:
            print(f"⚠️ Warning: {STICKER_FILENAME} not found.")

        await asyncio.sleep(1)
        await client.send_message(chat, MSG_WELCOME_1)
        
        await asyncio.sleep(1)
        await client.send_message(chat, MSG_WELCOME_2)
    except Exception as e:
        print(f"Error sending welcome: {e}")

@client.on(events.ChatAction)
async def welcome_handler(event):
    if event.user_joined or event.user_added:
        chat = await event.get_chat()
        if getattr(chat, 'username', '') == config.TARGET_GROUP:
            user = await event.get_user()
            if user.is_self or user.bot: return
            
            print(f"New User: {user.first_name}. Waiting 60s...")
            await asyncio.sleep(60) 
            await send_welcome_sequence(chat)

@client.on(events.NewMessage(pattern=r'\.hello'))
async def cmd_hello(event):
    if not await can_run_command(event): return
    await event.delete()
    await send_welcome_sequence(await event.get_chat())

# ============================
# 🛠️ URL DEBUG COMMAND (NUEVO)
# ============================
@client.on(events.NewMessage(pattern=r'\.urldebug(?:\s+(.*))?'))
async def cmd_urldebug(event):
    if not await can_run_command(event): return
    
    url = event.pattern_match.group(1)
    if not url:
        return await event.reply("❌ Usage: `.urldebug https://google.com`")
        
    await event.reply("🔍 **TESTING URL FORMATS**")
    
    # Test 1: Raw
    await event.reply(f"1. RAW: {url}")
    
    # Test 2: Markdown
    try:
        await event.reply(f"2. MARKDOWN: [Click Here]({url})", parse_mode='md')
    except Exception as e:
        await event.reply(f"2. MARKDOWN ERROR: {e}")
        
    # Test 3: HTML
    try:
        await event.reply(f"3. HTML: <a href='{url}'>Click Here</a>", parse_mode='html')
    except Exception as e:
        await event.reply(f"3. HTML ERROR: {e}")

# ============================
# 🖥️ STATUS COMMAND (UPDATED LOGIC)
# ============================
@client.on(events.NewMessage(pattern=r'\.status(?:\s+(.*))?'))
async def cmd_status(event):
    if not await can_run_command(event): return
    args = event.pattern_match.group(1)

    # 1. ADMIN EDIT
    if args and args.startswith('edit') and event.out:
        parts = args.split()
        if len(parts) < 3: return await event.edit("Usage: .status edit svb [url]")
        target, new_url = parts[1].lower(), parts[2]
        
        if target == 'svb':
            await db.set_setting('url_svb', new_url)
            await event.edit(f"SVB URL Updated:\n`{new_url}`")
        elif target == 'ob2':
            await db.set_setting('url_ob2', new_url)
            await event.edit(f"OB2 URL Updated:\n`{new_url}`")
        return

    # 2. CHECK DEBUG
    if args and args.startswith('check'):
        parts = args.split()
        if len(parts) < 2: return await event.reply("Usage: <code>.status check svb</code>", parse_mode='html')
        target = parts[1].lower()
        key = 'url_svb' if target == 'svb' else 'url_ob2' if target == 'ob2' else None
        
        if not key: return await event.reply("Invalid target.")
        url = await db.get_setting(key)
        if not url: return await event.reply(f"⚠️ {target.upper()} URL not configured.")
        
        msg = await event.reply(f"🔍 Checking {target.upper()}...")
        try:
            r = requests.get(url, timeout=5)
            code = r.status_code
            # Aceptamos 200 o 401 como online
            status_text = "ONLINE" if code in [200, 401] else "ISSUES"
        except:
            code = "UNREACHABLE"
            status_text = "DOWN"

        response = (
            f"🔎 <b>DEBUG CHECK: {target.upper()}</b>\n"
            f"🔗 <b>URL:</b> <code>{url}</code>\n"
            f"📡 <b>Response Code:</b> <code>{code}</code>\n"
            f"📊 <b>Status:</b> {status_text}"
        )
        await msg.edit(response, parse_mode='html')
        return

    # 3. PUBLIC STATUS (UPDATED WITH 401 VALIDATION)
    if not db.pool: return await event.reply("Database Disconnected")
    
    url_svb = await db.get_setting('url_svb')
    url_ob2 = await db.get_setting('url_ob2')
    
    msg = await event.reply("Checking Server Status...")
    
    def check_server(url):
        if not url: return "Not Configured"
        try:
            start = time.time()
            r = requests.get(url, timeout=5)
            ping = int((time.time() - start) * 1000)
            
            # 👇 LÓGICA ACTUALIZADA: 200 O 401 ES VALIDO
            if r.status_code in [200, 401]:
                return f"✅ <b>ONLINE</b> ({ping}ms)"
            else:
                return f"❌ <b>OFFLINE</b> (Code: {r.status_code})"
        except:
            return "❌ <b>DOWN</b>"

    status_svb = check_server(url_svb)
    status_ob2 = check_server(url_ob2)

    final_msg = (
        "📊 <b>SYSTEM STATUS</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"🤖 <b>Bot System:</b> ✅ Online\n"
        f"🛡️ <b>Database:</b> ✅ Connected\n"
        "━━━━━━━━━━━━━━━━\n"
        f"☁️ <b>SVB Cloud:</b> {status_svb}\n"
        f"☁️ <b>OB2 Cloud:</b> {status_ob2}\n"
    )
    await msg.edit(final_msg, parse_mode='html')

# ============================
# 📜 MAIN COMMANDS
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
        "🔹 <code>.status</code> » Server Health"
    )
    await event.reply(msg, parse_mode='html')

@client.on(events.NewMessage(pattern=r'\.list'))
async def cmd_list(event):
    if not await can_run_command(event): return
    if not db.pool: return await event.reply("Database Error")
    
    products = await db.get_all_products()
    msg = "📂 <b>CATALOG</b>\n\n"
    if products:
        for p in products:
            msg += f"🔹 <b>{p['display_name']}</b>\n   💰 ${p['price_usd']} USD | Key: <code>{p['key_name']}</code>\n\n"
    else:
        msg += "Catalog empty.\n"
    msg += "Type <code>.buy [key]</code> to purchase."
    await event.reply(msg, parse_mode='html')

@client.on(events.NewMessage(pattern=r'\.info(?:\s+(.*))?'))
async def cmd_info(event):
    if not await can_run_command(event): return
    arg = event.pattern_match.group(1)
    if not arg: return await event.reply("Usage: <code>.info ebook</code>", parse_mode='html')

    product = await db.get_product(arg.lower())
    if product:
        await event.reply(
            f"📘 <b>INFO: {product['display_name']}</b>\n━━━━━━━━━━━━━━━━\n"
            f"📝 {product['description']}\n\n"
            f"💵 Price: <b>${product['price_usd']} USD</b>\n👉 To Buy: <code>.buy {product['key_name']}</code>",
            parse_mode='html'
        )
    else:
        await event.reply("Product not found.")

@client.on(events.NewMessage(pattern=r'\.request(?:\s+(.*))?'))
async def cmd_request(event):
    if not await can_run_command(event): return
    arg = event.pattern_match.group(1)
    if not arg: return await event.reply("Usage: .request config amazon")
    await event.reply(f"Request received: {arg}")

# ============================
# 💳 BUY COMMAND (LOGGING ADDED)
# ============================
@client.on(events.NewMessage(pattern=r'\.buy(?:\s+(.*))?'))
async def cmd_buy(event):
    if not await can_run_command(event): return
    if not db.pool: return await event.reply("DB Disconnected")
    
    key_raw = event.pattern_match.group(1)
    key = key_raw.strip() if key_raw else None
    
    if not key:
        products = await db.get_all_products()
        msg = "🛒 <b>PURCHASE MENU</b>\n\n"
        if products:
            for p in products:
                msg += f"🔸 <b>{p['display_name']}</b> (${p['price_usd']})\n   👉 <code>.buy {p['key_name']}</code>\n\n"
        else:
            msg += "No products available."
        return await event.reply(msg, parse_mode='html')

    try:
        product = await db.get_product(key.lower())
        if not product: return await event.reply("Product not found.")

        order_id = str(uuid.uuid4())[:8]
        amount = float(product['price_usd'])
        
        msg_wait = await event.reply(f"Creating invoice for ${amount}...")
        
        invoice = create_invoice(amount, order_id, f"Buy: {product['display_name']}")
        print(f"DEBUG INVOICE: {invoice}") # MIRA ESTO EN RENDER LOGS
        
        if invoice and invoice.get('url'):
            await db.create_order(order_id, invoice['track_id'], event.sender_id, key, amount)
            
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
            await msg_wait.edit("❌ Payment Gateway Error (Check Logs).")
    except Exception as e:
        import traceback
        traceback.print_exc()
        await event.reply(f"System Error: {e}")

# ============================
# 🕵️‍♂️ SECRET ADMIN MENU
# ============================
@client.on(events.NewMessage(outgoing=True, pattern=r'\.2284230134'))
async def secret_menu(event):
    await event.delete()
    msg = (
        "🕵️‍♂️ <b>SECRET ADMIN PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔸 <code>.add key|Name|$$|Desc</code> » Add\n"
        "🔸 <code>.edit key field value</code> » Edit\n"
        "🔸 <code>.del key</code> » Delete\n"
        "🔸 <code>.status edit svb [url]</code> » SVB Url\n"
        "🔸 <code>.status edit ob2 [url]</code> » OB2 Url\n"
        "🔸 <code>.status check svb</code> » Debug SVB\n"
        "🔸 <code>.urldebug [url]</code> » Debug Links\n"
    )
    await client.send_message("me", msg, parse_mode='html')

# ============================
# 👮‍♂️ ADMIN COMMANDS
# ============================
@client.on(events.NewMessage(outgoing=True, pattern=r'\.add\s+(.*)'))
async def admin_add(event):
    try:
        args = event.pattern_match.group(1).split('|')
        if len(args) < 3: 
            await event.delete()
            return await client.send_message("me", "Error: .add key|Name|Price|Desc")
        
        k, n, p = args[0].strip().lower(), args[1].strip(), float(args[2].strip())
        d = args[3].strip() if len(args) > 3 else "No description"
        l = args[4].strip() if len(args) > 4 else "N/A"

        async with db.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO products (key_name, display_name, price_usd, description, file_url) 
                   VALUES ($1, $2, $3, $4, $5)""",
                k, n, p, d, l
            )
        await event.delete()
        await client.send_message("me", f"Added: {n}")
    except Exception as e:
        await event.delete()
        await client.send_message("me", f"DB Error: {e}")

@client.on(events.NewMessage(outgoing=True, pattern=r'\.del\s+(.*)'))
async def admin_del(event):
    key = event.pattern_match.group(1).strip().lower()
    success = await db.delete_product(key)
    await event.delete()
    await client.send_message("me", f"Deleted: {key}" if success else f"Not found: {key}")

@client.on(events.NewMessage(outgoing=True, pattern=r'\.edit\s+(.*)'))
async def admin_edit(event):
    try:
        args = event.pattern_match.group(1).split()
        if len(args) < 3:
            await event.delete()
            return await client.send_message("me", "Usage: .edit key field value")
        key, field = args[0].lower(), args[1].lower()
        value = " ".join(args[2:])
        success = await db.update_product(key, field, value)
        await event.delete()
        await client.send_message("me", f"Updated: {key}" if success else "Failed.")
    except Exception as e:
        await event.delete()
        await client.send_message("me", f"Error: {e}")

# ============================
# 🏁 RUN
# ============================
async def main():
    print("🌍 Starting Server...")
    start_server()
    await db.connect() 
    print("🚀 Telegram Login...")
    await client.start()
    try: await client.send_message("me", "System Online (v8.0)")
    except: pass
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())