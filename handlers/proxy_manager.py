from telethon import events, errors

# ID de Tyras
TYRAS_ID = 5632906275

# Nota: Asumo que ya tienes una función load_proxies y save_proxies 
# (puedes ponerlas aquí o importarlas)
PROXIES_FILE = "proxies.json"

def load_proxies():
    import json
    if not os.path.exists(PROXIES_FILE): return []
    with open(PROXIES_FILE, "r") as f:
        try: return json.load(f)
        except: return []

def save_proxies(proxies):
    import json
    with open(PROXIES_FILE, "w") as f:
        json.dump(proxies, f)

async def handler_addproxy(event):
    if event.sender_id != TYRAS_ID:
        return
        
    await event.respond("✅ Send the list of proxy codes now (one per line):")
    
    try:
        # Usamos conversation para esperar la respuesta en el mismo chat
        async with event.client.conversation(event.sender_id) as conv:
            response = await conv.get_response(timeout=60)
            codes = [c.strip() for c in response.text.split('\n') if c.strip()]
            
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
        args = event.pattern_match.group(1)
        count = int(args) if args else 1
        
        proxies = load_proxies()
        if len(proxies) < count:
            await event.respond(f"❌ Not enough proxies! Only {len(proxies)} available.")
            return
            
        given = proxies[:count]
        remaining = proxies[count:]
        save_proxies(remaining)
        
        # Formato monoespaciado como pediste
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
