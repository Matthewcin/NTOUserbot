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
    """Replica la lógica exacta de tu config SilverBullet"""
    # 1. Uppercase y Replace espacios por guiones
    a2 = username.upper().replace(" ", "-")
    
    # 2. Base64 Encode (con el salt -hashsecurity)
    raw_b = f"{a2}-hashsecurity"
    b_b64 = base64.b64encode(raw_b.encode('utf-8')).decode('utf-8')
    
    # 3. SHA256 Hash del string Base64
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
        "🔸 <code>.add / .del / .edit</code> » Shop\n"
        "🔸 <code>.status edit svb [url]</code>", 
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

    # Creamos el usuario en la API automáticamente (Upsert)
    payload = {
        "username": generated_key,
        "password": "123", # Dummy pass
        "key": generated_key,
        "iPs": ["0.0.0.0"],
        "groups": []
    }
    
    _, status = _api_request('PUT', f"users/{generated_key}", payload)

    status_icon = "✅" if status in [200, 201, 204] else "⚠️"
    
    msg = (
        f"✅ <b>KEY GENERATED</b>\n"
        f"👤 User: <code>{username.upper()}</code>\n"
        f"🔑 Key: <code>{generated_key}</code>\n"
        f"🔒 Mask: <code>{masked_key}</code>\n"
        f"📡 API Status: {status_icon} ({status})"
    )
    await event.client.send_message("me", msg, parse_mode='html')


# --- 2. ADD GROUP ---
async def handler_addgroup(event):
    if not event.out: return
    args = event.pattern_match.group(1)
    await event.delete()

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

    # Obtener datos de DB (Cooldown) usando SQL directo para no editar database.py
    db_user_id = None
    cooldown_info = "Unknown (No Telegram Link)"
    
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


# --- 5. SHOP HANDLERS ---
async def handler_add(event):
    if not event.out: return
    try:
        args = event.pattern_match.group(1).split('|')
        if len(args) < 3: 
            await event.delete()
            return await event.client.send_message("me", "Error: .add key|Name|Price|Desc")
        
        k, n, p = args[0].strip().lower(), args[1].strip(), float(args[2].strip())
        d = args[3].strip() if len(args) > 3 else "No description"
        l = args[4].strip() if len(args) > 4 else "N/A"

        async with db.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO products (key_name, display_name, price_usd, description, file_url) 
                   VALUES ($1, $2, $3, $4, $5)""",
                k, n, p, d, l
            )
        await event.delete()
        await event.client.send_message("me", f"Added: {n}")
    except Exception as e:
        await event.delete()
        await event.client.send_message("me", f"DB Error: {e}")

async def handler_del(event):
    if not event.out: return
    key = event.pattern_match.group(1).strip().lower()
    success = await db.delete_product(key)
    await event.delete()
    await event.client.send_message("me", f"Deleted: {key}" if success else f"Not found: {key}")

async def handler_edit(event):
    if not event.out: return
    try:
        args = event.pattern_match.group(1).split()
        if len(args) < 3:
            await event.delete()
            return await event.client.send_message("me", "Usage: .edit key field value")
        key, field = args[0].lower(), args[1].lower()
        value = " ".join(args[2:])
        success = await db.update_product(key, field, value)
        await event.delete()
        await event.client.send_message("me", f"Updated: {key}" if success else "Failed.")
    except Exception as e:
        await event.delete()
        await event.client.send_message("me", f"Error: {e}")

# --- 6. WARN HANDLER ---
async def handler_warn(event):
    if not event.out: return

    args = event.pattern_match.group(1)
    
    if not args:
        await event.delete()
        await event.client.send_message("me", "❌ Usage: `.warn [Message]` or `.warn delete`")
        return

    msg = args.strip()

    if msg.lower() == "delete":
        await db.set_setting('global_warn', '')
        await event.delete()
        await event.client.send_message("me", "✅ Warning removed.")
    else:
        await db.set_setting('global_warn', msg)
        await event.delete()
        await event.client.send_message("me", f"✅ Warning set:\n`{msg}`")
