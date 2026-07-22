from telethon import events
from database import db

AUTHORIZED_IDS = [5632906275, 934491540, 8863568013]

async def handler_addproxy(event):
    if event.sender_id not in AUTHORIZED_IDS:
        return
        
    await event.respond("✅ Send the list of proxy codes now (one per line):")

    async def capture_proxies(response):
        if response.sender_id == event.sender_id and response.id != event.id:
            codes = [c.strip() for c in response.text.split('\n') if c.strip()]
            
            await db.add_proxies(codes)
            total_proxies = await db.get_proxies_count()
            
            await response.respond(f"📦 Successfully added {len(codes)} codes! Total in stock: {total_proxies}")
            
            try:
                await event.client.send_message('myConfigCloud2', f"🎁 <b>New Stock Alert!</b> {len(codes)} new Proxy codes have been added. Get yours now!", reply_to=33, link_preview=False, parse_mode='html')
            except Exception as e:
                await response.respond(f"⚠️ Added but failed to notify group: {e}")
            
            event.client.remove_event_handler(capture_proxies)

    event.client.add_event_handler(capture_proxies, events.NewMessage(from_users=event.sender_id))

async def handler_giveproxy(event):
    if event.sender_id not in AUTHORIZED_IDS:
        return
    
    try:
        args = event.pattern_match.group(1)
        count = int(args) if args else 1
        
        total_available = await db.get_proxies_count()
        if total_available < count:
            await event.respond(f"❌ Not enough proxies! Only {total_available} available.")
            return
            
        given = await db.get_and_remove_proxies(count)
        
        code_str = "\n".join([f"`{c}`" for c in given])
        
        msg = (
            f"Here's your {count} GB of Premium Residential Proxies!\n"
            f"[To claim them please register here](https://proxy.sb/?ref=YMMZ2D49)\n\n"
            f"then go to https://proxy.sb/dashboard/claim and there you can claim your {count} Codes:\n\n"
            f"{code_str}"
        )
        
        await event.respond(msg, parse_mode='md')
    except Exception as e:
        await event.respond(f"❌ Error: {e}")
