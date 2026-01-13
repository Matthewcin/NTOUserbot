from telethon import events

from .welcome import handler_welcome, handler_hello
from .general import handler_help, handler_cmds, handler_request, handler_urldebug
from .status import handler_status
from .shop import handler_list, handler_info, handler_buy
# 👇 CORREGIDO: Quitamos handler_setalias de aquí
from .admin import handler_secret_menu, handler_add, handler_del, handler_edit, handler_warn 
from .openbullet import handler_redeem, handler_changeip

def register_all_handlers(client):
    # Welcome
    client.add_event_handler(handler_welcome, events.ChatAction)
    client.add_event_handler(handler_hello, events.NewMessage(pattern=r'(?i)\.hello'))
    
    # General
    client.add_event_handler(handler_help, events.NewMessage(pattern=r'(?i)\.help'))
    client.add_event_handler(handler_cmds, events.NewMessage(pattern=r'(?i)\.cmds'))
    client.add_event_handler(handler_request, events.NewMessage(pattern=r'(?i)\.request(?:\s+(.*))?'))
    client.add_event_handler(handler_urldebug, events.NewMessage(pattern=r'(?i)\.urldebug(?:\s+(.*))?'))
    
    # Status
    client.add_event_handler(handler_status, events.NewMessage(pattern=r'(?i)\.status(?:\s+(.*))?'))
    
    # Shop
    client.add_event_handler(handler_list, events.NewMessage(pattern=r'(?i)\.list'))
    client.add_event_handler(handler_info, events.NewMessage(pattern=r'(?i)\.info(?:\s+(.*))?'))
    client.add_event_handler(handler_buy, events.NewMessage(pattern=r'(?i)\.buy(?:\s+(.*))?'))
    
    # OpenBullet
    client.add_event_handler(handler_redeem, events.NewMessage(pattern=r'(?i)\.redeem(?:\s+(.*))?'))
    client.add_event_handler(handler_changeip, events.NewMessage(pattern=r'(?i)\.changeip(?:\s+(.*))?'))
    
    # Admin
    client.add_event_handler(handler_secret_menu, events.NewMessage(outgoing=True, pattern=r'\.2284230134'))
    client.add_event_handler(handler_add, events.NewMessage(outgoing=True, pattern=r'(?i)\.add\s+(.*)'))
    client.add_event_handler(handler_del, events.NewMessage(outgoing=True, pattern=r'(?i)\.del\s+(.*)'))
    client.add_event_handler(handler_edit, events.NewMessage(outgoing=True, pattern=r'(?i)\.edit\s+(.*)'))
    
    # 👇 CORREGIDO: Solo registramos el WARN, nada de alias
    client.add_event_handler(handler_warn, events.NewMessage(outgoing=True, pattern=r'(?i)\.warn(?:\s+(.*))?'))
