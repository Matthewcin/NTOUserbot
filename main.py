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
# ⚙️ CREDENCIALES Y CONFIGURACIÓN
# ==========================================
# Variables de entorno (Render)
API_ID = int(os.getenv('API_ID', '32541501'))
API_HASH = os.getenv('API_HASH', '66f7a1c72eac5d25705ef1d35275ca4f')
SESSION_STRING = os.getenv('SESSION_STRING')
DB_URL = os.getenv('DB_URL')
# Aquí toma tu nueva clave de comerciante: WGJMFR-0DMVXO-IRCXPB-GDJHED
OXAPAY_KEY = os.getenv('OXAPAY_KEY') 

# Configuración del Userbot
TARGET_GROUP = 'myConfigCloud'
MY_USER_LINK = 'https://t.me/Virusnto'

# ==========================================
# 🌐 SERVIDOR WEB (Keep Alive)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot Online & Pagos Activos"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def start_server():
    t = Thread(target=run_server)
    t.start()

# ==========================================
# 🔌 GESTOR DE BASE DE DATOS (Neon)
# ==========================================
class Database:
    def __init__(self, db_url):
        self.db_url = db_url
        self.pool = None

    async def connect(self):
        if not self.pool:
            try:
                self.pool = await asyncpg.create_pool(self.db_url)
                print("✅ Conexión a Base de Datos: EXITOSA")
            except Exception as e:
                print(f"❌ Error conectando a Neon DB: {e}")

    # Obtener producto
    async def get_product(self, key):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM products WHERE key_name = $1", key)

    # Obtener todos los productos
    async def get_all_products(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT * FROM products")

    # Guardar nueva orden
    async def create_order(self, order_id, track_id, user_id, product_key, amount):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO orders (order_id, oxapay_track_id, user_id, product_key, amount_usd) 
                   VALUES ($1, $2, $3, $4, $5)""",
                order_id, track_id, user_id, product_key, amount
            )

db = Database(DB_URL)

# ==========================================
# 💸 MOTOR DE PAGOS (OXAPAY MERCHANT API)
# ==========================================
def create_invoice(amount, order_id, description):
    """Crea un link de pago usando la API de Comerciante"""
    url = "https://api.oxapay.com/merchants/request"
    
    payload = {
        "merchant": OXAPAY_KEY,
        "amount": amount,
        "currency": "USDT", # Moneda base del precio
        "life_time": 60,    # Tiempo para pagar (minutos)
        "fee_paid_by_payer": 0, # 0 = Tú pagas fee, 1 = Cliente paga
        "return_url": MY_USER_LINK,
        "description": description,
        "order_id": order_id
    }

    try:
        response = requests.post(url, json=payload).json()
        
        # El código 100 significa Éxito
        if response.get("result") == 100:
            return {
                "url": response.get("pay_url"),
                "track_id": response.get("trackId")
            }
        else:
            print(f"❌ Error Oxapay: {response.get('message')}")
            return None
    except Exception as e:
        print(f"❌ Excepción API: {e}")
        return None

# ==========================================
# 🤖 LÓGICA DEL USERBOT
# ==========================================
if not SESSION_STRING:
    print("❌ ERROR CRÍTICO: Falta SESSION_STRING")
    exit()

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

async def can_run_command(event):
    """Permisos: Dueño (Tú) O Clientes en Privado/Grupo"""
    if event.out: return True
    chat = await event.get_chat()
    es_privado = event.is_private
    es_mi_grupo = (getattr(chat, 'username', '') == TARGET_GROUP)
    return es_privado or es_mi_grupo

# --- COMANDO .LIST ---
@client.on(events.NewMessage(pattern=r'\.list'))
async def cmd_list(event):
    if not await can_run_command(event): return
    
    products = await db.get_all_products()
    msg = "📂 **CATÁLOGO DISPONIBLE**\n\n"
    
    if not products:
        msg += "⚠️ No hay productos configurados aún."
    else:
        for p in products:
            msg += f"🔹 **{p['display_name']}**\n"
            msg += f"   💰 Precio: ${p['price_usd']} USD\n"
            msg += f"   🔑 Clave: `{p['key_name']}`\n\n"
    
    msg += "🛒 Escribe `.buy [clave]` para comprar."
    await event.reply(msg)

# --- COMANDO .BUY ---
@client.on(events.NewMessage(pattern=r'\.buy(?:\s+(.*))?'))
async def cmd_buy(event):
    if not await can_run_command(event): return
    
    key = event.pattern_match.group(1)
    if not key:
        return await event.reply("❌ **Uso correcto:** `.buy ebook` (o el nombre del producto)")
    
    # 1. Buscar producto en DB
    product = await db.get_product(key.lower())
    if not product:
        return await event.reply("❌ Producto no encontrado. Mira la lista con `.list`.")

    # 2. Preparar Orden
    import uuid
    order_id = str(uuid.uuid4())[:8]
    amount = float(product['price_usd'])
    name = product['display_name']

    # 3. Generar Link con Oxapay
    msg_espera = await event.reply(f"🔄 **Generando factura para {name}...**")
    
    invoice = create_invoice(amount, order_id, f"Compra: {name}")
    
    if invoice:
        # 4. Guardar en Base de Datos
        await db.create_order(order_id, invoice['track_id'], event.sender_id, key, amount)
        
        # 5. Enviar Link al Cliente
        await msg_espera.edit(
            f"💳 **FACTURA DE PAGO CREADA**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 **Producto:** {name}\n"
            f"💵 **Total:** ${amount} USD\n\n"
            f"👇 **HAZ CLIC PARA PAGAR:**\n"
            f"🔗 **[PAGAR CON CRIPTO AHORA]({invoice['url']})**\n\n"
            f"ℹ️ Aceptamos: USDT, Bitcoin, Litecoin, Tron, etc.\n"
            f"⏳ El enlace expira en 60 minutos.\n\n"
            f"✅ **IMPORTANTE:** Cuando pagues, envíame el comprobante por aquí."
        )
    else:
        await msg_espera.edit("❌ Error conectando con la pasarela de pagos. Intenta más tarde.")

# --- COMANDO ADMIN: .ADD (Guardar producto en DB) ---
@client.on(events.NewMessage(outgoing=True, pattern=r'\.add\s+(.*)'))
async def admin_add(event):
    # Formato: .add ebook | Ebook Pro | 100 | Descripción | Link(opcional)
    try:
        args = event.pattern_match.group(1).split('|')
        if len(args) < 3:
            return await event.edit("❌ Faltan datos. Uso: `.add clave | Nombre | Precio | Desc`")

        key = args[0].strip().lower()
        name = args[1].strip()
        price = float(args[2].strip())
        desc = args[3].strip() if len(args) > 3 else "Sin descripción"
        link_file = args[4].strip() if len(args) > 4 else "N/A"
        
        async with db.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO products (key_name, display_name, price_usd, description, file_url) 
                   VALUES ($1, $2, $3, $4, $5)
                   ON CONFLICT (key_name) DO UPDATE 
                   SET price_usd=$3, display_name=$2, description=$4, file_url=$5""",
                key, name, price, desc, link_file
            )
        await event.edit(f"✅ **Producto Guardado en Neon:** {name}")
    except Exception as e:
        await event.edit(f"❌ Error DB: {e}")

# ==========================================
# 🏁 INICIO DEL SISTEMA
# ==========================================
async def main():
    print("🌍 Iniciando Servidor Web...")
    start_server()
    
    print("🔌 Conectando a Base de Datos...")
    await db.connect()
    
    print("🚀 Userbot Iniciado (Modo Comerciante Oxapay)")
    await client.start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
