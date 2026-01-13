import hashlib
import base64
import requests
import json
import qrcode
import io
from telethon import events
import config
from database import db

# ==========================================
# 🛠️ HERRAMIENTAS INTERNAS
# ==========================================

def _api_request(method, endpoint, data=None):
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
    if not text or len(str(text)) < 10: return text
    s = str(text)
    return f"{s[:visible_start]}••••{s[-visible_end:]}"

def generate_sb_key(username):
    a2 = username.upper().replace(" ", "-")
    raw_b = f"{a2}-hashsecurity"
    b_b64 = base64.b64encode(raw_b.encode('utf-8')).decode('utf-8')
    c_hash = hashlib.sha256(b_b64.encode('utf-8')).hexdigest()
    return f"{a2}-{c_hash}"

async def generate_qr_message(event, address, network, amount_text, is_preview=False):
    """Función auxiliar para generar QR"""
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(address)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    bio = io.BytesIO()
    bio.name = 'qr.png'
    img.save(bio, 'PNG')
    bio.seek(0)

    caption = (
        f"<code>{address}</code>\n\n"
        f"PLEASE SEND <code>{amount_text}</code> via <code>{network}</code>"
    )
    
    target = "me" if is_preview else event.chat_id
    
    if is_preview:
        caption = "🔍 <b>PREVIEW MODE (Not Saved)</b>\n\n" + caption

    await event.client.send_file(target, bio, caption=caption, parse_mode='html')

# ==========================================
# 👮‍♂️ HANDLERS DE ADMIN
# ==========================================

async def handler_secret_menu(event):
    await event.delete()
    await event.client.send_message("me", 
        "🕵️‍♂️ <b>ADMIN PANEL v3</b>\n━━━━━━━━━━━━━━━━\n"
        "🔸 <code>.generate [user]</code> » Create Key\n"
        "🔸 <code>.apicheck [key]</code> » User Info\n"
        "🔸 <code>.addgroup [grp] [key]</code> » Add GRP\n"
        "🔸 <code>.delgroup [grp] [key]</code> » Del GRP\n"
        "🔸 <code>.warn [msg]</code> » Global Alert\n"
        "🔸 <code>.pay [SYM] [AMT]</code> » Generate Payment\n"
        "🔸 <code>.payadd [SYM] [ADDR]</code> » Add Wallet\n"
        "🔸 <code>.paylist</code> » List Wallets", 
        parse_mode='html')

# --- CRYPTO HANDLERS ---

# 1. PAY (Generar QR desde DB)
async def handler_pay(event):
    if not event.out: return
    args = event.pattern_match.group(1)
    await event.delete()

    if not args:
        return await event.client.send_message("me", "❌ Usage: `.pay [SYMBOL] [AMOUNT]`")

    parts = args.split()
    if len(parts) < 2:
         return await event.client.send_message("me", "❌ Format: `.pay [SYMBOL] [AMOUNT]`")

    symbol = parts[0].upper()
    amount = parts[1]
    
    wallet = await db.get_wallet(symbol)
    if not wallet:
         return await event.client.send_message("me", f"❌ Wallet <b>{symbol}</b> not found. Use .payadd first.", parse_mode='html')
    
    await generate_qr_message(event, wallet['address'], wallet['network'], f"${amount} USD")

# 2. PAYADD (Agregar Wallet)
async def handler_payadd(event):
    if not event.out: return
    args = event.pattern_match.group(1)
    await event.delete()

    if not args:
        return await event.client.send_message("me", "❌ Usage: `.payadd [SYM] [ADDRESS] [NETWORK]`")

    parts = args.split()
    if len(parts) < 3:
         return await event.client.send_message("me", "❌ Missing args. `.payadd BTC 1A1z... Bitcoin`")

    symbol = parts[0].upper()
    address = parts[1]
    network = " ".join(parts[2:])

    if await db.set_wallet(symbol, address, network):
        await event.client.send_message("me", f"✅ Wallet <b>{symbol}</b> added/updated!", parse_mode='html')
    else:
        await event.client.send_message("me", "❌ Database Error.")

# 3. PAYEDIT (Editar Wallet - Alias de Payadd)
async def handler_payedit(event):
    await handler_payadd(event)

# 4. PAYCHECK (Preview)
async def handler_paycheck(event):
    if not event.out: return
    args = event.pattern_match.group(1)
    await event.delete()

    if not args:
        return await event.client.send_message("me", "❌ Usage: `.paycheck [SYM] [ADDR] [NET]`")

    parts = args.split()
    if len(parts) < 2:
        symbol = parts[0].upper()
        w = await db.get_wallet(symbol)
        if w:
            await event.client.send_message("me", 
                f"🔎 <b>WALLET INFO: {symbol}</b>\n"
                f"📍 Addr: <code>{w['address']}</code>\n"
                f"🔗 Net: <code>{w['network']}</code>", parse_mode='html')
        else:
            await event.client.send_message("me", f"❌ {symbol} not found.")
        return

    symbol = parts[0].upper()
    address = parts[1]
    network = " ".join(parts[2:]) if len(parts) > 2 else "Default"
    
    await generate_qr_message(event, address, network, "PREVIEW AMOUNT", is_preview=True)

# 5. PAYLIST (Listar todas)
async def handler_paylist(event):
    if not event.out: return
    await event.delete()
    
    wallets = await db.get_all_wallets()
    if not wallets:
        return await event.client.send_message("me", "📂 No wallets configured.")

    msg = "💰 <b>CONFIGURED WALLETS</b>\n━━━━━━━━━━━━━━━━\n"
    for w in wallets:
        msg += (
            f"🔹 <b>{w['symbol']}</b> ({w['network']})\n"
            f"   <code>{w['address']}</code>\n\n"
        )
    
    await event.client.send_message("me", msg, parse_mode='html')


# --- OB / ADMIN HANDLERS ---

async def handler_generate(event):
    if not event.out: return
    args = event.pattern_match.group(1)
    await event.delete()
    if not args: return await event.client.send_message("me", "❌ Usage: `.generate [username]`")
    username = args.strip()
    generated_key = generate_sb_key(username)
    masked_key = mask_text(generated_key, 10, 8)
    payload = {"username": generated_key, "password": "123", "key": generated_key, "iPs": ["0.0.0.0"], "groups": []}
    _, status = _api_request('PUT', f"users/{generated_key}", payload)
    status_icon = "✅" if status in [200, 201, 204] else "⚠️"
    msg = f"✅ <b>KEY GENERATED</b>\n👤 User: <code>{username.upper()}</code>\n🔑 Key: <code>{generated_key}</code>\n🔒 Mask: <code>{masked_key}</code>\n📡 Status: {status_icon} ({status})"
    await event.client.send_message("me", msg, parse_mode='html')

async def handler_addgroup(event):
    if not event.out: return
    args = event.pattern_match.group(1)
    await event.delete()
    try:
        parts = args.split()
        if len(parts) < 2: raise ValueError
        group_name, api_key = parts[0].strip(), parts[1].strip()
    except: return await event.client.send_message("me", "❌ Usage: `.addgroup [GROUP] [KEY]`")
    user_data, status = _api_request('GET', f"users/{api_key}")
    if status != 200: return await event.client.send_message("me", "❌ API Error.")
    current_groups = user_data.get('groups', [])
    if group_name in current_groups: return await event.client.send_message("me", f"⚠️ Group exists.")
    current_groups.append(group_name)
    update_payload = {"key": api_key, "iPs": user_data.get('iPs', []), "groups": current_groups}
    _, up_status = _api_request('PUT', f"users/{api_key}", update_payload)
    if up_status in [200, 204]: await event.client.send_message("me", f"✅ Added <b>{group_name}</b>", parse_mode='html')
    else: await event.client.send_message("me", f"❌ API Error: {up_status}")

async def handler_delgroup(event):
    if not event.out: return
    args = event.pattern_match.group(1)
    await event.delete()
    try:
        parts = args.split()
        if len(parts) < 2: raise ValueError
        group_name, api_key = parts[0].strip(), parts[1].strip()
    except: return await event.client.send_message("me", "❌ Usage: `.delgroup [GROUP] [KEY]`")
    user_data, status = _api_request('GET', f"users/{api_key}")
    if status != 200: return await event.client.send_message("me", "❌ User not found.")
    current_groups = user_data.get('groups', [])
    if group_name not in current_groups: return await event.client.send_message("me", f"⚠️ Not in group.")
    current_groups.remove(group_name)
    update_payload = {"key": api_key, "iPs": user_data.get('iPs', []), "groups": current_groups}
    _, up_status = _api_request('PUT', f"users/{api_key}", update_payload)
    if up_status in [200, 204]: await event.client.send_message("me", f"🗑️ Removed <b>{group_name}</b>", parse_mode='html')
    else: await event.client.send_message("me", f"❌ API Error: {up_status}")

# 👇 ACTUALIZADO: Envía al chat actual (event.respond) en lugar de 'me'
async def handler_apicheck(event):
    if not event.out: return
    api_key = event.pattern_match.group(1)
    await event.delete()
    if not api_key: return await event.respond("❌ Usage: `.apicheck [KEY]`")
    
    user_data, status = _api_request('GET', f"users/{api_key}")
    if status != 200: return await event.respond("❌ Key not found on Server.")
    
    db_user_id = None
    cooldown_info = "Unknown"
    if db.pool:
        row = await db.pool.fetchrow("SELECT user_id FROM licenses WHERE api_key = $1", api_key)
        if row:
            db_user_id = row['user_id']
            can_change = await db.can_change_ip(db_user_id)
            cooldown_info = "✅ Ready" if can_change is True else f"⏳ {can_change}"

    msg = (f"🕵️‍♂️ <b>INFO (CENSORED)</b>\n"
           f"🔑 <code>{mask_text(api_key, 8, 8)}</code>\n"
           f"🌍 IPs: {', '.join([mask_text(i,3,2) for i in user_data.get('iPs', [])])}\n"
           f"👥 Grps: {', '.join(user_data.get('groups', []))}\n"
           f"⏲️ Cool: {cooldown_info}\n"
           f"👤 TG: {db_user_id if db_user_id else 'N/A'}")
    
    # Se envía al chat donde se usó el comando
    await event.respond(msg, parse_mode='html')

# --- SHOP & WARN ---
async def handler_add(event):
    if not event.out: return
    try:
        args = event.pattern_match.group(1).split('|')
        k, n, p = args[0].lower(), args[1], float(args[2])
        d = args[3] if len(args)>3 else "No desc"
        l = args[4] if len(args)>4 else "N/A"
        async with db.pool.acquire() as c:
            await c.execute("INSERT INTO products (key_name, display_name, price_usd, description, file_url) VALUES ($1,$2,$3,$4,$5)", k,n,p,d,l)
        await event.delete(); await event.client.send_message("me", f"Added: {n}")
    except: await event.delete()

async def handler_del(event):
    if not event.out: return
    await db.delete_product(event.pattern_match.group(1).strip().lower())
    await event.delete(); await event.client.send_message("me", "Deleted.")

async def handler_edit(event):
    if not event.out: return
    try:
        a = event.pattern_match.group(1).split()
        await db.update_product(a[0].lower(), a[1].lower(), " ".join(a[2:]))
        await event.delete(); await event.client.send_message("me", "Updated.")
    except: await event.delete()

async def handler_warn(event):
    if not event.out: return
    msg = event.pattern_match.group(1).strip()
    if msg.lower() == "delete": await db.set_setting('global_warn', ''); await event.client.send_message("me", "Warn removed.")
    else: await db.set_setting('global_warn', msg); await event.client.send_message("me", "Warn set.")
    await event.delete()
