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
# ⚙️ CREDENCIALES
# ==========================================
API_ID = int(os.getenv('API_ID', '32541501'))
API_HASH = os.getenv('API_HASH', '66f7a1c72eac5d25705ef1d35275ca4f')
SESSION_STRING = os.getenv('SESSION_STRING')
DB_URL = os.getenv('DB_URL')
OXAPAY_KEY = os.getenv('OXAPAY_KEY', 'WGJMFR-0DMVXO-IRCXPB-GDJHED')

TARGET_GROUP = 'myConfigCloud'
MY_USER_LINK = 'https://t.me/Virusnto'

# ==========================================
# 🌐 WEB SERVER (Para Render)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot Online. Tablas de DB verificadas."

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def start_server():
    t = Thread(target=run_server)
    t.start()

# ==========================================
# 🔌 DATABASE (Auto-Creación + Neon Fix)
# ==========================================
class Database:
    def __init__(self, db_url):
        self.db_url = db_url
        self.pool = None

    async def connect(self):
        if not self.pool:
            try:
                # 1. Limpiamos la URL para evitar error con asyncpg y Neon
                # Quitamos '?sslmode=require...' que asyncpg no soporta en el string
                url_limpia = self.db_url.split('?')[0]
                
                # 2. Conectamos forzando SSL
                self.pool = await asyncpg.create_pool(url_limpia, ssl='require')
                print("✅ Neon DB Conectada Correctamente")
                
                # 3. CREACIÓN AUTOMÁTICA DE TABLAS
                await self.init_tables()
                
            except Exception as e:
                print(f"❌ Error CRÍTICO conectando a DB: {e}")

    async def init_tables(self):
        """Crea las tablas si no existen (Auto-Reparación)"""
        async with self.pool.acquire() as conn:
            # Tabla Productos
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
            
            # Tabla Ordenes
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
            print("✅ Tablas 'products' y 'orders' verificadas/creadas.")

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

db = Database(DB_URL)

# ==========================================
# 💸 OXAPAY API
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
        if response.get("result") == 100:
            return {"url": response.get("pay_url"), "track_id": response.get("trackId")}
        return None
    except:
        return None

# ==========================================
# 🤖 USERBOT
# ==========================================
if not SESSION_STRING:
    print("❌ Falta SESSION_STRING")
    exit()

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

async def can_run_command(event):
    if event.out: return True
    chat = await event.get_chat()
    es_privado = event.is_private
    es_mi_grupo = (getattr(chat, 'username', '') == TARGET_GROUP)
    return es_privado or es_mi_grupo

# --- .INFO ---
@client.on(events.NewMessage(pattern=r'\.info(?:\s+(.*))?'))
async def cmd_info(event):
    if not await can_run_command(event): return
    arg = event.pattern_match.group(1)
    
    if not arg:
        return await event.reply("ℹ️ **Uso:** `.info ebook`")

    if not db.pool: return await event.reply("❌ Error: DB desconectada.")

    product = await db.get_product(arg.lower())
    if product:
        await event.reply(
            f"📘 **INFO: {product['display_name']}**\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📝 {product['description']}\n\n"
            f"💵 **Precio:** ${product['price_usd']} USD\n"
            f"🛒 Compra escribiendo: `.buy {product['key_name']}`"
        )
    else:
        await event.reply("❌ Producto no encontrado.")

# --- .LIST ---
@client.on(events.NewMessage(pattern=r'\.list'))
async def cmd_list(event):
    if not await can_run_command(event): return
    if not db.pool: return await event.reply("❌ Error: DB desconectada.")
    
    products = await db.get_all_products()
    msg = "📂 **CATÁLOGO**\n\n"
    if products:
        for p in products:
            msg += f"🔹 **{p['display_name']}** (`{p['key_name']}`)\n"
            msg += f"   💰 ${p['price_usd']} USD\n\n"
    else:
        msg += "⚠️ Catálogo vacío. Usa `.add` para llenar la tienda.\n"
    
    msg += "ℹ️ Usa `.buy` para ver el menú de compra."
    await event.reply(msg)

# --- .BUY (MEJORADO) ---
@client.on(events.NewMessage(pattern=r'\.buy(?:\s+(.*))?'))
async def cmd_buy(event):
    if not await can_run_command(event): return
    if not db.pool: return await event.reply("❌ Error: DB desconectada.")
    
    key_raw = event.pattern_match.group(1)
    key = key_raw.strip() if key_raw else None
    
    # 1. Menú General
    if not key:
        products = await db.get_all_products()
        msg = "🛒 **TIENDA DISPONIBLE**\n\n"
        if products:
            for p in products:
                msg += f"🔸 **{p['display_name']}**\n"
                msg += f"   💰 ${p['price_usd']} USD\n"
                msg += f"   👉 Pide tu factura: `.buy {p['key_name']}`\n\n"
        else:
            msg += "⚠️ No hay productos aún."
        return await event.reply(msg)

    # 2. Facturación
    product = await db.get_product(key.lower())
    if not product:
        return await event.reply("❌ Producto no encontrado.")

    import uuid
    order_id = str(uuid.uuid4())[:8]
    amount = float(product['price_usd'])
    
    msg_wait = await event.reply(f"🔄 Conectando Oxapay (${amount})...")
    invoice = create_invoice(amount, order_id, f"Compra: {product['display_name']}")
    
    if invoice:
        await db.create_order(order_id, invoice['track_id'], event.sender_id, key, amount)
        await msg_wait.edit(
            f"💳 **FACTURA GENERADA**\n"
            f"📦 {product['display_name']}\n"
            f"💵 **${amount} USD**\n\n"
            f"🔗 **[PAGAR AQUÍ (USDT/BTC/LTC)]({invoice['url']})**\n\n"
            f"⏳ Tienes 60 minutos."
        )
    else:
        await msg_wait.edit("❌ Error API Pagos (Revisa tu API Key).")

# --- .ADD (ADMIN) ---
@client.on(events.NewMessage(outgoing=True, pattern=r'\.add\s+(.*)'))
async def admin_add(event):
    if not db.pool: return await event.edit("❌ DB Desconectada.")
    try:
        args = event.pattern_match.group(1).split('|')
        k, n, p = args[0].strip().lower(), args[1].strip(), float(args[2].strip())
        d = args[3].strip() if len(args) > 3 else "Sin descripción"
        l = args[4].strip() if len(args) > 4 else "N/A"

        async with db.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO products (key_name, display_name, price_usd, description, file_url) 
                   VALUES ($1, $2, $3, $4, $5)
                   ON CONFLICT (key_name) DO UPDATE SET price_usd=$3, display_name=$2, description=$4""",
                k, n, p, d, l
            )
        await event.edit(f"✅ Agregado a DB: {n}")
    except Exception as e:
        await event.edit(f"❌ Error: {e}")

# ==========================================
# 🏁 RUN
# ==========================================
async def main():
    print("🌍 Server Online...")
    start_server()
    
    print("🔌 Conectando DB...")
    await db.connect() # ¡Esto creará las tablas si faltan!
    
    print("🚀 Bot Listo.")
    await client.start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())