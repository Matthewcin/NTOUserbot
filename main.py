import os
import asyncio
import logging
import asyncpg
import requests
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from keep_alive import start_server

# ==========================================
# ⚙️ CONFIGURATION & SECRETS
# ==========================================
# Telegram Config
API_ID = int(os.getenv('API_ID', '32541501'))
API_HASH = os.getenv('API_HASH', '66f7a1c72eac5d25705ef1d35275ca4f')
SESSION_STRING = os.getenv('SESSION_STRING')

# Database Config (Neon.tech)
DB_URL = os.getenv('DB_URL') 
# Put your full postgres url in Render Environment Variables! 
# Example: postgresql://neondb_owner:npg_Nd2D8...@ep-flat...aws.neon.tech/neondb?sslmode=require

# Payment Config (Oxapay - Sign up at oxapay.com to get a Key)
# It is the best low-fee (0.4%) option for Telegram.
OXAPAY_KEY = os.getenv('OXAPAY_KEY', 'Paste_Your_Oxapay_Merchant_Key_Here')

# Bot Config
TARGET_GROUP = 'myConfigCloud'
MY_USER_LINK = 'https://t.me/Virusnto'
OWNER_ID = 934491540 # Replace with your numeric ID

# ==========================================
# 🔌 DATABASE MANAGER
# ==========================================
class Database:
    def __init__(self, db_url):
        self.db_url = db_url
        self.pool = None

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.db_url)
            print("✅ Connected to Neon Database")

    async def get_product(self, key):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM products WHERE key_name = $1", key)

    async def create_order(self, order_id, user_id, product_key, amount):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO orders (order_id, user_id, product_key, amount_usd) VALUES ($1, $2, $3, $4)",
                order_id, user_id, product_key, amount
            )

    async def get_all_products(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT * FROM products")

db = Database(DB_URL)

# ==========================================
# 🚀 INITIALIZATION
# ==========================================
if not SESSION_STRING:
    print("❌ Error: SESSION_STRING missing.")
    exit()

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==========================================
# 💸 PAYMENT LOGIC (Oxapay)
# ==========================================
def create_crypto_payment(amount, order_id, email="customer@mail.com"):
    """Creates a payment link via Oxapay"""
    url = "https://api.oxapay.com/merchants/request"
    data = {
        "merchant": OXAPAY_KEY,
        "amount": amount,
        "currency": "USDT", # You can change to LTC, BTC, etc.
        "life_time": 60, # 60 minutes to pay
        "fee_paid_by_payer": 0,
        "return_url": "https://t.me/Virusnto",
        "description": f"Order {order_id}",
        "order_id": order_id
    }
    try:
        response = requests.post(url, json=data).json()
        if response.get("result") == 100:
            return response.get("pay_url")
        else:
            print(f"Payment Error: {response}")
            return None
    except Exception as e:
        print(f"API Error: {e}")
        return None

# ==========================================
# 🤖 COMMANDS
# ==========================================

async def can_run_command(event):
    if event.out: return True
    chat = await event.get_chat()
    es_privado = event.is_private
    es_mi_grupo = (getattr(chat, 'username', '') == TARGET_GROUP)
    return es_privado or es_mi_grupo

@client.on(events.NewMessage(pattern=r'\.list'))
async def cmd_list(event):
    if not await can_run_command(event): return

    products = await db.get_all_products()
    
    msg = "📂 **CATALOG**\n\n"
    if not products:
        msg += "No products found in Database."
    else:
        for p in products:
            msg += f"🔹 **{p['display_name']}**\n"
            msg += f"   └─ Price: ${p['price_usd']} USD\n"
            msg += f"   └─ Key: `{p['key_name']}`\n\n"
    
    msg += "ℹ️ Use `.buy [key]` to purchase instant access."
    await event.reply(msg)

@client.on(events.NewMessage(pattern=r'\.buy(?:\s+(.*))?'))
async def cmd_buy(event):
    if not await can_run_command(event): return
    
    key = event.pattern_match.group(1)
    if not key:
        await event.reply("🛒 **Usage:** `.buy ebook` (or product key)")
        return
    
    product = await db.get_product(key.lower())
    
    if not product:
        await event.reply("❌ Product not found. Check `.list`.")
        return

    # Generate Order ID
    import uuid
    order_id = str(uuid.uuid4())[:8]
    user_id = event.sender_id
    price = float(product['price_usd'])

    # Create Payment Link
    # Note: If you don't have Oxapay key yet, this will fail.
    # For now, we simulate a link or use manual check.
    if OXAPAY_KEY == "Paste_Your_Oxapay_Merchant_Key_Here":
        # Fallback if no API key configured
        await event.reply(
            f"💳 **MANUAL PURCHASE: {product['display_name']}**\n"
            f"💵 **Price:** ${price} USD\n\n"
            f"Please send exact amount to my wallet and contact me with ID `{order_id}`:\n"
            f"👤 **[CONTACT OWNER]({MY_USER_LINK})**"
        )
    else:
        pay_url = create_crypto_payment(price, order_id)
        if pay_url:
            await db.create_order(order_id, user_id, key, price)
            await event.reply(
                f"💳 **INVOICE GENERATED**\n"
                f"📦 **Item:** {product['display_name']}\n"
                f"💵 **Total:** ${price} USDT\n\n"
                f"👉 **[CLICK HERE TO PAY]({pay_url})**\n\n"
                f"⏳ Access will be sent automatically upon confirmation."
            )
        else:
            await event.reply("❌ Error generating invoice. Please contact admin.")

# ==========================================
# 👮‍♂️ ADMIN COMMANDS (DB MANAGEMENT)
# ==========================================
@client.on(events.NewMessage(outgoing=True, pattern=r'\.dbadd\s+(.*)'))
async def admin_db_add(event):
    # Format: .dbadd key|Display Name|100.00|Desc|Link
    try:
        args = event.pattern_match.group(1).split('|')
        async with db.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO products (key_name, display_name, price_usd, description, file_url) VALUES ($1, $2, $3, $4, $5)",
                args[0].strip(), args[1].strip(), float(args[2].strip()), args[3].strip(), args[4].strip()
            )
        await event.edit(f"✅ Saved to NeonDB: {args[0]}")
    except Exception as e:
        await event.edit(f"❌ DB Error: {e}")

# ==========================================
# 🏁 RUN
# ==========================================
async def main():
    print("🌍 Web Server Online...")
    start_server()
    await db.connect() # Connect to Neon
    print("🚀 Userbot Active...")
    await client.start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
