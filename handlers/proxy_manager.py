import json
import os
from telethon import events

# ID de Tyras para restricción de acceso
TYRAS_ID = 5632906275
PROXIES_FILE = "proxies.json"

def load_proxies():
    """Lee los proxies desde el archivo JSON."""
    if not os.path.exists(PROXIES_FILE):
        return []
    with open(PROXIES_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return []

def save_proxies(proxies):
    """Guarda los proxies en el archivo JSON."""
    with open(PROXIES_FILE, "w") as f:
        json.dump(proxies, f, indent=4)

async def handler_addproxy(event):
    if event.sender_id != TYRAS_ID:
        return
        
    await event.respond("✅ Send the list of proxy codes now (one per line):")
    
    try:
        # Iniciamos la conversación para esperar la respuesta
        async with event.client.conversation(event.sender_id) as conv:
            response = await conv.get_response(timeout=60)
            codes = [c.strip() for c in response.text.split('\n') if c.strip()]
            
            # Cargamos, añadimos y guardamos
            proxies = load_proxies()
            proxies.extend(codes)
            save_proxies(proxies)
            
            await event.respond(f"📦 Successfully added {len(codes)} codes! Total in stock: {len(proxies)}")
            await event.client.send_message('myConfigCloud', f"🎁 <b>New Stock Alert!</b> {len(codes)} new Proxy codes have been added. Get yours now!", parse_mode='html')
    except Exception as e:
        await event.respond(f"❌ Error adding proxies: {e}")

async def handler_giveproxy(event):
    if event.sender_id != TYRAS_ID:
        return
    
    try:
        # Obtenemos la cantidad del comando (ej: .giveproxy 4)
        args = event.pattern_match.group(1)
        count = int(args) if args else 1
        
        proxies = load_proxies()
        if len(proxies) < count:
            await event.respond(f"❌ Not enough proxies! Only {len(proxies)} available.")
            return
            
        # Tomamos los necesarios y guardamos el resto
        given = proxies[:count]
        remaining = proxies[count:]
        save_proxies(remaining)
        
        # Formato de códigos monoespaciados
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
