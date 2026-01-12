from telethon import events

# Importamos todo
from .welcome import handler_welcome, handler_hello
from .general import handler_help, handler_cmds, handler_request, handler_urldebug
from .status import handler_status
from .shop import handler_list, handler_info, handler_buy
from .admin import handler_secret_menu, handler_add, handler_del, handler_edit
from .openbullet import handler_redeem, handler_changeip  # <--- NUEVO

def register_all_handlers(client):
    # Welcome
    client.add_event_handler(handler_welcome, events.ChatAction)
    client.add_event_handler(handler_hello, events.NewMessage(pattern=r'\.hello'))
    
    # General
    client.add_event_handler(handler_help, events.NewMessage(pattern=r'\.help'))
    client.add_event_handler(handler_cmds, events.NewMessage(pattern=r'\.cmds'))
    client.add_event_handler(handler_request, events.NewMessage(pattern=r'\.request(?:\s+(.*))?'))
    client.add_event_handler(handler_urldebug, events.NewMessage(pattern=r'\.urldebug(?:\s+(.*))?'))
    
    # Status
    client.add_event_handler(handler_status, events.NewMessage(pattern=r'\.status(?:\s+(.*))?'))
    
    # Shop
    client.add_event_handler(handler_list, events.NewMessage(pattern=r'\.list'))
    client.add_event_handler(handler_info, events.NewMessage(pattern=r'\.info(?:\s+(.*))?'))
    client.add_event_handler(handler_buy, events.NewMessage(pattern=r'\.buy(?:\s+(.*))?'))
    
    # OpenBullet (NUEVO)
    client.add_event_handler(handler_redeem, events.NewMessage(pattern=r'\.redeem(?:\s+(.*))?'))
    client.add_event_handler(handler_changeip, events.NewMessage(pattern=r'\.changeip(?:\s+(.*))?'))
    
    # Admin
    client.add_event_handler(handler_secret_menu, events.NewMessage(outgoing=True, pattern=r'\.2284230134'))
    client.add_event_handler(handler_add, events.NewMessage(outgoing=True, pattern=r'\.add\s+(.*)'))
    client.add_event_handler(handler_del, events.NewMessage(outgoing=True, pattern=r'\.del\s+(.*)'))
    client.add_event_handler(handler_edit, events.NewMessage(outgoing=True, pattern=r'\.edit\s+(.*)'))
