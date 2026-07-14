import asyncio
import random
import uuid
import io
import qrcode
from collections import defaultdict
from telethon import events
from database import db
from handlers.utils import can_run_command
from binance_api import get_coin_price, get_deposit_address, verify_payment

WAITING_FOR_TXID = {}

async def reply_or_edit(event, text, **kwargs):
    # Si no se envía un parse_mode específico, forzamos HTML por defecto
    if 'parse_mode' not in kwargs:
        kwargs['parse_mode'] = 'html'
        
    if event.out:
        await event.edit(text, **kwargs)
    else:
        await event.reply(text, **kwargs)

# --- 1. LIST PRODUCT CATALOG ---
async def handler_list(event):
    if not await can_run_command(event): return
    try:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch("SELECT key_name, display_name, price_usd FROM products")
        if not rows: await reply_or_edit(event, "📂 <b>EMPTY CATALOG</b>"); return
        
        msg = "🛒 <b>AVAILABLE PRODUCTS</b>\n\n"
        for row in rows:
            msg += f"🔹 <b>{row['display_name']}</b> | Key: <code>{row['key_name']}</code> | Price: ${row['price_usd']}\n"
        await reply_or_edit(event, msg)
    except Exception as e:
        await reply_or_edit(event, f"❌ Error: {e}")

# --- 2. PRODUCT INFO ---
async def handler_info(event):
    if not await can_run_command(event): return
    args = event.message.text.split()
    if len(args) < 2: await reply_or_edit(event, "ℹ️ Usage: <code>.info [key]</code>"); return
    
    key = args[1].lower().strip()
    product = await db.get_product(key)
    if not product: await reply_or_edit(event, f"❌ Product <code>{key}</code> not found."); return
    
    msg = (f"📦 <b>{product['display_name']}</b>\n"
           f"💰 <b>Price:</b> ${product['price_usd']} USD\n"
           f"🔑 <b>Key:</b> <code>{product['key_name']}</code>\n\n"
           f"🛒 Buy: <code>.buy {key} [SYMBOL] [NETWORK]</code>")
    await reply_or_edit(event, msg)

# --- 3. LIST WALLETS ---
async def handler_wallets(event):
    if not await can_run_command(event): return
    async with db.pool.acquire() as conn:
        rows = await conn.fetch("SELECT symbol, network, address FROM wallets ORDER BY symbol, network")
    if not rows: await reply_or_edit(event, "❌ No wallets configured."); return
    
    grouped = defaultdict(list)
    for r in rows:
        grouped[r['symbol']].append(r)
    
    msg = "🌐 <b>AVAILABLE WALLETS</b>\n\n"
    for symbol, wallets in grouped.items():
        msg += f"💰 <b>{symbol}</b>\n"
        for w in wallets:
            msg += f"   ├ <b>{w['network']}</b>:\n   └ <code>{w['address']}</code>\n"
        msg += "\n"
    await reply_or_edit(event, msg)

# --- 4. BUY HANDLER ---
async def handler_buy(event):
    if not await can_run_command(event): return
    
    if event.chat_id in WAITING_FOR_TXID:
        await reply_or_edit(event, "❌ <b>You already have an active order.</b>\nReply to the payment message with <code>CANCEL</code> to cancel the previous one.")
        return

    args = event.message.text.split()
    if len(args) < 3:
        await reply_or_edit(event, "❌ <b>Usage:</b> <code>.buy [key] [SYMBOL] [NETWORK]</code>", parse_mode='html')
        return
    
    product_key, symbol = args[1].lower(), args[2].upper()
    network = args[3].upper() if len(args) > 3 else None
    
    # Check available networks in DB
    async with db.pool.acquire() as conn:
        available_nets = await conn.fetch("SELECT network FROM wallets WHERE symbol = $1", symbol)
    
    if not available_nets:
        await reply_or_edit(event, f"❌ No configuration found for <b>{symbol}</b>.", parse_mode='html')
        return

    # If multiple networks exist and user didn't select one, show menu
    if len(available_nets) > 1 and not network:
        msg = f"Available Networks for <b>{symbol}</b>:\n\n"
        for row in available_nets:
            net = row['network']
            msg += f"{net}; <code>.buy {product_key} {symbol} {net}</code>\n"
        await reply_or_edit(event, msg, parse_mode='html')
        return
    
    # If only one exists, auto-select it
    if len(available_nets) == 1 and not network:
        network = available_nets[0]['network']

    product = await db.get_product(product_key)
    if not product: await reply_or_edit(event, f"❌ Product <code>{product_key}</code> not found.", parse_mode='html'); return

    # Get address using validated network
    wallet = await db.get_wallet_by_network(symbol, network)
    if not wallet: 
        await reply_or_edit(event, f"❌ No wallet configuration found for {symbol} {network}", parse_mode='html')
        return
    
    address = wallet['address']
    # If tag is needed, fetch it here or include in wallet table
    tag = wallet.get('tag', "") 

    crypto_price = 1.0 if symbol in ['USDT', 'USDC'] else get_coin_price(f"{symbol}USDT")
    usd_price = round(float(product['price_usd']) + round(random.uniform(0.01, 0.15), 2), 2)
    amount_crypto = round(usd_price / crypto_price, 8)
    
    qr = qrcode.make(address)
    bio = io.BytesIO(); bio.name = 'qr.png'; qr.save(bio, 'PNG'); bio.seek(0)
    
    order_msg = (f"💳 <b>PAYMENT INSTRUCTIONS</b>\n"
                 f"📦 <b>Item:</b> {product['display_name']}\n"
                 f"💰 <b>Send:</b> <code>{amount_crypto}</code> {symbol} via {network}\n"
                 f"📍 <b>Address:</b> <code>{address}</code>\n"
                 f"⚠️ <b>Reply with TXID or CANCEL.</b>")

    sent_msg = await event.client.send_file(event.chat_id, bio, caption=order_msg, parse_mode='html')
    WAITING_FOR_TXID[event.chat_id] = {
        'order_id': str(uuid.uuid4())[:8], 'product_key': product_key, 'product_url': product.get('file_url'),
        'symbol': symbol, 'amount_crypto': amount_crypto, 'usd_price': usd_price, 'message_id': sent_msg.id
    }

# --- 5. VERIFY TXID ---
async def handler_txid(event):
    if event.chat_id not in WAITING_FOR_TXID: return
    reply_to = await event.get_reply_message()
    if not reply_to: return
    
    order_info = WAITING_FOR_TXID[event.chat_id]
    if reply_to.id != order_info['message_id']: return
    
    text = event.message.text.strip()
    
    if text.upper() == "CANCEL":
        WAITING_FOR_TXID.pop(event.chat_id)
        await event.reply("✅ Order Cancelled Successfully.")
        return
    
    if await db.is_txid_used(text): await event.reply("❌ This TXID was already used."); return

    msg = await event.respond("🔍 <b>Verifying...</b>", parse_mode='html')
    success, status_msg, received = verify_payment(text, order_info['amount_crypto'], order_info['symbol'])

    if success:
        await db.log_order(order_info['order_id'], text, event.chat_id, order_info['product_key'], order_info['usd_price'], order_info['symbol'], 'confirmed')
        await msg.edit(f"✅ <b>ORDER CONFIRMED!</b>\n{order_info['product_url']}", parse_mode='html')
        WAITING_FOR_TXID.pop(event.chat_id)
    else:
        await db.log_order(order_info['order_id'], text, event.chat_id, order_info['product_key'], order_info['usd_price'], order_info['symbol'], 'failed')
        await msg.edit(f"❌ <b>Failed:</b> {status_msg}. If you sent the money, wait a few seconds and Resend TXID.", parse_mode='html')