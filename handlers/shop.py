import asyncio
import random
import traceback
import uuid
from datetime import datetime, timezone
from telethon import events
from database import db
import config
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
            await reply_or_edit(event, "📂 **EMPTY CATALOG**")
            return
        
        msg = "🛒 **AVAILABLE PRODUCTS**\n\n"
        for row in rows:
            msg += f"🔹 <b>{row['display_name']}</b>\n"
            msg += f"   ├ Key: <code>{row['key_name']}</code>\n"
            msg += f"   └ Price: ${row['price_usd']}\n\n"
            
        msg += "ℹ️ Use <code>.info [key]</code> to see details.\n"
        msg += "💳 Use <code>.buy [key] [BTC/LTC]</code> to buy."
        
        await reply_or_edit(event, msg)
        
    except Exception as e:
        await reply_or_edit(event, f"❌ Error listing products: {e}")
        traceback.print_exc()

async def handler_info(event):
    if not await can_run_command(event): return
    
    args = event.message.text.split()
    if len(args) < 2:
        await reply_or_edit(event, "ℹ️ Usage: `.info [key]`")
        return
        
    key = args[1].lower().strip()
    
    try:
        product = await db.get_product(key)
        
        if not product:
            await reply_or_edit(event, f"❌ Product `{key}` not found.")
            return
            
        msg = (
            f"📦 <b>{product['display_name']}</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"💰 <b>Price:</b> ${product['price_usd']} USD\n"
            f"🔑 <b>Key:</b> <code>{product['key_name']}</code>\n\n"
            f"📝 <b>Description:</b>\n{product.get('description', 'No description')}\n\n"
            f"🛒 Buy: <code>.buy {key} [SYMBOL]</code>"
        )
        await reply_or_edit(event, msg)
        
    except Exception as e:
        await reply_or_edit(event, f"❌ Error: {e}")

async def handler_buy(event):
    if not await can_run_command(event): return
    
    args = event.message.text.split()
    if len(args) < 3:
        await reply_or_edit(event, "❌ **Usage:** `.buy [product_key] [SYMBOL]`\nExample: `.buy premium btc`")
        return
    
    product_key = args[1].lower()
    symbol = args[2].upper()
    
    product = await db.get_product(product_key)
    if not product:
        await reply_or_edit(event, f"❌ Product `{product_key}` not found.")
        return

    if symbol == "USDT":
        crypto_price = 1.0
    else:
        crypto_price = get_coin_price(f"{symbol}USDT")

    if crypto_price <= 0:
        await reply_or_edit(event, f"❌ Error fetching price for {symbol}.")
        return

    address, tag = get_deposit_address(symbol)
    if not address:
        wallet_data = await db.get_wallet(symbol)
        if not wallet_data:
            await reply_or_edit(event, f"❌ Wallet for {symbol} not found on Binance or DB.")
            return
        address = wallet_data['address']
        network = wallet_data['network']
    else:
        network = "Binance"

    usd_price_base = float(product['price_usd'])
    random_cents = round(random.uniform(0.01, 0.15), 2)
    usd_price = round(usd_price_base + random_cents, 2)
    
    amount_crypto = round(usd_price / crypto_price, 8)
    order_id = str(uuid.uuid4())[:8]

    address_str = f"<code>{address}</code>"
    if tag:
        address_str += f"\n🏷 <b>Tag/Memo:</b> <code>{tag}</code>"

    order_msg = (
        f"💳 <b>PAYMENT INSTRUCTIONS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 <b>Item:</b> {product['display_name']}\n"
        f"💵 <b>Total:</b> ${usd_price} USD\n"
        f"💰 <b>Send EXACTLY:</b> <code>{amount_crypto}</code> {symbol}\n\n"
        f"📍 <b>Address ({network}):</b>\n{address_str}\n\n"
        f"⚠️ <b>Reply to this message ONLY with the TXID (Hash).</b>"
    )

    if event.out:
        await event.delete()
        sent_msg = await event.client.send_message(event.chat_id, order_msg, parse_mode='html')
    else:
        sent_msg = await event.reply(order_msg, parse_mode='html')

    WAITING_FOR_TXID[event.chat_id] = {
        'order_id': order_id,
        'product_key': product_key,
        'product_url': product.get('file_url', 'Contact the Admin to receive your product.'),
        'symbol': symbol,
        'amount_crypto': amount_crypto,
        'address': address,
        'usd_price': usd_price,
        'message_id': sent_msg.id,
        'timestamp': datetime.now(timezone.utc)
    }

async def handler_txid(event):
    if event.chat_id not in WAITING_FOR_TXID:
        return
        
    if not event.is_reply:
        return
        
    reply_to = await event.get_reply_message()
    if not reply_to:
        return
        
    order_info = WAITING_FOR_TXID[event.chat_id]
    
    if reply_to.id != order_info['message_id']:
        return
        
    order_info = WAITING_FOR_TXID.pop(event.chat_id)
    txid = event.message.text.strip()
    
    await event.respond("🔍 **Verifying transaction on Binance...**")
    
    symbol = order_info['symbol']
    amount_crypto = order_info['amount_crypto']
    
    success, status_msg = verify_payment(txid, amount_crypto, symbol)

    if success:
        await db.create_order(
            order_info['order_id'], 
            txid, 
            event.chat_id, 
            order_info['product_key'], 
            order_info['usd_price']
        )

        await event.respond(
            f"✅ **PAYMENT CONFIRMED!**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Verified via Binance API\n\n"
            f"🚀 Your product:\n{order_info['product_url']}"
        )
    else:
        WAITING_FOR_TXID[event.chat_id] = order_info
        
        reason = status_msg
        if status_msg == "NOT_FOUND": reason = "Not found on Binance yet"
        elif status_msg == "PENDING": reason = "Pending Network Confirmations"
        elif status_msg == "INSUFFICIENT_AMOUNT": reason = "Insufficient amount sent"
        
        await event.respond(f"❌ **Validation Failed:** {reason}\n\n_Make sure the TXID is correct, or wait a minute and reply again._")