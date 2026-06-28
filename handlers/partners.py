from telethon import events

async def handler_bought(event):
    try:
        await event.delete()
    except:
        pass
        
    user = event.pattern_match.group(1)
    products = event.pattern_match.group(2)
    
    product_list = [p.strip() for p in products.split(',') if p.strip()]
    gb_amount = len(product_list)
    
    if gb_amount == 0:
        gb_amount = 1
        
    msg = (
        f"⚡ Deal Claimed! {user} just bought --> {products} and scored {gb_amount}GB of free proxies from ProxySB! 🎁\n\n"
        f"<b><a href='https://proxy.sb/?ref=YMMZ2D49'>Buy today and I'll send you your own promo code/s to claim at Proxy.sb</a></b>\n\n"
        f"Limited codes available! - 1GB of Free Proxies Per Product!"
    )
    
    try:
        await event.client.send_message('myConfigCloud', msg, reply_to=3832, link_preview=False, parse_mode='html')
    except Exception as e:
        await event.respond(f"❌ Error: {str(e)}")
