import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

import config
from database import db
from server import start_server
import handlers

if not config.SESSION_STRING:
    print("❌ CRITICAL: MISSING SESSION_STRING")
    exit()

client = TelegramClient(StringSession(config.SESSION_STRING), config.API_ID, config.API_HASH)

async def main():
    print("🌍 1. Starting Web Server...")
    start_server()
    
    print("🔌 2. Connecting Database...")
    await db.connect()
    
    print("🧠 3. Loading Handlers...")
    handlers.register_all_handlers(client)
    
    print("🚀 4. Login to Telegram...")
    await client.start()
    
    try: await client.send_message("me", "🚀 **SYSTEM ONLINE (Split Version 161.0)**")
    except: pass
    
    print("✅ BOT IS RUNNING!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
