import requests
import uuid
import traceback
from telethon import events
from database import db
import config

# --- FUNCIÓN PARA GENERAR LINK DE OXAPAY ---
async def create_oxapay_link(amount, order_id):
    url = "https://api.oxapay.com/merchants/request"
    
    data = {
        "merchant": config.OXAPAY_KEY,
        "amount": amount,
        "currency": "USD",
        "lifeTime": 30, # El link dura 30 minutos
        "feePaidByPayer": 0,
        "underPaidCover": 2.5,
        "callbackUrl": config.WEBHOOK_URL,
        "returnUrl": "https://t.me/Virusnto", # A donde vuelven tras pagar
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

# --- HANDLER PRINCIPAL (.buy) ---

async def handler_buy(event):
    # 1. Seguridad: Solo responde si TÚ (el dueño del userbot) escribiste el mensaje.
    if not event.out: 
        return
    
    # 2. Obtener argumentos del mensaje (ej: .buy ebook)
    args = event.message.text.split()
    
    if len(args) < 2:
        await event.edit("❌ **Uso correcto:** `.buy [nombre_producto]`")
        return
    
    product_key = args[1].strip().lower()
    
    try:
        # 3. Aviso visual de "Cargando..." en el mismo chat
        await event.edit(f"🔍 Buscando producto `{product_key}`...")
        
        # 4. Buscar en Base de Datos
        product = await db.get_product(product_key)
        
        if not product:
            await event.edit(f"❌ El producto `{product_key}` no existe en la base de datos.")
            return
        
        # 5. Generar Pago
        await event.edit("🔄 **Generando factura con OxaPay...**")
        
        amount = float(product['price_usd'])
        order_id = str(uuid.uuid4())[:8]
        
        payment_data = await create_oxapay_link(amount, order_id)
        
        if payment_data:
            # Guardar orden en DB para que el Webhook la reconozca luego
            await db.create_order(
                order_id, 
                payment_data['trackId'], 
                event.chat_id, 
                product_key, 
                amount
            )
            
            # 6. MOSTRAR RESULTADO FINAL EN EL MISMO CHAT
            # Usamos HTML para que el link se vea bonito y clicable
            mensaje_final = (
                f"🛒 <b>ORDEN CREADA</b>\n\n"
                f"📦 <b>Producto:</b> {product['display_name']}\n"
                f"💵 <b>Precio:</b> ${amount} USD\n"
                f"🆔 <b>ID Orden:</b> <code>{order_id}</code>\n\n"
                f"👉 <a href='{payment_data['url']}'><b>[ PAGAR CON CRYPTO ]</b></a>\n"
                f"👉 <a href='{payment_data['url']}'><b>[ CLICK AQUÍ ]</b></a>\n\n"
                f"<i>⏳ El enlace expira en 30 minutos.</i>"
            )
            
            # link_preview=False evita que Telegram intente cargar una vista previa de la web de pagos
            await event.edit(mensaje_final, parse_mode='html', link_preview=False)
            
        else:
            await event.edit("❌ Error: No se pudo conectar con OxaPay. Revisa la API Key.")

    except Exception as e:
        # Si algo explota, que te lo diga en el chat
        error_msg = f"❌ **Error del Sistema:**\n`{str(e)}`"
        await event.edit(error_msg)
        traceback.print_exc()
