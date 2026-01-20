import requests
import uuid
import traceback
from telethon import events
from database import db
import config

# ==========================================
# 🔹 1. FUNCIONES AUXILIARES (OxaPay)
# ==========================================

async def create_oxapay_link(amount, order_id):
    url = "https://api.oxapay.com/merchants/request"
    
    data = {
        "merchant": config.OXAPAY_KEY,
        "amount": amount,
        "currency": "USD",
        "lifeTime": 30,
        "feePaidByPayer": 0,
        "underPaidCover": 2.5,
        "callbackUrl": config.WEBHOOK_URL,
        "returnUrl": "https://t.me/Virusnto",
        "description": f"Order {order_id}",
        "orderId": order_id
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        res_json = response.json()
        
        if res_json.get("result") == 100:
            return {
                "url": res_json.get("payLink"),
                "trackId": res_json.get("trackId")
            }
        else:
            print(f"❌ Error OxaPay: {res_json}")
            return None
    except Exception as e:
        print(f"⚠️ Exception OxaPay: {e}")
        return None

# ==========================================
# 🔹 2. HANDLERS (Comandos)
# ==========================================

# --- COMANDO .LIST (Faltaba este) ---
async def handler_list(event):
    if not event.out: return
    
    try:
        # Obtenemos todos los productos de la DB
        # Nota: Asumimos que db.pool existe. Hacemos la query directa aquí para asegurar.
        if not db.pool:
            await event.edit("❌ Error: Base de datos no conectada.")
            return

        async with db.pool.acquire() as conn:
            rows = await conn.fetch("SELECT key_name, display_name, price_usd FROM products")
        
        if not rows:
            await event.edit("📂 **CATÁLOGO VACÍO**\nNo hay productos en venta aún.")
            return
        
        # Construimos el mensaje
        msg = "🛒 **PRODUCTOS DISPONIBLES**\n\n"
        for row in rows:
            msg += f"🔹 <b>{row['display_name']}</b>\n"
            msg += f"   ├ Key: <code>{row['key_name']}</code>\n"
            msg += f"   └ Precio: ${row['price_usd']}\n\n"
            
        msg += "ℹ️ Usa <code>.info [key]</code> para ver detalles.\n"
        msg += "💳 Usa <code>.buy [key]</code> para comprar."
        
        await event.edit(msg, parse_mode='html')
        
    except Exception as e:
        await event.edit(f"❌ Error al listar: {e}")
        traceback.print_exc()

# --- COMANDO .INFO (Faltaba este también) ---
async def handler_info(event):
    if not event.out: return
    
    args = event.message.text.split()
    if len(args) < 2:
        await event.edit("ℹ️ Uso: `.info [key_producto]`")
        return
        
    key = args[1].lower().strip()
    
    try:
        product = await db.get_product(key)
        
        if not product:
            await event.edit(f"❌ Producto `{key}` no encontrado.")
            return
            
        msg = (
            f"📦 <b>{product['display_name']}</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"💰 <b>Precio:</b> ${product['price_usd']} USD\n"
            f"🔑 <b>Key:</b> <code>{product['key_name']}</code>\n\n"
            f"📝 <b>Descripción:</b>\n{product.get('description', 'Sin descripción')}\n\n"
            f"🛒 Para comprar escribe: <code>.buy {key}</code>"
        )
        await event.edit(msg, parse_mode='html')
        
    except Exception as e:
        await event.edit(f"❌ Error: {e}")

# --- COMANDO .BUY (El de OxaPay) ---
async def handler_buy(event):
    if not event.out: return
    
    args = event.message.text.split()
    if len(args) < 2:
        await event.edit("❌ **Uso:** `.buy [key_producto]`")
        return
    
    product_key = args[1].strip().lower()
    
    try:
        await event.edit(f"🔍 Buscando `{product_key}`...")
        product = await db.get_product(product_key)
        
        if not product:
            await event.edit(f"❌ Producto `{product_key}` no existe.")
            return
        
        await event.edit("🔄 **Creando factura crypto...**")
        
        amount = float(product['price_usd'])
        order_id = str(uuid.uuid4())[:8]
        
        payment_data = await create_oxapay_link(amount, order_id)
        
        if payment_data:
            await db.create_order(
                order_id, 
                payment_data['trackId'], 
                event.chat_id, 
                product_key, 
                amount
            )
            
            mensaje_final = (
                f"🛒 <b>ORDEN CREADA</b>\n\n"
                f"📦 <b>Item:</b> {product['display_name']}\n"
                f"💵 <b>Total:</b> ${amount} USD\n"
                f"🆔 <b>ID:</b> <code>{order_id}</code>\n\n"
                f"👉 <a href='{payment_data['url']}'><b>[ PAGAR AHORA ]</b></a>\n\n"
                f"<i>⏳ Expira en 30 minutos.</i>"
            )
            await event.edit(mensaje_final, parse_mode='html', link_preview=False)
        else:
            await event.edit("❌ Error API OxaPay.")

    except Exception as e:
        await event.edit(f"❌ Error: {str(e)}")
        traceback.print_exc()
