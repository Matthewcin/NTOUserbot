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
# 🌐 WEB SERVER (Keep Alive)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot Online. Sistema Operativo."

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def start_server():
    t = Thread(target=run_server)
    t.start()

# ==========================================
# 🔌 DATABASE (NEON + AUTO-FIX)
# ==========================================
class Database:
    def __init__(self, db_url):
        self.db_url = db_url
        self.pool = None

    async def connect(self):
        if not self.pool:
            try:
                # Limpiamos la URL para evitar errores con asyncpg
                url_limpia = self.db_url.split('?')[0]
                self.pool = await asyncpg.create_pool(url_limpia, ssl='require')
                
                # Verificamos/Creamos tablas
                await self.init_tables()
            except Exception as e:
                print(f"❌ Error CRÍTICO DB: {e}")

    async def init_tables(self):
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
            
    async def delete_product(self, key):
        if not self.pool: return False
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM products WHERE key_name = $1", key)
            return result != "DELETE 0"

db = Database(DB_URL)

# ==========================================
# 💸 OXAPAY (MERCHANT API)
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
# 🤖 USERBOT SYSTEM
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

# ---------------------------------------------
# 📜 1. COMANDOS INFORMATIVOS (.status .cmds .help)
# ---------------------------------------------
@client.on(events.NewMessage(pattern=r'\.status'))
async def cmd_status(event):
    if not await can_run_command(event): return
    await event.reply("✅ **SISTEMA ONLINE**\n🛡️ Neon DB: Conectada\n💰 Pasarela: Activa")

@client.on(events.NewMessage(pattern=r'\.help'))
async def cmd_help(event):
    if not await can_run_command(event): return
    await event.reply("🆘 **AYUDA**\nUsa `.cmds` para ver la lista completa de comandos.")

@client.on(events.NewMessage(pattern=r'\.cmds'))
async def cmd_cmds(event):
    if not await can_run_command(event): return
    msg = (
        "🤖 **LISTA DE COMANDOS**\n"
        "━━━━━━━━━━━━━━━━\n"
        "🔹 `.list` » Ver catálogo\n"
        "🔹 `.info [item]` » Detalles de producto\n"
        "🔹 `.buy` » Menú de compra\n"
        "🔹 `.buy [item]` » Generar factura\n"
        "🔹 `.request [txt]` » Solicitar algo\n"
        "🔹 `.status` » Estado del bot"
    )
    if event.out: # Solo tú ves esto
        msg += (
            "\n\n👮‍♂️ **ADMIN (Solo tú):**\n"
            "🔸 `.add key|Nom|$$|Desc` » Agregar\n"
            "🔸 `.del key` » Borrar"
        )
    await event.reply(msg)

# ---------------------------------------------
# 📂 2. COMANDOS DE TIENDA (.list .info .request)
# ---------------------------------------------
@client.on(events.NewMessage(pattern=r'\.list'))
async def cmd_list(event):
    if not await can_run_command(event): return
    if not db.pool: return await event.reply("❌ Error DB")
    
    products = await db.get_all_products()
    msg = "📂 **CATÁLOGO DISPONIBLE**\n\n"
    if products:
        for p in products:
            msg += f"🔹 **{p['display_name']}**\n   💰 ${p['price_usd']} USD | Clave: `{p['key_name']}`\n\n"
    else:
        msg += "⚠️ Tienda vacía.\n"
    msg += "ℹ️ `.buy [clave]` para comprar."
    await event.reply(msg)

@client.on(events.NewMessage(pattern=r'\.info(?:\s+(.*))?'))
async def cmd_info(event):
    if not await can_run_command(event): return
    arg = event.pattern_match.group(1)
    if not arg: return await event.reply("ℹ️ Uso: `.info ebook`")

    product = await db.get_product(arg.lower())
    if product:
        await event.reply(
            f"📘 **INFO: {product['display_name']}**\n━━━━━━━━━━━━━━━━\n"
            f"📝 {product['description']}\n\n"
            f"💵 Precio: **${product['price_usd']} USD**\n"
            f"👉 Compra con: `.buy {product['key_name']}`"
        )
    else:
        await event.reply("❌ Producto no encontrado.")

@client.on(events.NewMessage(pattern=r'\.request(?:\s+(.*))?'))
async def cmd_request(event):
    if not await can_run_command(event): return
    arg = event.pattern_match.group(1)
    if not arg: return await event.reply("📝 Dime qué necesitas. Ej: `.request config amazon`")
    
    await event.reply(f"✅ **Solicitud Recibida:** {arg}\nLo tendré en cuenta para futuras actualizaciones.")

# ---------------------------------------------
# 💳 3. COMANDO DE COMPRA (.buy)
# ---------------------------------------------
@client.on(events.NewMessage(pattern=r'\.buy(?:\s+(.*))?'))
async def cmd_buy(event):
    if not await can_run_command(event): return
    if not db.pool: return await event.reply("❌ Error DB")
    
    key_raw = event.pattern_match.group(1)
    key = key_raw.strip() if key_raw else None
    
    # CASO 1: SIN ARGUMENTO (MENU)
    if not key:
        products = await db.get_all_products()
        msg = "🛒 **MENÚ DE COMPRA**\n\n"
        if products:
            for p in products:
                msg += f"🔸 **{p['display_name']}** (${p['price_usd']})\n   👉 `.buy {p['key_name']}`\n\n"
        else:
            msg += "⚠️ No hay productos disponibles."
        return await event.reply(msg)

    # CASO 2: CON ARGUMENTO (FACTURA)
    product = await db.get_product(key.lower())
    if not product: return await event.reply("❌ Producto no encontrado.")

    import uuid
    order_id = str(uuid.uuid4())[:8]
    amount = float(product['price_usd'])
    
    msg_wait = await event.reply(f"🔄 Creando factura de ${amount}...")
    invoice = create_invoice(amount, order_id, f"Compra: {product['display_name']}")
    
    if invoice:
        await db.create_order(order_id, invoice['track_id'], event.sender_id, key, amount)
        await msg_wait.edit(
            f"💳 **FACTURA GENERADA**\n📦 {product['display_name']}\n💵 **${amount} USD**\n\n"
            f"🔗 **[PAGAR AQUÍ (USDT/BTC/LTC)]({invoice['url']})**\n\n"
            f"⏳ Tienes 60 minutos."
        )
    else:
        await msg_wait.edit("❌ Error en pasarela de pagos.")

# ---------------------------------------------
# 👮‍♂️ 4. COMANDOS ADMIN (.add .del)
# ---------------------------------------------
@client.on(events.NewMessage(outgoing=True, pattern=r'\.add\s+(.*)'))
async def admin_add(event):
    try:
        args = event.pattern_match.group(1).split('|')
        if len(args) < 3: return await event.edit("❌ Uso: `.add key | Nombre | $$ | Desc`")
        
        k, n, p = args[0].strip().lower(), args[1].strip(), float(args[2].strip())
        d = args[3].strip() if len(args) > 3 else "Sin desc"
        l = args[4].strip() if len(args) > 4 else "N/A"

        async with db.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO products (key_name, display_name, price_usd, description, file_url) 
                   VALUES ($1, $2, $3, $4, $5)
                   ON CONFLICT (key_name) DO UPDATE SET price_usd=$3, display_name=$2, description=$4""",
                k, n, p, d, l
            )
        await event.edit(f"✅ Guardado: {n}")
    except Exception as e: await event.edit(f"❌ Error: {e}")

@client.on(events.NewMessage(outgoing=True, pattern=r'\.del\s+(.*)'))
async def admin_del(event):
    key = event.pattern_match.group(1).strip().lower()
    if await db.delete_product(key):
        await event.edit(f"🗑️ Producto borrado: {key}")
    else:
        await event.edit(f"⚠️ No encontré: {key}")

# ==========================================
# 🏁 RUN + NOTIFICACIÓN
# ==========================================
async def main():
    print("🌍 Server Online...")
    start_server()
    await db.connect() 
    print("🚀 Telegram Login...")
    await client.start()
    
    # Auto-Notificación de éxito
    try:
        await client.send_message("me", "🚀 **BOT INICIADO CORRECTAMENTE**\n✅ DB: Conectada\n✅ Comandos: Listos")
    except: pass
    
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
