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
                await event.client.send_message('myConfigCloud', f"🎁 <b>New Stock Alert!</b> {len(codes)} new Proxy codes have been added. Get yours now!", reply_to=3832, link_preview=False, parse_mode='html')
            except Exception as e:
                await response.respond(f"⚠️ Added but failed to notify group: {e}")
            
            event.client.remove_event_handler(capture_proxies)

    event.client.add_event_handler(capture_proxies, events.NewMessage(from_users=event.sender_id))

async def handler_giveproxy(event):
    match = event.pattern_match
    if not match or len(match.groups()) < 1:
        msg = await event.reply("❌ **Usage:** `.giveproxy <NUMBER>`")
        if event.out: await event.delete()
        return

    try:
        count = int(match.group(1).strip())
        proxies = await db.get_and_remove_proxies(count)
        
        if not proxies:
            error_msg = "❌ **No proxies available in database.**"
            if event.out:
                await event.edit(error_msg)
            else:
                await event.reply(error_msg)
            return
            
        result_text = "\n".join(proxies)
        success_msg = f"✅ **Here are your {count} proxies:**\n\n`{result_text}`"
        
        if event.out:
            await event.edit(success_msg)
        else:
            await event.reply(success_msg)
            
    except ValueError:
        msg = await event.reply("❌ **Error:** Please provide a valid number.")
        if event.out: await event.delete()
    except Exception as e:
        msg = await event.reply(f"❌ **Error:** {str(e)}")
        if event.out: await event.delete()
