import requests
import asyncio
from telethon import events
import config
from database import db
# No necesitamos can_run_command para el chequeo estricto de admin, usaremos event.out

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

# 👇 CAMBIO: Delay por defecto aumentado a 6 segundos
async def temp_message(event, text, delay=6):
    msg = await event.respond(text, parse_mode='md')
    await asyncio.sleep(delay)
    await msg.delete()

# --- REDEEM ---
async def handler_redeem(event):
    args = event.pattern_match.group(1)
    await event.delete() # Borrado instantáneo del mensaje del usuario

    if not args:
        await temp_message(event, "❌ Usage: `.redeem [API_KEY]`")
        return

    api_key = args.strip()
    user_id = event.sender_id
    
    # 1. Validaciones locales
    existing_key = await db.get_license(user_id)
    if existing_key:
        # No mostramos la key que ya tiene, solo avisamos
        await temp_message(event, "⚠️ You already have a key assigned.")
        return

    if await db.is_key_redeemed(api_key):
        await temp_message(event, "❌ This key is already in use.")
        return

    # Mensaje de espera (se borra rápido luego)
    wait_msg = await event.respond("🔄 Processing...")

    # 2. Verificar en Servidor OB
    user_data, status = ob_api_request('GET', f"users/{api_key}")

    if status != 200:
        await wait_msg.delete()
        await temp_message(event, "❌ **Invalid Key.** Check spelling.")
        return

    # 3. Canjear
    if await db.redeem_license(user_id, api_key):
        default_ip = "127.102.23.52"
        groups = user_data.get('groups', [])
        update_data = {"key": api_key, "iPs": [default_ip], "groups": groups}
        
        _, up_status = ob_api_request('PUT', f"users/{api_key}", update_data)
        
        await wait_msg.delete()
        
        if up_status in [200, 204]:
            # MENSAJE LIMPIO: Sin key, sin IP, solo confirmación
            await temp_message(event, "✅ **SUCCESS!** License activated.")
        else:
            await temp_message(event, "⚠️ License activated, but IP reset failed.")
    else:
        await wait_msg.delete()
        await temp_message(event, "❌ **System Error.** Try again.")

# --- CHANGE IP ---
async def handler_changeip(event):
    args = event.pattern_match.group(1)
    await event.delete() # Borrado instantáneo

    if not args:
        await temp_message(event, "❌ Usage: `.changeip [NEW_IP]`")
        return

    parts = args.split()
    
    # 🛑 MODO ADMIN (2 Argumentos)
    if len(parts) >= 2:
        if not event.out:
            await temp_message(event, "⛔ **Access Denied.**")
            return

        search_input = parts[0].strip()
        new_ip = parts[1].strip()
        
        full_key = await db.search_license_by_partial(search_input)
        
        if full_key is None:
            await temp_message(event, "❌ Admin: Key not found in DB.")
            return
        elif full_key == "AMBIGUOUS":
            await temp_message(event, "⚠️ Admin: Multiple matches found.")
            return
            
        user_data, status = ob_api_request('GET', f"users/{full_key}")
        if status != 200:
            await temp_message(event, "❌ Admin: Invalid Key on Server.")
            return
            
        groups = user_data.get('groups', [])
        update_data = {"key": full_key, "iPs": [new_ip], "groups": groups}
        
        _, up_status = ob_api_request('PUT', f"users/{full_key}", update_data)
        
        if up_status in [200, 204]:
            # MENSAJE LIMPIO ADMIN: Solo confirmamos que se hizo
            await temp_message(event, f"✅ **ADMIN:** IP Updated for user.")
        else:
            await temp_message(event, "❌ **ADMIN:** Update Failed.")
        return

    # 👤 MODO USUARIO (1 Argumento)
    new_ip = parts[0].strip()
    user_id = event.sender_id

    api_key = await db.get_license(user_id)
    if not api_key:
        await temp_message(event, "❌ License not found.")
        return

    can_change = await db.can_change_ip(user_id)
    if can_change is not True:
        await temp_message(event, f"⏳ **Cooldown Active.** Wait: {can_change}")
        return

    wait_msg = await event.respond("🔄 Processing...")
    
    # Obtenemos datos para no borrar grupos
    user_data, status = ob_api_request('GET', f"users/{api_key}")
    
    if status != 200:
        await wait_msg.delete()
        await temp_message(event, "❌ Server connection error.")
        return

    groups = user_data.get('groups', [])
    update_data = {"key": api_key, "iPs": [new_ip], "groups": groups}
    _, up_status = ob_api_request('PUT', f"users/{api_key}", update_data)
    
    await wait_msg.delete()

    if up_status in [200, 204]:
        await db.update_ip_cooldown(user_id)
        # MENSAJE LIMPIO USUARIO
        await temp_message(event, "✅ **SUCCESS!** Your IP has been updated.")
    else:
        await temp_message(event, "❌ Update failed.")
