import json
import os
from telethon import events

AUTHORIZED_IDS = [5632906275, 934491540]
PROXIES_FILE = "proxies.json"

def load_proxies():
    if not os.path.exists(PROXIES_FILE): return []
    with open(PROXIES_FILE, "r") as f:
        try: return json.load(f)
        except: return []

def save_proxies(proxies):
    with open(PROXIES_FILE, "w") as f:
        json.dump(proxies, f, indent=4)

async def handler_addproxy(event):
    if event.sender_id not in AUTHORIZED_IDS:
        return
        
    await event.respond("✅ Send the list of proxy codes now (one per line):")

    # Definimos una función interna para capturar la respuesta
    async def capture_proxies(response):
        if response.sender_id == event.sender_id:
            codes = [c.strip() for c in response.text.split('\n') if c.strip()]
            proxies = load_proxies()
            proxies.extend(codes)
            save_proxies(proxies)
            
            await response.respond(f"📦 Successfully added {len(codes)} codes! Total in stock: {len(proxies)}")
            await event.client.send_message('myConfigCloud', f"🎁 <b>New Stock Alert!</b> {len(codes)} new Proxy codes added.", parse_mode='html')
            
            # Removemos el handler después de capturar
            event.client.remove_event_handler(capture_proxies)

    # Registramos el handler temporal
    event.client.add_event_handler(capture_proxies, events.NewMessage(from_users=event.sender_id))

async def handler_giveproxy(event):
    if event.sender_id not in AUTHORIZED_IDS:
        return
    
    try:
        args = event.pattern_match.group(1)
        count = int(args) if args else 1
        
        proxies = load_proxies()
        if len(proxies) < count:
            await event.respond(f"❌ Not enough proxies! Only {len(proxies)} available.")
            return
            
        given = proxies[:count]
        remaining = proxies[count:]
        save_proxies(remaining)
        
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
