import os
import asyncio
import hashlib
import base64
import json
import requests
import asyncpg
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from keep_alive import start_server

# ==========================================
# ⚙️ TUS SECRETOS (VARIABLES DE ENTORNO)
# ==========================================
# Telegram
API_ID = int(os.getenv('API_ID', '32541501'))
API_HASH = os.getenv('API_HASH', '66f7a1c72eac5d25705ef1d35275ca4f')
SESSION_STRING = os.getenv('SESSION_STRING')

# Database (Neon)
DB_URL = os.getenv('DB_URL')

# Cryptomus (Poner en Environment Variables de Render)
CRYPTOMUS_MERCHANT_ID = os.getenv('CRYPTOMUS_MERCHANT_ID', 'PON_TU_MERCHANT_ID')
CRYPTOMUS_API_KEY = os.getenv('CRYPTOMUS_API_KEY', 'PON_TU_API_KEY')

# Bot Config
TARGET_GROUP = 'myConfigCloud'
MY_USER_LINK = 'https://t.me/Virusnto'

# ==========================================
# 🔌 BASE DE DATOS
# ==========================================
class Database:
    def __init__(self, db_url):
        self.db_url = db_url
        self.pool = None

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.db_url)
            print("✅ DB Conectada")

    async def get_product(self, key):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM products WHERE key_name = $1", key)

    async def create_order(self, order_id, cryptomus_uuid, user_id, product_key, amount):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO orders (order_id, cryptomus_uuid, user_id, product_key, amount_usd) VALUES ($1, $2, $3, $4, $5)",
                order_id, cryptomus_uuid, user_id, product_key, amount
            )
            
    async def get_all_products(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT * FROM products")

db = Database(DB_URL)

# ==========================================
# 💸 MOTOR DE PAGOS (CRYPTOMUS)
# ==========================================
def create_invoice(amount, order_id, name):
    """Genera un link de pago con Cryptomus"""
    url = "https://api.cryptomus.com/v1/payment"
    
    # Datos de la factura
    payload = {
        "amount": str(amount),
        "currency": "USD",
        "order_id": order_id,
        "url_callback": "https://google.com", # Webhook (Opcional por ahora)
        "url_return": MY_USER_LINK,
        "is_payment_multiple": False,
        "lifetime": 3600, # 1 Hora para pagar
        "to_currency": "USDT" # Preferencia de moneda
    }

    # 🔐 Generar la Firma de Seguridad (Cryptomus Signature)
    # Base64 del JSON
    data_json = json.dumps(payload).replace(" ", "") # Importante quitar espacios
    data_base64 = base64.b64encode(data_json.encode('utf-8')).decode('utf-8')
    # Hash MD5 (Base64 + API Key)
    sign_str = data_base64 + CRYPTOMUS_API_KEY
    sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()

    headers = {
        "merchant": CRYPTOMUS_MERCHANT_ID,
        "sign": sign,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        result = response.json()
        
        if "result" in result:
            return {
                "url": result["result"]["url"],
                "uuid": result["result"]["uuid"]
            }
        else:
            print(f"❌ Error Cryptomus: {result}")
            return None
    except Exception as e:
        print(f"❌ Error API: {e}")
        return None

# ==========================================
# 🤖 BOT LÓGICA
# ==========================================
if not SESSION_STRING:
    print("Falta SESSION_STRING")
    exit()

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

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
    msg = "📂 **CATÁLOGO DISPONIBLE**\n\n"
    if not products: msg += "⚠️ Catálogo vacío."
    else:
        for p in products:
            msg += f"🔹 **{p['display_name']}**\n   💰 ${p['price_usd']} USD | Clave: `{p['key_name']}`\n\n"
    msg += "🛒 Usa `.buy [clave]` para comprar."
    await event.reply(msg)

@client.on(events.NewMessage(pattern=r'\.buy(?:\s+(.*))?'))
async def cmd_buy(event):
    if not await can_run_command(event): return
    
    key = event.pattern_match.group(1)
    if not key: return await event.reply("❌ Uso: `.buy ebook`")
    
    # 1. Buscar producto en Neon
    product = await db.get_product(key.lower())
    if not product: return await event.reply("❌ Producto no encontrado.")

    # 2. Generar ID único
    import uuid
    order_id = str(uuid.uuid4())[:12]
    
    # 3. Crear Factura en Cryptomus
    await event.reply("🔄 **Generando factura segura...**")
    
    # IMPORTANTE: Si no has puesto las API KEYS reales, esto fallará.
    invoice = create_invoice(product['price_usd'], order_id, product['display_name'])
    
    if invoice:
        # 4. Guardar Orden en Neon
        await db.create_order(order_id, invoice['uuid'], event.sender_id, key, product['price_usd'])
        
        # 5. Enviar Link
        await event.reply(
            f"🧾 **FACTURA CREADA**\n"
            f"📦 Producto: {product['display_name']}\n"
            f"💵 Total: **${product['price_usd']} USD**\n\n"
            f"👇 Haz clic para pagar (USDT, BTC, LTC, TRX):\n"
            f"🔗 **[PAGAR AQUÍ AHORA]({invoice['url']})**\n\n"
            f"⏳ Tienes 60 minutos. Una vez pagado, envíame el comprobante."
        )
    else:
        await event.reply("❌ Error conectando con la pasarela de pago. Intenta más tarde.")

# Admin: Agregar producto a la DB
@client.on(events.NewMessage(outgoing=True, pattern=r'\.add\s+(.*)'))
async def admin_add(event):
    try:
        # .add ebook | The Art of Cracking | 100 | Desc | Link
        args = event.pattern_match.group(1).split('|')
        async with db.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO products (key_name, display_name, price_usd, description, file_url) 
                   VALUES ($1, $2, $3, $4, $5)
                   ON CONFLICT (key_name) DO UPDATE SET price_usd=$3""",
                args[0].strip(), args[1].strip(), float(args[2].strip()), args[3].strip(), args[4].strip()
            )
        await event.edit(f"✅ Producto guardado: {args[1]}")
    except Exception as e: await event.edit(f"❌ Error: {e}")

# ==========================================
# 🏁 RUN
# ==========================================
async def main():
    print("🌍 Iniciando...")
    start_server()
    await db.connect()
    print("🚀 Userbot Listo (Cryptomus Mode)")
    await client.start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
