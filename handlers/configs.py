from telethon import events
from database import db

# MAPA DE ESTADOS (Colores)
STATUS_MAP = {
    'working': '🟢',
    'ok': '🟢',
    'fix': '🟠',
    'needsfix': '🟠',
    'updated': '🔵',
    'fixed': '🔵',
    'dead': '🔴',
    'rip': '🔴',
    'checking': '⚪',
    'check': '⚪',
    'remade': '🟣',
    'new': '🟣'
}

# --- 1. COMANDO .CFGLIST (La lista maestra) ---
async def handler_cfglist(event):
    if not event.out: return

    configs = await db.get_all_configs()
    
    if not configs:
        await event.edit("📭 **No configs found.** Use `.addcfg` to add one.")
        return

    # Agrupar por categorías
    grouped = {}
    for conf in configs:
        cat = conf['category']
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(conf)

    # Orden de visualización preferido
    order = ['STREAMING', 'GAMING', 'EDUCATION', 'ADULT', 'FOOD', 'VPN', 'SHOP', 'UNSORTED', 'PRIVATE']
    
    # Primero borramos el mensaje del comando ".cfglist"
    await event.delete()

    # Enviamos un mensaje por cada categoría para que no sea un bloque gigante
    for cat in order:
        if cat in grouped:
            msg = f"📂 **{cat} CONFIGS**\n\n"
            for conf in grouped[cat]:
                price_tag = f" - {conf['price']}" if conf['price'] else ""
                msg += f"{conf['status']} {conf['name']}{price_tag}\n"
            
            # Enviar mensaje al chat
            await event.respond(msg)
    
    # Enviar las categorías que no estén en la lista de orden (personalizadas)
    for cat in grouped:
        if cat not in order:
            msg = f"📂 **{cat} CONFIGS**\n\n"
            for conf in grouped[cat]:
                price_tag = f" - {conf['price']}" if conf['price'] else ""
                msg += f"{conf['status']} {conf['name']}{price_tag}\n"
            await event.respond(msg)


# --- 2. COMANDO .ADDCFG ---
async def handler_addcfg(event):
    # Sintaxis: .addcfg <GROUP> <NAME> [PRICE]
    # Ej: .addcfg STREAMING Disney+
    # Ej: .addcfg PRIVATE Roblox $200
    if not event.out: return

    args = event.message.text.split(maxsplit=2)
    if len(args) < 3:
        await event.edit("❌ Use: `.addcfg <GROUP> <NAME> [PRICE]`\nEx: `.addcfg STREAMING Disney+`")
        return

    category = args[1].upper()
    
    # Manejar precio opcional
    remaining = args[2]
    # Si el usuario puso precio, intentamos separarlo. 
    # Estrategia: Si hay un espacio al final, asumimos que lo último es el precio si tiene $ o USD
    parts = remaining.rsplit(' ', 1)
    
    name = remaining
    price = ""

    # Detección simple de precio
    if len(parts) > 1:
        possible_price = parts[1]
        if '$' in possible_price or 'USD' in possible_price.upper() or possible_price.isdigit():
            name = parts[0]
            price = parts[1]

    if await db.add_config(category, name, price):
        await event.edit(f"✅ Added **{name}** to **{category}**.")
    else:
        await event.edit(f"❌ Error. Maybe **{name}** already exists in **{category}**?")


# --- 3. COMANDO .DELCFG ---
async def handler_delcfg(event):
    # Sintaxis: .delcfg <GROUP> <NAME>
    if not event.out: return

    args = event.message.text.split(maxsplit=2)
    if len(args) < 3:
        await event.edit("❌ Use: `.delcfg <GROUP> <NAME>`")
        return

    category = args[1]
    name = args[2]

    if await db.del_config(category, name):
        await event.edit(f"🗑 Deleted **{name}** from **{category}**.")
    else:
        await event.edit(f"❌ Config **{name}** not found in **{category}**.")


# --- 4. COMANDO .CFGSTATUS ---
async def handler_cfgstatus(event):
    # Sintaxis: .cfgstatus <GROUP> <NAME> <STATUS>
    # STATUS puede ser: working, fix, dead, check, updated, remade
    if not event.out: return

    args = event.message.text.split()
    if len(args) < 4:
        # Nota: Asumimos que el ÚLTIMO argumento es el status.
        await event.edit(
            "❌ Use: `.cfgstatus <GROUP> <NAME> <STATUS>`\n"
            "Status: working, fix, dead, check, updated, remade"
        )
        return

    category = args[1]
    status_key = args[-1].lower() # La última palabra es el estado
    
    # El nombre es todo lo que hay entre la categoría y el status
    name = " ".join(args[2:-1]) 

    if status_key not in STATUS_MAP:
        await event.edit("❌ Invalid Status. Use: working, fix, dead, check, updated, remade")
        return

    new_emoji = STATUS_MAP[status_key]

    if await db.update_config_status(category, name, new_emoji):
        await event.edit(f"✅ Status updated for **{name}**: {new_emoji}")
    else:
        await event.edit(f"❌ Config **{name}** not found in **{category}**.")


# --- 5. COMANDO .EDITCFG (Precio) ---
async def handler_editcfg(event):
    # Sintaxis: .editcfg <GROUP> <NAME> <NEW_PRICE>
    if not event.out: return

    args = event.message.text.split()
    if len(args) < 4:
        await event.edit("❌ Use: `.editcfg <GROUP> <NAME> <PRICE>`")
        return

    category = args[1]
    price = args[-1] # Último arg es el precio
    name = " ".join(args[2:-1])

    if await db.update_config_price(category, name, price):
        await event.edit(f"✅ Price updated for **{name}**: {price}")
    else:
        await event.edit(f"❌ Config **{name}** not found.")
