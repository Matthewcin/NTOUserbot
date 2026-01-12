import uuid
from telethon import events
from database import db
from payments import create_invoice
from handlers.utils import can_run_command

async def handler_list(event):
    if not await can_run_command(event): return
    if not db.pool: return await event.reply("DB Error")
    products = await db.get_all_products()
    msg = "📂 <b>CATALOG</b>\n\n"
    if products:
        for p in products:
            msg += f"🔹 <b>{p['display_name']}</b>\n   💰 ${p['price_usd']} USD | Key: <code>{p['key_name']}</code>\n\n"
    else: msg += "Catalog empty.\n"
    msg += "Type <code>.buy [key]</code> to purchase."
    await event.reply(msg, parse_mode='html')

async def handler_info(event):
    if not await can_run_command(event): return
    arg = event.pattern_match.group(1)
    if not arg: return await event.reply("Usage: <code>.info ebook</code>", parse_mode='html')
    p = await db.get_product(arg.lower())
    if p:
        await event.reply(
            f"📘 <b>INFO: {p['display_name']}</b>\n━━━━━━━━━━━━━━━━\n📝 {p['description']}\n\n"
            f"💵 Price: <b>${p['price_usd']} USD</b>\n👉 To Buy: <code>.buy {p['key_name']}</code>",
            parse_mode='html'
        )
    else: await event.reply("Not found.")

async def handler_buy(event):
    if not await can_run_command(event): return
    if not db.pool: return await event.reply("DB Disconnected")
    key = event.pattern_match.group(1)
    
    # Menu
    if not key:
        products = await db.get_all_products()
        msg = "🛒 <b>PURCHASE MENU</b>\n\n"
        if products:
            for p in products:
                msg += f"🔸 <b>{p['display_name']}</b> (${p['price_usd']})\n   👉 <code>.buy {p['key_name']}</code>\n\n"
        else: msg += "No products."
        return await event.reply(msg, parse_mode='html')

    # Invoice
    try:
        p = await db.get_product(key.strip().lower())
        if not p: return await event.reply("Product not found.")
        
        order_id = str(uuid.uuid4())[:8]
        amount = float(p['price_usd'])
        msg_wait = await event.reply(f"Creating invoice for ${amount}...")
        
        invoice = create_invoice(amount, order_id, f"Buy: {p['display_name']}")
        
        if invoice and invoice.get('url'):
            await db.create_order(order_id, invoice['track_id'], event.sender_id, key, amount)
            link_html = f"<a href='{invoice['url']}'>🔗 PAY NOW - CLICK HERE</a>"
            await msg_wait.edit(
                f"💳 <b>INVOICE GENERATED</b>\n📦 Item: {p['display_name']}\n💵 Total: <b>${amount} USD</b>\n\n"
                f"{link_html}\n\n⏳ Valid for 60m.\nℹ️ Send proof after payment.",
                parse_mode='html', link_preview=False
            )
        else: await msg_wait.edit("❌ Payment Gateway Error (Check Logs)")
    except Exception as e:
        import traceback
        traceback.print_exc()
        await event.reply(f"Error: {e}")
