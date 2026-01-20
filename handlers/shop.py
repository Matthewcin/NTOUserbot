import requests
import uuid
import sys
import traceback
from telethon import events
from database import db
import config

# Función auxiliar para imprimir logs visibles en Render
def log(msg):
    print(f"🛒 [SHOP DEBUG] {msg}", flush=True)

async def create_oxapay_link(amount, order_id, email="no-mail@test.com"):
    """Genera el link de pago usando la API de Merchant de OxaPay"""
    url = "https://api.oxapay.com/merchants/request"
    
    log(f"Iniciando petición a OxaPay para Orden: {order_id} - Monto: {amount}")
    
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
        "orderId": order_id,
        "email": email
    }
    
    try:
        # Imprimimos qué estamos enviando (Ocultando parte de la key por seguridad)
        masked_key = config.OXAPAY_KEY[:4] + "****" if config.OXAPAY_KEY else "NONE"
        log(f"Enviando datos a OxaPay API... Key usada: {masked_key}")
        log(f"Webhook URL configurada: {config.WEBHOOK_URL}")

        response = requests.post(url, json=data, timeout=10)
        
        log(f"Status Code recibido: {response.status_code}")
        
        try:
            res_json = response.json()
            log(f"Respuesta RAW de OxaPay: {res_json}")
        except:
            log(f"No se pudo leer JSON. Texto plano: {response.text}")
            return None
        
        if res_json.get("result") == 100:
            log("✅ Link generado exitosamente.")
            return {
                "url": res_json.get("payLink"),
                "trackId": res_json.get("trackId")
            }
        else:
            log(f"❌ OxaPay devolvió error (Result != 100). Mensaje: {res_json.get('message')}")
            return None

    except Exception as e:
        log(f"⚠️ EXCEPCIÓN CRÍTICA al contactar OxaPay: {e}")
        return None

# --- HANDLER DEL COMANDO ---

async def handler_buy(event):
    # Solo ejecutamos si el mensaje sale de ti (Userbot)
    if not event.out: 
        return
    
    try:
        log("--- COMANDO .BUY DETECTADO ---")
        
        # Obtener argumentos
        text = event.message.text # ej: .buy ebook
        args = text.split()
        
        if len(args) < 2:
            log("Faltan argumentos.")
            await event.edit("❌ Usage: `.buy [KeyName]`")
            return
        
        product_key = args[1].strip().lower()
        log(f"Buscando producto: '{product_key}' en DB...")
        
        # Buscar producto en DB
        product = await db.get_product(product_key)
        
        if not product:
            log(f"❌ Producto '{product_key}' NO encontrado en la base de datos.")
            await event.edit(f"❌ Product `{product_key}` not found in DB.")
            return
        
        log(f"✅ Producto encontrado: {product['display_name']} - Precio: {product['price_usd']}")

        # Generar datos
        order_id = str(uuid.uuid4())[:8]
        amount = float(product['price_usd'])
        
        await event.edit("🔄 Connecting to OxaPay...")
        
        # Crear Pago
        payment_data = await create_oxapay_link(amount, order_id)
        
        if payment_data:
            log("Guardando orden en DB...")
            # Guardar en DB
            await db.create_order(
                order_id, 
                payment_data['trackId'], 
                event.chat_id, 
                product_key, 
                amount
            )
            
            # Responder con el link
            msg = (
                f"🛒 <b>INVOICE CREATED</b>\n"
                f"📦 Product: {product['display_name']}\n"
                f"💵 Amount: ${amount} USD\n"
                f"🔗 Link: <a href='{payment_data['url']}'>Click to Pay (Crypto)</a>\n\n"
                f"<i>Link expires in 30 minutes.</i>"
            )
            await event.edit(msg, parse_mode='html')
            log("✅ Mensaje editado con el link. Proceso finalizado.")
        else:
            log("❌ Falló la generación del link (payment_data es None).")
            await event.edit("❌ Error generating invoice. Check Render Logs.")

    except Exception as e:
        log(f"🔥 CRASH EN HANDLER_BUY: {e}")
        traceback.print_exc() # Imprime el error completo en logs
        await event.edit(f"❌ System Error: {str(e)}")
