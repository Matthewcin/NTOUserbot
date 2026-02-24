import asyncio
import random
import traceback
import uuid
from datetime import datetime, timezone
from telethon import events
from database import db
import config
from .crypto_utils import crypto_check
from handlers.utils import can_run_command

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

    wallet_data = await db.get_wallet(symbol)
    if not wallet_data:
        await reply_or_edit(event, f"❌ Wallet for {symbol} not configured.")
        return

    usd_price_base = float(product['price_usd'])
    random_cents = round(random.uniform(0.01, 0.15), 2)
    usd_price = round(usd_price_base + random_cents, 2)
    
    crypto_price = crypto_check.get_crypto_price(symbol)
    amount_crypto = round(usd_price / crypto_price, 8)
    
    order_id = str(uuid.uuid4())[:8]

    explorer_url = "https://mempool.space" if symbol == 'BTC' else "https://blockchair.com/litecoin"

    order_msg = (
        f"💳 <b>PAYMENT INSTRUCTIONS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 <b>Item:</b> {product['display_name']}\n"
        f"💵 <b>Total:</b> ${usd_price} USD\n"
        f"💰 <b>Send EXACTLY:</b> <code>{amount_crypto}</code> {symbol}\n\n"
        f"📍 <b>Address ({wallet_data['network']}):</b>\n<code>{wallet_data['address']}</code>\n\n"
        f"🔍 <a href='{explorer_url}'><b>[ OPEN EXPLORER ]</b></a>\n\n"
        f"⚠️ <b>Reply to this message ONLY with the TXID (Hash).</b>"
    )

    if event.out:
        await event.delete()
        await event.client.send_message(event.chat_id, order_msg, parse_mode='html')
    else:
        await event.reply(order_msg, parse_mode='html')

    try:
        async with event.client.conversation(event.chat_id, timeout=600) as conv:
            response = await conv.get_response()
            txid = response.text.strip()
            
            await event.respond("🔍 **Verifying transaction on the blockchain...**")
            
            now = datetime.now(timezone.utc)
            
            success = False
            amount = 0
            confs = 0
            note = ""

            if symbol == 'BTC':
                success, amount, confs, note = crypto_check.check_btc(txid, wallet_data['address'], now)
            elif symbol == 'LTC':
                success, amount, confs, note = crypto_check.check_ltc(txid, wallet_data['address'], now)
            else:
                await event.respond("❌ Only BTC/LTC are supported for auto-verification right now.")
                return

            if success and amount >= (amount_crypto * 0.98):
                await db.create_order(
                    order_id, 
                    txid, 
                    event.chat_id, 
                    product_key, 
                    usd_price
                )

                await event.respond(
                    f"✅ **PAYMENT CONFIRMED!**\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"💰 Received: {amount} {symbol}\n"
                    f"⏳ Confirmations: {confs}\n\n"
                    f"🚀 Your product:\n{product.get('file_url', 'Contact the Admin to receive your product.')}"
                )
            else:
                await event.respond(f"❌ **Validation Failed:** {note}")

    except asyncio.TimeoutError:
        await event.respond("⏰ Order expired. If you already paid, contact the admin with your TXID.")
