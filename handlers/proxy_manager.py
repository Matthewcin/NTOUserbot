from telethon import events
from database import db

AUTHORIZED_IDS = [5632906275, 934491540]

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
    
    match = event.pattern_match
    if not match or not match.group(1):
        msg = await event.reply("❌ **Usage:** `.giveproxy <NUMBER>`")
        if event.out: await event.delete()
        return

    try:
        count = int(match.group(1).strip())
        
        total_available = await db.get_proxies_count()
        if total_available < count:
            error_msg = f"❌ Not enough proxies! Only {total_available} available."
            if event.out: await event.edit(error_msg)
            else: await event.respond(error_msg)
            return
            
        given = await db.get_and_remove_proxies(count)
        
        code_str = "\n".join([f"`{c}`" for c in given])
        
        msg = (
            f"🌐 **PREMIUM RESIDENTIAL PROXIES**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Here's your `{count}` codes of Premium Residential Proxies!\n"
            f"[To claim them please register here](https://proxy.sb/?ref=YMMZ2D49)\n\n"
            f"Then go to https://proxy.sb/dashboard/claim and there you can claim your codes:\n\n"
            f"{code_str}"
        )
        
        if event.out:
            await event.edit(msg, parse_mode='markdown', link_preview=False)
        else:
            await event.respond(msg, parse_mode='markdown', link_preview=False)
            
    except ValueError:
        msg = await event.reply("❌ **Error:** Please provide a valid number.")
        if event.out: await event.delete()
    except Exception as e:
        msg = await event.reply(f"❌ Error: {e}")
        if event.out: await event.delete()
