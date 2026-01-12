import requests
import asyncio
from telethon import events
import config
from database import db
from handlers.utils import can_run_command

def ob_api_request(method, endpoint, data=None):
    url = f"{config.OB_URL}/api/{endpoint}"
    headers = {"Authorization": config.OB_SECRET, "Content-Type": "application/json"}
    try:
        if method == 'GET': r = requests.get(url, headers=headers, timeout=15)
        elif method == 'PUT': r = requests.put(url, json=data, headers=headers, timeout=15)
        else: return None, 500
        if r.status_code == 204: return {}, 204
        try: return r.json(), r.status_code
        except: return r.text, r.status_code
    except Exception as e: return str(e), 500

async def temp_message(event, text, delay=3):
    msg = await event.respond(text, parse_mode='md')
    await asyncio.sleep(delay)
    await msg.delete()

# --- REDEEM (Igual que antes) ---
async def handler_redeem(event):
    args = event.pattern_match.group(1)
    await event.delete()

    if not args:
        await temp_message(event, "❌ Usage: `.redeem [API_KEY]`")
        return

    api_key = args.strip()
    user_id = event.sender_id
    
    existing_key = await db.get_license(user_id)
    if existing_key:
        await temp_message(event, "⚠️ You already have a key.")
        return

    if await db.is_key_redeemed(api_key):
        await temp_message(event, "❌ Key already in use.")
        return

    wait_msg = await event.respond("🔄 Verifying...")
    user_data, status = ob_api_request('GET', f"users/{api_key}")

    if status != 200:
        await wait_msg.delete()
        await temp_message(event, "❌ **Invalid Key.**")
        return

    if await db.redeem_license(user_id, api_key):
        default_ip = "127.102.23.52"
        groups = user_data.get('groups', [])
        update_data = {"key": api_key, "iPs": [default_ip], "groups": groups}
        _, up_status = ob_api_request('PUT', f"users/{api_key}", update_data)
        
        await wait_msg.delete()
        if up_status in [200, 204]:
            await temp_message(event, "✅ **SUCCESS!** Redeemed & Reset.")
        else:
            await temp_message(event, "✅ **SUCCESS!** Redeemed (Reset Failed).")
    else:
        await wait_msg.delete()
        await temp_message(event, "❌ **DB Error.**")

# --- CHANGE IP (Con Buscador Inteligente) ---
async def handler_changeip(event):
    args = event.pattern_match.group(1)
    await event.delete()

    if not args:
        await temp_message(event, "❌ Usage: `.changeip [NEW_IP]`")
        return

    parts = args.split()
    is_admin = await can_run_command(event) 
    
    # 🕵️‍♂️ MODO ADMIN: .changeip [PARTIAL_NAME] [IP]
    if len(parts) >= 2 and is_admin:
        # El input es lo que escribió (ej: "virus-nto")
        search_input = parts[0].strip()
        new_ip = parts[1].strip()
        
        # 👇 MAGIA AQUÍ: Buscamos la key completa en la DB
        full_key = await db.search_license_by_partial(search_input)
        
        if full_key is None:
            await temp_message(event, f"❌ Admin: No key matches '{search_input}'")
            return
        elif full_key == "AMBIGUOUS":
            await temp_message(event, f"⚠️ Admin: '{search_input}' matches multiple keys. Be specific.")
            return
            
        # Si encontramos una única key, procedemos con ella
        user_data, status = ob_api_request('GET', f"users/{full_key}")
        if status != 200:
            await temp_message(event, "❌ Admin: Key found in DB but invalid on Server.")
            return
            
        groups = user_data.get('groups', [])
        update_data = {"key": full_key, "iPs": [new_ip], "groups": groups}
        
        _, up_status = ob_api_request('PUT', f"users/{full_key}", update_data)
        
        if up_status in [200, 204]:
            await temp_message(event, f"✅ **ADMIN:** IP Updated for `{search_input}`")
        else:
            await temp_message(event, "❌ **ADMIN:** Update Failed.")
        return

    # 👤 MODO USUARIO: .changeip [IP]
    new_ip = parts[0].strip()
    user_id = event.sender_id

    api_key = await db.get_license(user_id)
    if not api_key:
        await temp_message(event, "❌ No license found.")
        return

    can_change = await db.can_change_ip(user_id)
    if can_change is not True:
        await temp_message(event, f"⏳ **Cooldown:** Wait {can_change}")
        return

    wait_msg = await event.respond("🔄 Updating...")
    user_data, status = ob_api_request('GET', f"users/{api_key}")
    
    if status != 200:
        await wait_msg.delete()
        await temp_message(event, "❌ Server Error.")
        return

    groups = user_data.get('groups', [])
    update_data = {"key": api_key, "iPs": [new_ip], "groups": groups}
    _, up_status = ob_api_request('PUT', f"users/{api_key}", update_data)
    
    await wait_msg.delete()

    if up_status in [200, 204]:
        await db.update_ip_cooldown(user_id)
        await temp_message(event, "✅ **SUCCESS!** IP Updated.")
    else:
        await temp_message(event, "❌ Failed.")
