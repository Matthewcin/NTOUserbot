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

# --- 1. LISTAR PRODUCTOS ---
async def handler_list(event):
    if not await can_run_command(event): return
    try:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch("SELECT key_name, display_name, price_usd FROM products")
        if not rows: await reply_or_edit(event, "📂 <b>CATÁLOGO VACÍO</b>"); return
        
        msg = "🛒 <b>PRODUCTOS DISPONIBLES</b>\n\n"
        for row in rows:
            msg += f"🔹 <b>{row['display_name']}</b> | Key: <code>{row['key_name']}</code> | Price: ${row['price_usd']}\n"
        await reply_or_edit(event, msg)
    except Exception as e:
        await reply_or_edit(event, f"❌ Error: {e}")

# --- 2. INFORMACIÓN DE PRODUCTO ---
async def handler_info(event):
    if not await can_run_command(event): return
    args = event.message.text.split()
    if len(args) < 2: await reply_or_edit(event, "ℹ️ Uso: <code>.info [key]</code>"); return
    
    key = args[1].lower().strip()
    product = await db.get_product(key)
    if not product: await reply_or_edit(event, f"❌ Producto <code>{key}</code> no encontrado."); return
    
    msg = (f"📦 <b>{product['display_name']}</b>\n"
           f"💰 <b>Precio:</b> ${product['price_usd']} USD\n"
           f"🔑 <b>Key:</b> <code>{product['key_name']}</code>\n\n"
           f"🛒 Compra: <code>.buy {key} [SYMBOL] [NETWORK]</code>")
    await reply_or_edit(event, msg)

# --- 3. LISTAR BILLETERAS ---
async def handler_wallets(event):
    if not await can_run_command(event): return
    async with db.pool.acquire() as conn:
        rows = await conn.fetch("SELECT symbol, network, address FROM wallets")
    if not rows: await reply_or_edit(event, "❌ No hay billeteras configuradas."); return
    
    msg = "🌐 <b>FAMOUS WALLETS / NETWORKS</b>\n\n"
    for r in rows:
        msg += f"💰 <b>{r['symbol']}</b> ({r['network']})\n<code>{r['address']}</code>\n\n"
    await reply_or_edit(event, msg)

# --- 4. COMPRAR ---
async def handler_buy(event):
    if not await can_run_command(event): return
    
    # Bloqueo de orden simultánea
    if event.chat_id in WAITING_FOR_TXID:
        await reply_or_edit(event, "❌ <b>Ya tienes una orden activa.</b>\nResponde al mensaje de pago con <code>CANCEL</code> para cancelar la anterior.")
        return

    args = event.message.text.split()
    if len(args) < 3:
        await reply_or_edit(event, "❌ <b>Uso:</b> <code>.buy [key] [SYMBOL] [NETWORK]</code>")
        return
    
    product_key, symbol, network = args[1].lower(), args[2].upper(), (args[3].upper() if len(args) > 3 else None)
    
    product = await db.get_product(product_key)
    if not product: await reply_or_edit(event, f"❌ Product <code>{product_key}</code> not found."); return

    address, tag = get_deposit_address(symbol, network=network)
    if not address:
        wallet = await db.get_wallet_by_network(symbol, network) if network else await db.get_wallet(symbol)
        if not wallet: await reply_or_edit(event, f"❌ No wallet config for {symbol}"); return
        address, tag = wallet['address'], ""
        network = wallet['network']

    crypto_price = 1.0 if symbol in ['USDT', 'USDC'] else get_coin_price(f"{symbol}USDT")
    usd_price = round(float(product['price_usd']) + round(random.uniform(0.01, 0.15), 2), 2)
    amount_crypto = round(usd_price / crypto_price, 8)
    
    qr = qrcode.make(address)
    bio = io.BytesIO(); bio.name = 'qr.png'; qr.save(bio, 'PNG'); bio.seek(0)
    
    order_msg = (f"💳 <b>PAYMENT INSTRUCTIONS</b>\n"
                 f"📦 <b>Item:</b> {product['display_name']}\n"
                 f"💰 <b>Send:</b> <code>{amount_crypto}</code> {symbol} via {network or 'Mainnet'}\n"
                 f"📍 <b>Address:</b> <code>{address}</code>\n"
                 f"⚠️ <b>Reply with TXID or CANCEL.</b>")

    sent_msg = await event.client.send_file(event.chat_id, bio, caption=order_msg, parse_mode='html')
    WAITING_FOR_TXID[event.chat_id] = {
        'order_id': str(uuid.uuid4())[:8], 'product_key': product_key, 'product_url': product.get('file_url'),
        'symbol': symbol, 'amount_crypto': amount_crypto, 'usd_price': usd_price, 'message_id': sent_msg.id
    }

# --- 5. VERIFICAR TXID ---
async def handler_txid(event):
    if event.chat_id not in WAITING_FOR_TXID: return
    reply_to = await event.get_reply_message()
    if not reply_to: return
    
    order_info = WAITING_FOR_TXID[event.chat_id]
    if reply_to.id != order_info['message_id']: return
    
    text = event.message.text.strip()
    
    if text.upper() == "CANCEL":
        WAITING_FOR_TXID.pop(event.chat_id)
        await event.reply("✅ Orden cancelada.")
        return
    
    if await db.is_txid_used(text):
        await event.reply("❌ Este TXID ya fue usado."); return

    msg = await event.respond("🔍 <b>Verificando...</b>", parse_mode='html')
    success, status_msg, received = verify_payment(text, order_info['amount_crypto'], order_info['symbol'])

    if success:
        await db.log_order(order_info['order_id'], text, event.chat_id, order_info['product_key'], order_info['usd_price'], order_info['symbol'], 'confirmed')
        await msg.edit(f"✅ <b>PAGADO!</b>\n{order_info['product_url']}", parse_mode='html')
        WAITING_FOR_TXID.pop(event.chat_id)
    else:
        await db.log_order(order_info['order_id'], text, event.chat_id, order_info['product_key'], order_info['usd_price'], order_info['symbol'], 'failed')
        await msg.edit(f"❌ <b>Falló:</b> {status_msg}. Si enviaste el dinero, espera y vuelve a enviar el TXID.", parse_mode='html')