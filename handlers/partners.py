from telethon import events

async def handler_bought(event):
    try:
        await event.delete()
    except:
        pass
        
    user = event.pattern_match.group(1)
    products = event.pattern_match.group(2)
    
    msg = (
        f"⚡ Deal Claimed! {user} just bought --> {products} and scored 2GB of free proxies from Proxy.sb! 🎁\n\n"
        f"Buy today and I'll send you your own promo code to claim at https://proxy.sb/?ref=YMMZ2D49\n\n"
        f"Limited codes available!"
    )
    
    try:
        await event.client.send_message('myConfigCloud', msg, reply_to=3832, link_preview=False)
    except Exception as e:
        await event.respond(f"❌ Error: {str(e)}")
