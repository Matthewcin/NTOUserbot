import requests
import asyncio
from telethon import events
import config
from database import db
from handlers.utils import can_run_command

# --- Lógica de conexión con API SmarterASP ---
def ob_api_request(method, endpoint, data=None):
    url = f"{config.OB_URL}/api/{endpoint}"
    headers = {
        "Authorization": config.OB_SECRET,
        "Content-Type": "application/json"
    }
    try:
        if method == 'GET':
            r = requests.get(url, headers=headers, timeout=15)
        elif method == 'PUT':
            r = requests.put(url, json=data, headers=headers, timeout=15)
        else:
            return None, 500
            
        if r.status_code == 204:
            return {}, 204
        try:
            return r.json(), r.status_code
        except:
            return r.text, r.status_code
    except Exception as e:
        return str(e), 500

async def temp_message(event, text, delay=3):
    """Envía un mensaje y lo borra a los X segundos"""
    msg = await event.respond(text, parse_mode='md')
    await asyncio.sleep(delay)
    await msg.delete()

# --- HANDLER: .redeem ---
async def handler_redeem(event):
    args = event.pattern_match.group(1)
    # Borramos el mensaje del usuario INSTANTÁNEAMENTE por seguridad
    await event.delete()

    if not args:
        await temp_message(event, "❌ Usage: `.redeem [API_KEY]`")
        return

    api_key = args.strip()
    user_id = event.sender_id
    
    # 1. Verificar duplicados
    existing_key = await db.get_license(user_id)
    if existing_key:
        await temp_message(event, "⚠️ You already have a key assigned.")
        return

    if await db.is_key_redeemed(api_key):
        await temp_message(event, "❌ This key is already in use.")
        return

    # Mensaje temporal de espera
    wait_msg = await event.respond("🔄 Verifying...")

    # 2. Verificar en OB
    user_data, status = ob_api_request('GET', f"users/{api_key}")

    if status != 200:
        await wait_msg.delete()
        await temp_message(event, "❌ **Invalid Key.**")
        return

    # 3. Canjear y Resetear IP
    if await db.redeem_license(user_id, api_key):
        default_ip = "127.102.23.52"
        groups = user_data.get('groups', [])
        
        update_data = {"key": api_key, "iPs": [default_ip], "groups": groups}
        _, up_status = ob_api_request('PUT', f"users/{api_key}", update_data)
        
        await wait_msg.delete()
        if up_status in [200, 204]:
            # MENSAJE GENÉRICO (SIN KEY NI IP)
            await temp_message(event, "✅ **SUCCESS!** License redeemed & IP Reset.")
        else:
            await temp_message(event, "✅ **SUCCESS!** License redeemed (IP Reset failed).")
    else:
        await wait_msg.delete()
        await temp_message(event, "❌ **Database Error.**")

# --- HANDLER: .changeip ---
async def handler_changeip(event):
    args = event.pattern_match.group(1)
    await event.delete() # Borrar mensaje del usuario

    if not args:
        await temp_message(event, "❌ Usage: `.changeip [NEW_IP]`")
        return

    parts = args.split()
    
    # 🕵️‍♂️ MODO ADMIN: .changeip [KEY] [IP]
    # Solo si el usuario es el dueño del bot (checked by can_run_command logic usually, or explicit check)
    is_admin = await can_run_command(event) 
    
    if len(parts) == 2 and is_admin:
        # Modo Dios: Cambiar IP de CUALQUIER Key
        target_key = parts[0].strip()
        new_ip = parts[1].strip()
        
        # Obtener datos para preservar grupos
        user_data, status = ob_api_request('GET', f"users/{target_key}")
        if status != 200:
            await temp_message(event, "❌ Admin: Invalid Key.")
            return
            
        groups = user_data.get('groups', [])
        update_data = {"key": target_key, "iPs": [new_ip], "groups": groups}
        
        _, up_status = ob_api_request('PUT', f"users/{target_key}", update_data)
        
        if up_status in [200, 204]:
            await temp_message(event, "✅ **ADMIN:** Target IP Updated.")
        else:
            await temp_message(event, "❌ **ADMIN:** Update Failed.")
        return

    # 👤 MODO USUARIO: .changeip [IP]
    new_ip = parts[0].strip()
    user_id = event.sender_id

    # 1. Buscar licencia
    api_key = await db.get_license(user_id)
    if not api_key:
        await temp_message(event, "❌ License not found. Use `.redeem`.")
        return

    # 2. CHEQUEO DE COOLDOWN (7 DÍAS)
    can_change = await db.can_change_ip(user_id)
    if can_change is not True:
        # can_change contiene el texto del tiempo restante
        await temp_message(event, f"⏳ **Cooldown Active.** Wait: {can_change}")
        return

    wait_msg = await event.respond("🔄 Updating...")

    # 3. Actualizar en OB
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
        # 4. ACTUALIZAR TIMESTAMP EN DB
        await db.update_ip_cooldown(user_id)
        # MENSAJE GENÉRICO (SIN IP)
        await temp_message(event, "✅ **SUCCESS!** Your IP has been updated.")
    else:
        await temp_message(event, "❌ Failed to update IP.")
