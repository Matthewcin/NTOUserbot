from telethon import events
from handlers.utils import can_run_command

async def handler_help(event):
    if not await can_run_command(event): return
    await event.reply("🆘 <b>HELP MENU</b>\nType <code>.cmds</code>", parse_mode='html')

async def handler_cmds(event):
    if not await can_run_command(event): return
    await event.reply(
        "🤖 <b>COMMAND LIST</b>\n━━━━━━━━━━━━━━━━\n"
        "🔹 <code>.list</code> » Catalog\n🔹 <code>.info [item]</code> » Details\n"
        "🔹 <code>.buy</code> » Purchase\n🔹 <code>.buy [item]</code> » Invoice\n"
        "🔹 <code>.request [text]</code> » Request\n🔹 <code>.status</code> » Health",
        parse_mode='html'
    )

async def handler_request(event):
    if not await can_run_command(event): return
    arg = event.pattern_match.group(1)
    if not arg: return await event.reply("Usage: .request config amazon")
    await event.reply(f"Request received: {arg}")

async def handler_urldebug(event):
    if not await can_run_command(event): return
    url = event.pattern_match.group(1)
    if not url: return await event.reply("❌ Usage: `.urldebug https://google.com`")
    
    await event.reply("🔍 **TESTING URL FORMATS**")
    await event.reply(f"1. RAW: {url}")
    try: await event.reply(f"2. MARKDOWN: [Click Here]({url})", parse_mode='md')
    except Exception as e: await event.reply(f"2. ERROR: {e}")
    try: await event.reply(f"3. HTML: <a href='{url}'>Click Here</a>", parse_mode='html')
    except Exception as e: await event.reply(f"3. ERROR: {e}")
