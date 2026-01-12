import requests
import time
from telethon import events
from database import db
from handlers.utils import can_run_command

async def handler_status(event):
    if not await can_run_command(event): return
    args = event.pattern_match.group(1)

    # 1. ADMIN EDIT
    if args and args.startswith('edit') and event.out:
        parts = args.split()
        if len(parts) < 3: return await event.edit("Usage: .status edit svb [url]")
        target, new_url = parts[1].lower(), parts[2]
        
        if target == 'svb': await db.set_setting('url_svb', new_url)
        elif target == 'ob2': await db.set_setting('url_ob2', new_url)
        await event.edit(f"✅ {target.upper()} URL Updated:\n`{new_url}`")
        return

    # 2. DEBUG CHECK
    if args and args.startswith('check'):
        parts = args.split()
        if len(parts) < 2: return await event.reply("Usage: <code>.status check svb</code>", parse_mode='html')
        target = parts[1].lower()
        key = 'url_svb' if target == 'svb' else 'url_ob2' if target == 'ob2' else None
        
        if not key: return await event.reply("Invalid target.")
        url = await db.get_setting(key)
        if not url: return await event.reply(f"⚠️ {target.upper()} Not Configured")
        
        msg = await event.reply(f"🔍 Checking {target.upper()}...")
        try:
            r = requests.get(url, timeout=5)
            status_text = "ONLINE" if r.status_code in [200, 401] else "ISSUES"
            code = r.status_code
        except:
            code = "UNREACHABLE"
            status_text = "DOWN"

        await msg.edit(
            f"🔎 <b>DEBUG CHECK: {target.upper()}</b>\n🔗 <b>URL:</b> <code>{url}</code>\n"
            f"📡 <b>Code:</b> <code>{code}</code>\n📊 <b>Status:</b> {status_text}",
            parse_mode='html'
        )
        return

    # 3. PUBLIC STATUS
    if not db.pool: return await event.reply("DB Disconnected")
    url_svb = await db.get_setting('url_svb')
    url_ob2 = await db.get_setting('url_ob2')
    
    msg = await event.reply("Checking Status...")
    
    def check(url):
        if not url: return "Not Configured"
        try:
            start = time.time()
            r = requests.get(url, timeout=5)
            ping = int((time.time() - start) * 1000)
            if r.status_code in [200, 401]: return f"✅ <b>ONLINE</b> ({ping}ms)"
            return f"❌ <b>OFFLINE</b> (Code: {r.status_code})"
        except: return "❌ <b>DOWN</b>"

    await msg.edit(
        "📊 <b>SYSTEM STATUS</b>\n━━━━━━━━━━━━━━━━\n"
        f"🤖 <b>Bot System:</b> ✅ Online\n🛡️ <b>Database:</b> ✅ Connected\n"
        "━━━━━━━━━━━━━━━━\n"
        f"☁️ <b>SVB Cloud:</b> {check(url_svb)}\n☁️ <b>OB2 Cloud:</b> {check(url_ob2)}\n",
        parse_mode='html'
    )
