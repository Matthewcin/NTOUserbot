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
            
        # La API de OB a veces devuelve 204 No Content en Updates
        if r.status_code == 204:
            return {}, 204
            
        try:
            return r.json(), r.status_code
        except:
            return r.text, r.status_code
    except Exception as e:
        return str(e), 500

# --- HANDLER: .redeem ---
async def handler_redeem(event):
    # Cualquiera puede redimir, no usamos can_run_command estricto
    args = event.pattern_match.group(1)
    if not args:
        msg = await event.reply("❌ Usage: `.redeem [API_KEY]`")
        await asyncio.sleep(5)
        await msg.delete()
        await event.delete()
        return

    api_key = args.strip()
    user_id = event.sender_id
    
    # 1. Verificar si el usuario ya tiene una key (opcional, si quieres permitir 1 por usuario)
    existing_key = await db.get_license(user_id)
    if existing_key:
        msg = await event.reply(f"⚠️ You already have a key: `{existing_key}`")
        await asyncio.sleep(5)
        await msg.delete()
        return

    # 2. Verificar si la key ya fue canjeada por otro
    if await db.is_key_redeemed(api_key):
        msg = await event.reply("❌ This key is already redeemed by someone else.")
        await asyncio.sleep(5)
        await msg.delete()
        return

    wait_msg = await event.reply("🔄 Verifying Key with Server...")

    # 3. Consultar a SmarterASP si la key existe
    user_data, status = ob_api_request('GET', f"users/{api_key}")

    if status == 404:
        await wait_msg.edit("❌ **Invalid Key.** Not found on server.")
        return
    elif status != 200:
        await wait_msg.edit(f"❌ **Server Error:** Code {status}")
        return

    # 4. Si es válida, guardamos en Neon y Reseteamos IP
    if await db.redeem_license(user_id, api_key):
        # Reset IP to default
        default_ip = "127.102.23.52"
        # Necesitamos enviar los grupos actuales para no borrarlos
        groups = user_data.get('groups', [])
        
        update_data = {
            "key": api_key,
            "iPs": [default_ip],
            "groups": groups
        }
        
        _, up_status = ob_api_request('PUT', f"users/{api_key}", update_data)
        
        await event.delete() # Borramos el mensaje del usuario con la key
        
        if up_status in [200, 204]:
            await wait_msg.edit(f"✅ **SUCCESS!**\nKey redeemed successfully.\nIP Reset to `{default_ip}`")
        else:
            await wait_msg.edit(f"✅ **SUCCESS!**\nKey redeemed, but IP reset failed (Error {up_status}).")
    else:
        await wait_msg.edit("❌ **Database Error.** Could not save license.")

# --- HANDLER: .changeip ---
async def handler_changeip(event):
    args = event.pattern_match.group(1)
    if not args:
        msg = await event.reply("❌ Usage: `.changeip [NEW_IP]`")
        await asyncio.sleep(5)
        await msg.delete()
        await event.delete()
        return

    new_ip = args.strip()
    user_id = event.sender_id

    # 1. Buscar la key del usuario en Neon
    api_key = await db.get_license(user_id)
    
    if not api_key:
        msg = await event.reply("❌ You don't have a license. Use `.redeem [KEY]` first.")
        await asyncio.sleep(5)
        await msg.delete()
        await event.delete()
        return

    wait_msg = await event.reply("🔄 Updating IP...")

    # 2. Obtener datos actuales (para preservar grupos)
    user_data, status = ob_api_request('GET', f"users/{api_key}")
    
    if status != 200:
        await wait_msg.edit("❌ **Error:** Could not fetch user data from server.")
        return

    # 3. Actualizar IP
    groups = user_data.get('groups', [])
    update_data = {
        "key": api_key,
        "iPs": [new_ip],
        "groups": groups
    }
    
    _, up_status = ob_api_request('PUT', f"users/{api_key}", update_data)
    
    await event.delete()

    if up_status in [200, 204]:
        await wait_msg.edit(f"✅ **IP UPDATED!**\nNew IP: `{new_ip}`")
    else:
        await wait_msg.edit(f"❌ **FAILED:** Server returned code {up_status}")
