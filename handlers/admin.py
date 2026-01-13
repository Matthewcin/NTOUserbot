import hashlib
import base64
import requests
import json
from telethon import events
import config
from database import db

# ==========================================
# 🛠️ HERRAMIENTAS INTERNAS (Helpers)
# ==========================================

def _api_request(method, endpoint, data=None):
    """Comunicación interna con SmarterASP para Admin"""
    url = f"{config.OB_URL}/api/{endpoint}"
    headers = {"Authorization": config.OB_SECRET, "Content-Type": "application/json"}
    try:
        if method == 'GET': r = requests.get(url, headers=headers, timeout=10)
        elif method == 'PUT': r = requests.put(url, json=data, headers=headers, timeout=10)
        elif method == 'POST': r = requests.post(url, json=data, headers=headers, timeout=10)
        else: return None, 500
        
        if r.status_code == 204: return {}, 204
        try: return r.json(), r.status_code
        except: return r.text, r.status_code
    except Exception as e: return str(e), 500

def mask_text(text, visible_start=4, visible_end=4):
    """Censura el centro del texto (Ej: USUARIO-701•••3906e2)"""
    if not text or len(str(text)) < 10: return text
    s = str(text)
    return f"{s[:visible_start]}••••{s[-visible_end:]}"

def generate_sb_key(username):
    """Replica la lógica de tu config SilverBullet"""
    # 1. Uppercase y Replace
    a2 = username.upper().replace(" ", "-")
    
    # 2. Base64 Encode (con el salt -hashsecurity)
    raw_b = f"{a2}-hashsecurity"
    b_b64 = base64.b64encode(raw_b.encode('utf-8')).decode('utf-8')
    
    # 3. SHA256 Hash
    # Nota: Si en SB 'InputBase64=TRUE', SB decodifica antes de hashear.
    # Si 'InputBase64=FALSE' (default), hashea el string base64.
    # Asumimos el flujo estándar: Hashear el string resultante del Base64.
    c_hash = hashlib.sha256(b_b64.encode('utf-8')).hexdigest()
    
    # 4. Final Key
    return f"{a2}-{c_hash}"

# ==========================================
# 👮‍♂️ HANDLERS DE ADMIN
# ==========================================

async def handler_secret_menu(event):
    await event.delete()
    await event.client.send_message("me", 
        "🕵️‍♂️ <b>ADMIN PANEL v2</b>\n━━━━━━━━━━━━━━━━\n"
        "🔸 <code>.generate [user]</code> » Create Key\n"
        "🔸 <code>.apicheck [key]</code> » User Info\n"
        "🔸 <code>.addgroup [grp] [key]</code> » Add GRP\n"
        "🔸 <code>.delgroup [grp] [key]</code> » Del GRP\n"
        "🔸 <code>.warn [msg]</code> » Global Alert\n"
        "🔸 <code>.add / .del / .edit</code> » Shop", 
        parse_mode='html')

# --- 1. GENERATE KEY ---
async def handler_generate(event):
    if not event.out: return
    args = event.pattern_match.group(1)
    await event.delete()

    if not args:
        return await event.client.send_message("me", "❌ Usage: `.generate [username]`")

    username = args.strip()
    generated_key = generate_sb_key(username)
    masked_key = mask_text(generated_key, 10, 8)

    # Creamos el usuario en la API automáticamente para que ya funcione
    # IP Default: 0.0.0.0 (esperando redeem)
    payload = {
        "username": generated_key, # En OB API el username suele ser la key
        "password": "123", # Password dummy, la auth es por key
        "key": generated_key,
        "iPs": ["0.0.0.0"],
        "groups": []
    }
    
    # Usamos POST para crear o PUT si ya existe (la API de OB varía, probamos PUT directo a users/key)
    # Normalmente para crear es POST a /api/users, pero SmarterASP OB API suele usar PUT para "Upsert"
    _, status = _api_request('PUT', f"users/{generated_key}", payload)

    msg = (
        f"✅ <b>KEY GENERATED & REGISTERED</b>\n"
        f"👤 User: <code>{username.upper()}</code>\n"
        f"🔑 Key: <code>{generated_key}</code>\n"
        f"🔒 Mask: <code>{masked_key}</code>\n"
        f"📡 API Status: {status}"
    )
    await event.client.send_message("me", msg, parse_mode='html')


# --- 2. ADD GROUP ---
async def handler_addgroup(event):
    if not event.out: return
    args = event.pattern_match.group(1)
    await event.delete()

    # Esperamos formato: .addgroup GRUPO KEY
    try:
        parts = args.split()
        if len(parts) < 2: raise ValueError
        group_name = parts[0].strip()
        api_key = parts[1].strip()
    except:
        return await event.client.send_message("me", "❌ Usage: `.addgroup [GROUP] [KEY]`")

    # 1. Obtener datos actuales
    user_data, status = _api_request('GET', f"users/{api_key}")
    if status != 200:
        return await event.client.send_message("me", "❌ Error fetching user from API.")

    # 2. Modificar grupos
    current_groups = user_data.get('groups', [])
    if group_name in current_groups:
        return await event.client.send_message("me", f"⚠️ Group <code>{group_name}</code> already exists.", parse_mode='html')
    
    current_groups.append(group_name)
    
    # 3. Enviar actualización
    user_data['groups'] = current_groups
    # Asegurar que enviamos la key y las IPs correctamente
    update_payload = {
        "key": api_key,
        "iPs": user_data.get('iPs', []),
        "groups": current_groups
    }
    
    _, up_status = _api_request('PUT', f"users/{api_key}", update_payload)
    
    if up_status in [200, 204]:
        await event.client.send_message("me", f"✅ Added <b>{group_name}</b> to <code>{mask_text(api_key)}</code>", parse_mode='html')
    else:
        await event.client.send_message("me", f"❌ API Error: {up_status}")


# --- 3. DEL GROUP ---
async def handler_delgroup(event):
    if not event.out: return
    args = event.pattern_match.group(1)
    await event.delete()

    try:
        parts = args.split()
        if len(parts) < 2: raise ValueError
        group_name = parts[0].strip()
        api_key = parts[1].strip()
    except:
        return await event.client.send_message("me", "❌ Usage: `.delgroup [GROUP] [KEY]`")

    user_data, status = _api_request('GET', f"users/{api_key}")
    if status != 200: return await event.client.send_message("me", "❌ User not found.")

    current_groups = user_data.get('groups', [])
    if group_name not in current_groups:
        return await event.client.send_message("me", f"⚠️ User doesn't have group <code>{group_name}</code>", parse_mode='html')

    current_groups.remove(group_name)
    
    update_payload = {
        "key": api_key,
        "iPs": user_data.get('iPs', []),
        "groups": current_groups
    }
    
    _, up_status = _api_request('PUT', f"users/{api_key}", update_payload)
    
    if up_status in [200, 204]:
        await event.client.send_message("me", f"🗑️ Removed <b>{group_name}</b> from <code>{mask_text(api_key)}</code>", parse_mode='html')
    else:
        await event.client.send_message("me", f"❌ API Error: {up_status}")


# --- 4. API CHECK (INFO) ---
async def handler_apicheck(event):
    if not event.out: return
    api_key = event.pattern_match.group(1)
    await event.delete()

    if not api_key:
        return await event.client.send_message("me", "❌ Usage: `.apicheck [KEY]`")

    # Obtener datos de API
    user_data, status = _api_request('GET', f"users/{api_key}")
    if status != 200:
        return await event.client.send_message("me", "❌ Key not found on Server.")

    # Obtener datos de DB (Cooldown)
    # Necesitamos el user_id para chequear cooldown, pero aquí buscamos por Key.
    # Buscamos en la tabla licenses a quién pertenece esa key
    db_user_id = None
    cooldown_info = "Unknown (No Telegram Link)"
    
    # Hacemos una query inversa rápida (Key -> UserID)
    if db.pool:
        row = await db.pool.fetchrow("SELECT user_id FROM licenses WHERE api_key = $1", api_key)
        if row:
            db_user_id = row['user_id']
            # Chequear cooldown
            can_change = await db.can_change_ip(db_user_id)
            if can_change is True:
                cooldown_info = "✅ Ready to change"
            else:
                cooldown_info = f"⏳ Wait: {can_change}"

    # Formatear datos
    ips = user_data.get('iPs', [])
    masked_ips = [mask_text(ip, 3, 2) for ip in ips]
    groups = user_data.get('groups', [])
    masked_key = mask_text(api_key, 8, 8)

    msg = (
        f"🕵️‍♂️ <b>USER DETAILS (CENSORED)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔑 <b>Key:</b> <code>{masked_key}</code>\n"
        f"🌍 <b>IPs:</b> {', '.join(masked_ips)}\n"
        f"👥 <b>Groups:</b> {', '.join(groups) if groups else 'None'}\n"
        f"⏲️ <b>Cooldown:</b> {cooldown_info}\n"
        f"👤 <b>TG UserID:</b> <code>{mask_text(db_user_id, 2, 2) if db_user_id else 'N/A'}</code>"
    )
    
    await event.client.send_message("me", msg, parse_mode='html')


# --- HANDLERS SHOP Y WARN (MANTENIDOS) ---
async def handler_add(event):
    # (El código anterior de .add, .del, .edit, .warn VA AQUÍ IGUAL QUE ANTES)
    # Para ahorrar espacio en este mensaje, asumo que copias los handlers anteriores aquí.
    # Si los necesitas completos de nuevo dímelo.
    pass 

async def handler_del(event): pass
async def handler_edit(event): pass
async def handler_warn(event):
    if not event.out: return
    args = event.pattern_match.group(1)
    if not args: return await event.delete()
    msg = args.strip()
    if msg.lower() == "delete":
        await db.set_setting('global_warn', '')
        await event.client.send_message("me", "✅ Warning removed.")
    else:
        await db.set_setting('global_warn', msg)
        await event.client.send_message("me", f"✅ Warning set.")
