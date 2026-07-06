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

async def handler_buy(event):
    if not await can_run_command(event): return
    args = event.message.text.split()
    
    # Soporte: .buy [key] [SYMBOL] [NETWORK]
    if len(args) < 3:
        await event.reply("❌ <b>Usage:</b> <code>.buy [key] [SYMBOL] [NETWORK]</code>\nEx: <code>.buy disney USDT TRC20</code>", parse_mode='html')
        return
    
    product_key = args[1].lower()
    symbol = args[2].upper()
    network = args[3].upper() if len(args) > 3 else None
    
    product = await db.get_product(product_key)
    if not product:
        await event.reply(f"❌ Product <code>{product_key}</code> not found.", parse_mode='html')
        return

    # 1. Obtener dirección
    address, tag = get_deposit_address(symbol, network=network)
    
    # Si Binance no la da, buscamos en DB local
    if not address:
        wallet = await db.get_wallet_by_network(symbol, network) if network else await db.get_wallet(symbol)
        if not wallet:
            await event.reply(f"❌ No wallet found for <b>{symbol}</b> {f'({network})' if network else ''}", parse_mode='html')
            return
        address, tag = wallet['address'], ""
        network = wallet['network'] # Usamos la red de la DB

    # 2. Calcular precio
    crypto_price = 1.0 if symbol in ['USDT', 'USDC'] else get_coin_price(f"{symbol}USDT")
    usd_price = round(float(product['price_usd']) + round(random.uniform(0.01, 0.15), 2), 2)
    amount_crypto = round(usd_price / crypto_price, 8)
    
    # 3. Generar QR
    qr = qrcode.make(address)
    bio = io.BytesIO(); bio.name = 'qr.png'; qr.save(bio, 'PNG'); bio.seek(0)
    
    # 4. Mensaje claro con la RED
    order_msg = (f"💳 <b>PAYMENT INSTRUCTIONS</b>\n"
                 f"📦 <b>Item:</b> {product['display_name']}\n"
                 f"💵 <b>Total:</b> ${usd_price} USD\n"
                 f"💰 <b>Send:</b> <code>{amount_crypto}</code> {symbol}\n"
                 f"🌐 <b>Network:</b> <code>{network or 'Mainnet'}</code>\n\n"
                 f"📍 <b>Address:</b> <code>{address}</code>"
                 + (f"\n🏷 <b>Tag:</b> <code>{tag}</code>" if tag else "") +
                 f"\n\n⚠️ <b>Reply to this message ONLY with your TXID.</b>")

    sent_msg = await event.client.send_file(event.chat_id, bio, caption=order_msg, parse_mode='html')

    WAITING_FOR_TXID[event.chat_id] = {
        'order_id': str(uuid.uuid4())[:8], 'product_key': product_key,
        'product_url': product.get('file_url', 'Admin contact needed'),
        'symbol': symbol, 'amount_crypto': amount_crypto, 'usd_price': usd_price,
        'message_id': sent_msg.id
    }

async def handler_txid(event):
    if event.chat_id not in WAITING_FOR_TXID: return
    reply_to = await event.get_reply_message()
    if not reply_to: return
    
    order_info = WAITING_FOR_TXID[event.chat_id]
    if reply_to.id != order_info['message_id']: return
    
    txid = event.message.text.strip()
    
    # Anti-fraude
    if await db.is_txid_used(txid):
        await event.respond("❌ <b>Error:</b> This TXID is already used.", parse_mode='html')
        return

    msg = await event.respond("🔍 <b>Verifying transaction...</b>", parse_mode='html')
    success, status_msg, received = verify_payment(txid, order_info['amount_crypto'], order_info['symbol'])

    if success:
        await db.log_order(order_info['order_id'], txid, event.chat_id, order_info['product_key'], order_info['usd_price'], order_info['symbol'], 'confirmed')
        await msg.edit(f"✅ <b>PAYMENT CONFIRMED!</b>\n\n🚀 Your product:\n{order_info['product_url']}", parse_mode='html')
        WAITING_FOR_TXID.pop(event.chat_id)
    else:
        await db.log_order(order_info['order_id'], txid, event.chat_id, order_info['product_key'], order_info['usd_price'], order_info['symbol'], 'failed')
        error_text = f"❌ <b>Validation Failed:</b> {status_msg}"
        if status_msg == "INSUFFICIENT_AMOUNT":
            error_text += f"\n📉 <b>Received:</b> {received} {order_info['symbol']}"
        await msg.edit(error_text + f"\n\n🆔 <code>{txid}</code>", parse_mode='html')