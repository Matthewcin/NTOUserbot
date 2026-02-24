import asyncio
from telethon import events
from database import db
import config
from .crypto_utils import crypto_check

async def handler_list(event):
    if not event.out and not event.is_private: return
    
    try:
        if not db.pool:
            await event.edit("❌ Error: DB Disconnected.")
            return

        async with db.pool.acquire() as conn:
            rows = await conn.fetch("SELECT key_name, display_name, price_usd FROM products")
        
        if not rows:
            await event.edit("📂 **EMPTY CATALOG**")
            return
        
        msg = "🛒 **AVAILABLE PRODUCTS**\n\n"
        for row in rows:
            msg += f"🔹 <b>{row['display_name']}</b>\n"
            msg += f"   ├ Key: <code>{row['key_name']}</code>\n"
            msg += f"   └ Price: ${row['price_usd']}\n\n"
            
        msg += "ℹ️ Use <code>.info [key]</code> for details.\n"
        msg += "💳 Use <code>.buy [key] [BTC/LTC]</code> to purchase."
        
        await event.edit(msg, parse_mode='html')
        
    except Exception as e:
        await event.edit(f"❌ Error: {e}")

async def handler_info(event):
    if not event.out and not event.is_private: return
    args = event.message.text.split()
    if len(args) < 2:
        await event.edit("ℹ️ Usage: `.info [key]`")
        return
        
    key = args[1].lower().strip()
    product = await db.get_product(key)
    
    if not product:
        await event.edit(f"❌ Product `{key}` not found.")
        return
            
    msg = (
        f"📦 <b>{product['display_name']}</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"💰 <b>Price:</b> ${product['price_usd']} USD\n"
        f"🔑 <b>Key:</b> <code>{product['key_name']}</code>\n\n"
        f"📝 <b>Description:</b>\n{product.get('description', 'No desc')}\n\n"
        f"🛒 Buy: <code>.buy {key} [SYMBOL]</code>"
    )
    await event.edit(msg, parse_mode='html')

async def handler_buy(event):
    if not event.out and not event.is_private: return
    
    args = event.message.text.split()
    if len(args) < 3:
        await event.edit("❌ **Usage:** `.buy [product_key] [SYMBOL]`\nExample: `.buy premium btc`")
        return
    
    product_key = args[1].lower()
    symbol = args[2].upper()
    
    product = await db.get_product(product_key)
    if not product:
        await event.edit(f"❌ Product `{product_key}` not found.")
        return

    wallet_data = await db.get_wallet(symbol)
    if not wallet_data:
        await event.edit(f"❌ Wallet for {symbol} not configured.")
        return

    # Calcular cantidad en Crypto
    usd_price = float(product['price_usd'])
    crypto_price = crypto_check.get_crypto_price(symbol)
    amount_crypto = round(usd_price / crypto_price, 8)

    order_msg = (
        f"💳 <b>PAYMENT INSTRUCTIONS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 <b>Item:</b> {product['display_name']}\n"
        f"💵 <b>Total:</b> ${usd_price} USD\n"
        f"💰 <b>Send:</b> <code>{amount_crypto}</code> {symbol}\n\n"
        f"📍 <b>Address ({wallet_data['network']}):</b>\n<code>{wallet_data['address']}</code>\n\n"
        f"⚠️ <b>After sending, reply to THIS message with ONLY the TXID (Hash).</b>"
    )

    sent_msg = await event.edit(order_msg, parse_mode='html')

    # Sistema de espera de TXID
    try:
        async with event.client.conversation(event.chat_id, timeout=600) as conv:
            response = await conv.get_response()
            txid = response.text.strip()
            
            await event.respond("🔍 **Verifying transaction...**")
            
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            
            success = False
            if symbol == 'BTC':
                success, amount, confs, note = crypto_check.check_btc(txid, wallet_data['address'], now)
            elif symbol == 'LTC':
                success, amount, confs, note = crypto_check.check_ltc(txid, wallet_data['address'], now)
            else:
                await event.respond("❌ Only BTC/LTC supported for auto-check.")
                return

            if success and amount >= (amount_crypto * 0.98): # Margen 2%
                await event.respond(
                    f"✅ **PAYMENT DETECTED!**\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"💰 Amount: {amount} {symbol}\n"
                    f"⏳ Confs: {confs}\n\n"
                    f"🚀 Your product: {product.get('file_url', 'Check with Admin')}"
                )
            else:
                await event.respond(f"❌ **Validation Failed:** {note}")

    except asyncio.TimeoutError:
        await event.respond("⏰ Order expired. If you paid, contact admin.")
