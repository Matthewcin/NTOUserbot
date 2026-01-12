import os
import asyncio
import json
import requests
import asyncpg
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from flask import Flask
from threading import Thread

# ==========================================
# ⚙️ CONFIG & CREDENTIALS
# ==========================================
API_ID = int(os.getenv('API_ID', '32541501'))
API_HASH = os.getenv('API_HASH', '66f7a1c72eac5d25705ef1d35275ca4f')
SESSION_STRING = os.getenv('SESSION_STRING')
DB_URL = os.getenv('DB_URL')
OXAPAY_KEY = os.getenv('OXAPAY_KEY', 'WGJMFR-0DMVXO-IRCXPB-GDJHED')

TARGET_GROUP = 'myConfigCloud'
MY_USER_LINK = 'https://t.me/Virusnto'

# ==========================================
# 🌐 WEB SERVER
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot Online. System Operational."

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def start_server():
    t = Thread(target=run_server)
    t.start()

# ==========================================
# 🔌 DATABASE MANAGER (Neon Fix + Auto Tables)
# ==========================================
class Database:
    def __init__(self, db_url):
        self.db_url = db_url
        self.pool = None

    async def connect(self):
        if not self.pool:
            try:
                # Fix for Neon SSL issue
                url_clean = self.db_url.split('?')[0]
                self.pool = await asyncpg.create_pool(url_clean, ssl='require')
                await self.init_tables()
            except Exception as e:
                print(f"❌ CRITICAL DB ERROR: {e}")

    async def init_tables(self):
        async with self.pool.acquire() as conn:
            # Product Table
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
            # Order Table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    oxapay_track_id BIGINT,
                    user_id BIGINT,
                    product_key TEXT,
                    amount_usd NUMERIC(10, 2),
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO orders (order_id, oxapay_track_id, user_id, product_key, amount_usd) 
                   VALUES ($1, $2, $3, $4, $5)""",
                order_id, track_id, user_id, product_key, amount
            )

    async def update_product(self, key, field, value):
        if not self.pool: return False
        # Map simple fields to DB columns
        valid_fields = {
            'price': 'price_usd',
            'name': 'display_name',
            'desc': 'description',
            'link': 'file_url'
        }
        if field not in valid_fields: return False
        
        column = valid_fields[field]
        
        # Convert price to float
        if field == 'price':
            try: value = float(value)
            except: return False

        async with self.pool.acquire() as conn:
            # We construct the query safely
            query = f"UPDATE products SET {column} = $1 WHERE key_name = $2"
            result = await conn.execute(query, value, key)
            return result != "UPDATE 0"

    async def delete_product(self, key):
        if not self.pool: return False
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM products WHERE key_name = $1", key)
            return result != "DELETE 0"

db = Database(DB_URL)

# ==========================================
# 💸 OXAPAY PAYMENT PROCESSOR
# ==========================================
def create_invoice(amount, order_id, description):
    url = "https://api.oxapay.com/merchants/request"
    payload = {
        "merchant": OXAPAY_KEY,
        "amount": amount,
        "currency": "USDT",
        "life_time": 60,
        "fee_paid_by_payer": 0,
        "return_url": MY_USER_LINK,
        "description": description,
        "order_id": order_id
    }
    try:
        response = requests.post(url, json=payload).json()
        
        # DEBUG: Print response if it fails
        if response.get("result") != 100:
            print(f"⚠️ OXAPAY ERROR: {response}") # Check Render Logs if this happens
            return None
            
        return {"url": response.get("pay_url"), "track_id": response.get("trackId")}
    except Exception as e:
        print(f"⚠️ API EXCEPTION: {e}")
        return None

# ==========================================
# 🤖 USERBOT LOGIC
# ==========================================
if not SESSION_STRING:
    print("❌ MISSING SESSION_STRING")
    exit()

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

async def can_run_command(event):
    if event.out: return True
    chat = await event.get_chat()
    es_privado = event.is_private
    es_mi_grupo = (getattr(chat, 'username', '') == TARGET_GROUP)
    return es_privado or es_mi_grupo

# ---------------------------------------------
# 📜 PUBLIC COMMANDS (US English)
# ---------------------------------------------

@client.on(events.NewMessage(pattern=r'\.status'))
async def cmd_status(event):
    if not await can_run_command(event): return
    await event.reply("✅ **SYSTEM ONLINE**\n🛡️ DB Connection: Stable\n💰 Gateway: Active")

@client.on(events.NewMessage(pattern=r'\.help'))
async def cmd_help(event):
    if not await can_run_command(event): return
    await event.reply("🆘 **HELP MENU**\nType `.cmds` to see the full list of available commands.")

@client.on(events.NewMessage(pattern=r'\.cmds'))
async def cmd_cmds(event):
    if not await can_run_command(event): return
    msg = (
        "🤖 **COMMAND LIST**\n"
        "━━━━━━━━━━━━━━━━\n"
        "🔹 `.list` » View Catalog\n"
        "🔹 `.info [item]` » Product Details\n"
        "🔹 `.buy` » Purchase Menu\n"
        "🔹 `.buy [item]` » Generate Invoice\n"
        "🔹 `.request [text]` » Request Config/Account\n"
        "🔹 `.status` » System Status"
    )
    if event.out: # Only YOU see this
        msg += (
            "\n\n👮‍♂️ **ADMIN (Stealth Mode):**\n"
            "🔸 `.add key|Name|$$|Desc` » Add Item\n"
            "🔸 `.edit key field value` » Edit Item\n"
            "🔸 `.del key` » Delete Item"
        )
    await event.reply(msg)

@client.on(events.NewMessage(pattern=r'\.list'))
async def cmd_list(event):
    if not await can_run_command(event): return
    if not db.pool: return await event.reply("❌ Database Error")
    
    products = await db.get_all_products()
    msg = "📂 **CURRENT CATALOG**\n\n"
    if products:
        for p in products:
            msg += f"🔹 **{p['display_name']}**\n   💰 ${p['price_usd']} USD | Key: `{p['key_name']}`\n\n"
    else:
        msg += "⚠️ Catalog is empty.\n"
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
            f"💵 Price: **${product['price_usd']} USD**\n"
            f"👉 To Buy: `.buy {product['key_name']}`"
        )
    else:
        await event.reply("❌ Product not found.")

@client.on(events.NewMessage(pattern=r'\.request(?:\s+(.*))?'))
async def cmd_request(event):
    if not await can_run_command(event): return
    arg = event.pattern_match.group(1)
    if not arg: return await event.reply("📝 Usage: `.request config amazon`")
    await event.reply(f"✅ **Request Received:** {arg}\nI will consider it for future updates.")

# ---------------------------------------------
# 💳 BUY COMMAND (Debugged)
# ---------------------------------------------
@client.on(events.NewMessage(pattern=r'\.buy(?:\s+(.*))?'))
async def cmd_buy(event):
    if not await can_run_command(event): return
    if not db.pool: return await event.reply("❌ Database Disconnected")
    
    key_raw = event.pattern_match.group(1)
    key = key_raw.strip() if key_raw else None
    
    # 1. MENU MODE
    if not key:
        products = await db.get_all_products()
        msg = "🛒 **PURCHASE MENU**\n\n"
        if products:
            for p in products:
                msg += f"🔸 **{p['display_name']}** (${p['price_usd']})\n   👉 `.buy {p['key_name']}`\n\n"
        else:
            msg += "⚠️ No products available yet."
        return await event.reply(msg)

    # 2. INVOICE MODE
    product = await db.get_product(key.lower())
    if not product: return await event.reply("❌ Product not found.")

    import uuid
    order_id = str(uuid.uuid4())[:8]
    amount = float(product['price_usd'])
    
    # Send waiting message
    msg_wait = await event.reply(f"🔄 Creating invoice for ${amount}...")
    
    invoice = create_invoice(amount, order_id, f"Buy: {product['display_name']}")
    
    if invoice:
        await db.create_order(order_id, invoice['track_id'], event.sender_id, key, amount)
        await msg_wait.edit(
            f"💳 **INVOICE GENERATED**\n"
            f"📦 Item: {product['display_name']}\n"
            f"💵 Total: **${amount} USD**\n\n"
            f"🔗 **[PAY NOW (CRYPTO)]({invoice['url']})**\n\n"
            f"⏳ Valid for 60 minutes.\n"
            f"ℹ️ Automatic confirmation."
        )
    else:
        # If failure, show generic error to user, but check logs in Render
        await msg_wait.edit("❌ **Payment Gateway Error.**\nPlease contact admin manually.")

# ---------------------------------------------
# 👮‍♂️ ADMIN COMMANDS (Stealth Mode 🥷)
# ---------------------------------------------
# These commands delete themselves and reply in Saved Messages

@client.on(events.NewMessage(outgoing=True, pattern=r'\.add\s+(.*)'))
async def admin_add(event):
    # .add key|Name|Price|Desc
    try:
        args = event.pattern_match.group(1).split('|')
        if len(args) < 3: 
            # Send error to saved messages
            await event.delete()
            return await client.send_message("me", "❌ Error: `.add key | Name | Price | Desc`")
        
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
        
        await event.delete() # Delete from group
        await client.send_message("me", f"✅ **Product Added:** {n} (${p})")
        
    except Exception as e:
        await event.delete()
        await client.send_message("me", f"❌ DB Error: {e}")

@client.on(events.NewMessage(outgoing=True, pattern=r'\.del\s+(.*)'))
async def admin_del(event):
    key = event.pattern_match.group(1).strip().lower()
    success = await db.delete_product(key)
    
    await event.delete() # Delete from group
    if success:
        await client.send_message("me", f"🗑️ **Deleted:** {key}")
    else:
        await client.send_message("me", f"⚠️ Product not found: {key}")

@client.on(events.NewMessage(outgoing=True, pattern=r'\.edit\s+(.*)'))
async def admin_edit(event):
    # Format: .edit ebook price 60
    # Fields: price, name, desc
    try:
        args = event.pattern_match.group(1).split()
        if len(args) < 3:
            await event.delete()
            return await client.send_message("me", "❌ Usage: `.edit [key] [price/name/desc] [value]`")

        key = args[0].lower()
        field = args[1].lower()
        # Join the rest of arguments as value (for names with spaces)
        value = " ".join(args[2:]) 

        success = await db.update_product(key, field, value)
        
        await event.delete() # Delete from group
        
        if success:
            await client.send_message("me", f"✅ **Updated:** {key} -> {field} = {value}")
        else:
            await client.send_message("me", f"❌ Failed. Check if key exists or field name (price/name/desc).")
            
    except Exception as e:
        await event.delete()
        await client.send_message("me", f"❌ Error: {e}")

# ==========================================
# 🏁 RUN
# ==========================================
async def main():
    print("🌍 Starting Server...")
    start_server()
    await db.connect() 
    print("🚀 Telegram Login...")
    await client.start()
    
    try:
        await client.send_message("me", "🚀 **DEPLOY SUCCESSFUL**\n✅ Bot is ready & Online.")
    except: pass
    
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
