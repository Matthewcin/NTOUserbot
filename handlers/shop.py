import asyncio
import random
import uuid
import io
import qrcode
from datetime import datetime, timezone
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

async def handler_buy(event):
    if not await can_run_command(event): return
    args = event.message.text.split()
    if len(args) < 3:
        await reply_or_edit(event, "❌ <b>Usage:</b> <code>.buy [key] [SYMBOL]</code>")
        return
    
    product_key = args[1].lower()
    symbol = args[2].upper()
    
    # Alias
    alias = {"LITECOIN": "LTC", "BITCOIN": "BTC", "ETHEREUM": "ETH", "TRON": "TRX", "TETHER": "USDT"}
    symbol = alias.get(symbol, symbol)
    
    product = await db.get_product(product_key)
    if not product:
        await reply_or_edit(event, f"❌ Product <code>{product_key}</code> not found.")
        return

    # Precio
    crypto_price = 1.0 if symbol == "USDT" else get_coin_price(f"{symbol}USDT")
    if crypto_price <= 0:
        await reply_or_edit(event, f"❌ Error: Could not fetch {symbol} price.")
        return

    # Wallet
    address, tag = get_deposit_address(symbol)
    if not address:
        wallet = await db.get_wallet(symbol)
        if not wallet:
            await reply_or_edit(event, f"❌ Wallet for {symbol} not configured.")
            return
        address, tag = wallet['address'], ""
    
    usd_price = round(float(product['price_usd']) + round(random.uniform(0.01, 0.15), 2), 2)
    amount_crypto = round(usd_price / crypto_price, 8)
    
    # Crear QR
    qr = qrcode.make(address)
    bio = io.BytesIO()
    bio.name = 'qr.png'
    qr.save(bio, 'PNG')
    bio.seek(0)
    
    order_msg = (
        f"💳 <b>PAYMENT INSTRUCTIONS</b>\n"
        f"📦 <b>Item:</b> {product['display_name']}\n"
        f"💵 <b>Total:</b> ${usd_price} USD\n"
        f"💰 <b>Send EXACTLY:</b> <code>{amount_crypto}</code> {symbol}\n\n"
        f"📍 <b>Address:</b> <code>{address}</code>"
        + (f"\n🏷 <b>Tag:</b> <code>{tag}</code>" if tag else "") +
        f"\n\n⚠️ <b>Reply to this message ONLY with your TXID.</b>"
    )

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
    # Log de depuración: Si no imprime nada, el handler no está capturando el mensaje
    if event.chat_id not in WAITING_FOR_TXID: return
    
    reply_to = await event.get_reply_message()
    if not reply_to: return
    
    order_info = WAITING_FOR_TXID[event.chat_id]
    if reply_to.id != order_info['message_id']: return
    
    print(f"✅ TXID recibido: {event.message.text.strip()}")
    order_info = WAITING_FOR_TXID.pop(event.chat_id)
    txid = event.message.text.strip()
    
    await event.respond("🔍 <b>Verifying transaction...</b>", parse_mode='html')
    
    success, status_msg = verify_payment(txid, order_info['amount_crypto'], order_info['symbol'])

    if success:
        await db.create_order(order_info['order_id'], txid, event.chat_id, order_info['product_key'], order_info['usd_price'])
        await event.respond(f"✅ <b>PAYMENT CONFIRMED!</b>\n\n🚀 Your product:\n{order_info['product_url']}", parse_mode='html')
    else:
        WAITING_FOR_TXID[event.chat_id] = order_info
        await event.respond(f"❌ <b>Validation Failed:</b> {status_msg}", parse_mode='html')