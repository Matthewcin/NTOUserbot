import asyncio
import random
import uuid
import io
import qrcode
from telethon import events
from database import db
from handlers.utils import can_run_command
from binance_api import get_coin_price, get_deposit_address, verify_payment

WAITING_FOR_TXID = {}

async def reply_or_edit(event, text):
    if event.out:
        await event.edit(text, parse_mode='html')
    else:
        await event.reply(text, parse_mode='html')

async def handler_list(event):
    if not await can_run_command(event): return
    
    try:
        if not db.pool:
            await reply_or_edit(event, "❌ Error: DB Disconnected.")
            return

        async with db.pool.acquire() as conn:
            rows = await conn.fetch("SELECT key_name, display_name, price_usd FROM products")
        
        if not rows:
            await reply_or_edit(event, "📂 <b>EMPTY CATALOG</b>", parse_mode='html')
            return
        
        msg = "🛒 <b>AVAILABLE PRODUCTS</b>\n\n"
        for row in rows:
            msg += f"🔹 <b>{row['display_name']}</b>\n"
            msg += f"   ├ Key: <code>{row['key_name']}</code>\n"
            msg += f"   └ Price: ${row['price_usd']}\n\n"
            
        msg += "ℹ️ Use <code>.info [key]</code> to see details.\n"
        msg += "💳 Use <code>.buy [key] [SYMBOL]</code> to buy."
        
        await reply_or_edit(event, msg)
        
    except Exception as e:
        await reply_or_edit(event, f"❌ Error listing products: {e}")

async def handler_info(event):
    if not await can_run_command(event): return
    args = event.message.text.split()
    if len(args) < 2:
        await reply_or_edit(event, "ℹ️ Usage: `.info [key]`")
        return
    key = args[1].lower().strip()
    product = await db.get_product(key)
    if not product:
        await reply_or_edit(event, f"❌ Product <code>{key}</code> not found.", parse_mode='html')
        return
    msg = (f"📦 <b>{product['display_name']}</b>\n"
           f"💰 <b>Price:</b> ${product['price_usd']} USD\n"
           f"🔑 <b>Key:</b> <code>{product['key_name']}</code>\n\n"
           f"📝 <b>Description:</b>\n{product.get('description', 'No description')}\n\n"
           f"🛒 Buy: <code>.buy {key} [SYMBOL]</code>")
    await reply_or_edit(event, msg)

async def handler_buy(event):
    if not await can_run_command(event): return
    args = event.message.text.split()
    if len(args) < 3:
        await reply_or_edit(event, "❌ <b>Usage:</b> <code>.buy [key] [SYMBOL]</code>", parse_mode='html')
        return
    
    product_key = args[1].lower()
    symbol = args[2].upper()
    
    alias = {"LITECOIN": "LTC", "BITCOIN": "BTC", "ETHEREUM": "ETH", "TRON": "TRX", "TETHER": "USDT"}
    symbol = alias.get(symbol, symbol)
    
    product = await db.get_product(product_key)
    if not product:
        await reply_or_edit(event, f"❌ Product <code>{product_key}</code> not found.", parse_mode='html')
        return

    crypto_price = 1.0 if symbol == "USDT" else get_coin_price(f"{symbol}USDT")
    if crypto_price <= 0:
        await reply_or_edit(event, f"❌ Error: Could not fetch {symbol} price.")
        return

    address, tag = get_deposit_address(symbol)
    if not address:
        wallet = await db.get_wallet(symbol)
        if not wallet:
            await reply_or_edit(event, f"❌ Wallet for {symbol} not configured.")
            return
        address, tag = wallet['address'], ""
    
    usd_price = round(float(product['price_usd']) + round(random.uniform(0.01, 0.15), 2), 2)
    amount_crypto = round(usd_price / crypto_price, 8)
    
    qr = qrcode.make(address)
    bio = io.BytesIO()
    bio.name = 'qr.png'
    qr.save(bio, 'PNG')
    bio.seek(0)
    
    order_msg = (f"💳 <b>PAYMENT INSTRUCTIONS</b>\n"
                 f"📦 <b>Item:</b> {product['display_name']}\n"
                 f"💵 <b>Total:</b> ${usd_price} USD\n"
                 f"💰 <b>Send EXACTLY:</b> <code>{amount_crypto}</code> {symbol}\n\n"
                 f"📍 <b>Address:</b> <code>{address}</code>"
                 + (f"\n🏷 <b>Tag:</b> <code>{tag}</code>" if tag else "") +
                 f"\n\n⚠️ <b>Reply to this message ONLY with your TXID.</b>")

    sent_msg = await event.client.send_file(event.chat_id, bio, caption=order_msg, parse_mode='html')

    WAITING_FOR_TXID[event.chat_id] = {
        'order_id': str(uuid.uuid4())[:8],
        'product_key': product_key,
        'product_url': product.get('file_url', 'Admin contact needed'),
        'symbol': symbol,
        'amount_crypto': amount_crypto,
        'usd_price': usd_price,
        'message_id': sent_msg.id
    }

async def handler_txid(event):
    # DIAGNÓSTICO TOTAL: Esto imprime todo lo que llega al handler
    print(f"DEBUG_EVENT: Mensaje recibido: '{event.message.text}' | ChatID: {event.chat_id}")
    
    # Verificamos si este chat tiene órdenes pendientes
    if event.chat_id not in WAITING_FOR_TXID:
        # Si ves esto en la consola al enviar el TXID, el bot no tiene tu orden registrada
        print(f"DEBUG_EVENT: ChatID {event.chat_id} NO está en WAITING_FOR_TXID. Órdenes activas: {list(WAITING_FOR_TXID.keys())}")
        return
        
    # Verificamos si es un reply
    if not event.is_reply:
        print("DEBUG_EVENT: El mensaje NO es un reply.")
        return
        
    reply_to = await event.get_reply_message()
    order_info = WAITING_FOR_TXID[event.chat_id]
    
    # Verificamos si respondes al mensaje correcto
    if reply_to.id != order_info['message_id']:
        print(f"DEBUG_EVENT: Reply ID ({reply_to.id}) NO coincide con el mensaje de pago ({order_info['message_id']}).")
        return
        
    # Si llega hasta aquí, todo está bien. Procesamos.
    print(f"✅ DEBUG_EVENT: Match encontrado! Verificando TXID: {event.message.text.strip()}")
    
    order_info = WAITING_FOR_TXID.pop(event.chat_id)
    txid = event.message.text.strip()
    
    await event.respond("🔍 <b>Verifying transaction via Binance...</b>", parse_mode='html')
    
    success, status_msg = verify_payment(txid, order_info['amount_crypto'], order_info['symbol'])

    if success:
        await db.create_order(order_info['order_id'], txid, event.chat_id, order_info['product_key'], order_info['usd_price'])
        await event.respond(f"✅ <b>PAYMENT CONFIRMED!</b>\n\n🚀 Your product:\n{order_info['product_url']}", parse_mode='html')
    else:
        WAITING_FOR_TXID[event.chat_id] = order_info
        await event.respond(f"❌ <b>Validation Failed:</b> {status_msg}.", parse_mode='html')