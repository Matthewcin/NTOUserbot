from telethon import events
from database import db

async def handler_secret_menu(event):
    await event.delete()
    await event.client.send_message("me", 
        "🕵️‍♂️ <b>SECRET PANEL</b>\n━━━━━━━━━━━━━━━━\n"
        "🔸 <code>.add key|Name|$$|Desc</code>\n🔸 <code>.edit key field value</code>\n"
        "🔸 <code>.del key</code>\n🔸 <code>.status edit svb [url]</code>", parse_mode='html')

async def handler_add(event):
    try:
        args = event.pattern_match.group(1).split('|')
        if len(args) < 3: return await event.delete()
        k, n, p = args[0].strip().lower(), args[1].strip(), float(args[2].strip())
        d = args[3].strip() if len(args) > 3 else "No description"
        l = args[4].strip() if len(args) > 4 else "N/A"
        
        async with db.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO products (key_name, display_name, price_usd, description, file_url) 
                VALUES ($1, $2, $3, $4, $5)""", k, n, p, d, l)
        await event.delete()
        await event.client.send_message("me", f"Added: {n}")
    except Exception as e:
        await event.delete()
        await event.client.send_message("me", f"Error: {e}")

async def handler_del(event):
    key = event.pattern_match.group(1).strip().lower()
    success = await db.delete_product(key)
    await event.delete()
    await event.client.send_message("me", f"Deleted: {key}" if success else "Not found")

async def handler_edit(event):
    try:
        args = event.pattern_match.group(1).split()
        if len(args) < 3: return await event.delete()
        success = await db.update_product(args[0].lower(), args[1].lower(), " ".join(args[2:]))
        await event.delete()
        await event.client.send_message("me", "Updated" if success else "Failed")
    except: await event.delete()
