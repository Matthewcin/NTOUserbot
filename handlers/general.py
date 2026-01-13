from telethon import events
from handlers.utils import can_run_command

# --- HELP MENU ---
async def handler_help(event):
    if not await can_run_command(event): return
    await event.reply("🆘 <b>HELP MENU</b>\nType <code>.cmds</code> to see available commands.", parse_mode='html')

# --- COMMAND LIST (UPDATED) ---
async def handler_cmds(event):
    if not await can_run_command(event): return
    
    # 1. Descripción del Bot
    intro = (
        "🤖 <b>CONFIG CLOUD ASSISTANT</b>\n"
        "<i>I am an automated Userbot designed to manage Config Cloud services, "
        "process secure payments, and manage OpenBullet licenses 24/7.</i>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    # 2. Comandos de Tienda
    store = (
        "🛒 <b>STORE & PAYMENTS</b>\n"
        "🔹 <code>.list</code> » View full catalog\n"
        "🔹 <code>.info [item]</code> » Product details\n"
        "🔹 <code>.buy</code> » Open purchase menu\n"
        "🔹 <code>.buy [item]</code> » Generate Invoice\n\n"
    )

    # 3. Comandos de Licencias (OB)
    licenses = (
        "🔑 <b>LICENSE MANAGER</b>\n"
        "🔹 <code>.redeem [key]</code> » Activate new license\n"
        "🔹 <code>.changeip [ip]</code> » Update IP (7d cooldown)\n\n"
    )

    # 4. Comandos de Sistema
    system = (
        "⚙️ <b>SYSTEM & UTILS</b>\n"
        "🔹 <code>.status</code> » Server & Database health\n"
        "🔹 <code>.status check [svb/ob2]</code> » Deep debug\n"
        "🔹 <code>.request [text]</code> » Send message to Admin\n"
        "🔹 <code>.urldebug [url]</code> » Test link formats"
    )

    # Unimos todo
    full_msg = intro + store + licenses + system
    
    await event.reply(full_msg, parse_mode='html')

# --- REQUEST HANDLER ---
async def handler_request(event):
    if not await can_run_command(event): return
    arg = event.pattern_match.group(1)
    if not arg: return await event.reply("Usage: .request config amazon")
    await event.reply(f"✅ Request received: {arg}")

# --- URL DEBUG HANDLER ---
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
