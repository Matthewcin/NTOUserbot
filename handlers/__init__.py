from telethon import events

from .welcome import handler_welcome, handler_hello
from .general import handler_help, handler_cmds, handler_urldebug, handler_guide, handler_testbtn

from .status import handler_status
from .shop import handler_list, handler_info, handler_buy, handler_txid
from .admin import (
    handler_secret_menu, 
    handler_add, handler_del, handler_edit, handler_warn,
    handler_generate, handler_addgroup, handler_delgroup, handler_apicheck,
    handler_pay, handler_payadd, handler_payedit, handler_paylist, handler_paycheck
)
from .openbullet import handler_redeem, handler_changeip

from .queue_system import (
    handler_request, 
    handler_queue, 
    handler_qlist, 
    handler_qa, 
    handler_qs,
    handler_qend,
    handler_qdel
)

from .configs import (
    handler_cfglist,
    handler_addcfg,
    handler_delcfg,
    handler_cfgstatus,
    handler_editcfg
)

def register_all_handlers(client):
    client.add_event_handler(handler_welcome, events.ChatAction)
    client.add_event_handler(handler_hello, events.NewMessage(pattern=r'(?i)\.hello'))
    
    client.add_event_handler(handler_help, events.NewMessage(pattern=r'(?i)\.help'))
    client.add_event_handler(handler_cmds, events.NewMessage(pattern=r'(?i)\.cmds'))
    client.add_event_handler(handler_urldebug, events.NewMessage(pattern=r'(?i)\.urldebug(?:\s+(.*))?'))
    client.add_event_handler(handler_guide, events.NewMessage(pattern=r'(?i)\.guide'))
    client.add_event_handler(handler_testbtn, events.NewMessage(pattern=r'(?i)\.testbtn'))
    
    client.add_event_handler(handler_request, events.NewMessage(pattern=r'(?i)\.request(?:\s+(.*))?'))
    client.add_event_handler(handler_queue, events.NewMessage(pattern=r'(?i)\.(queue|q)$'))
    
    client.add_event_handler(handler_qlist, events.NewMessage(outgoing=True, pattern=r'(?i)\.qlist$'))
    client.add_event_handler(handler_qa, events.NewMessage(outgoing=True, pattern=r'(?i)\.qa$'))
    client.add_event_handler(handler_qs, events.NewMessage(outgoing=True, pattern=r'(?i)\.qs$'))
    client.add_event_handler(handler_qend, events.NewMessage(outgoing=True, pattern=r'(?i)\.qend\s+(.*)'))
    client.add_event_handler(handler_qdel, events.NewMessage(outgoing=True, pattern=r'(?i)\.qdel\s+(.*)'))
    
    client.add_event_handler(handler_status, events.NewMessage(pattern=r'(?i)\.status(?:\s+(.*))?'))
    
    client.add_event_handler(handler_list, events.NewMessage(pattern=r'(?i)\.list'))
    client.add_event_handler(handler_info, events.NewMessage(pattern=r'(?i)\.info(?:\s+(.*))?'))
    client.add_event_handler(handler_buy, events.NewMessage(pattern=r'(?i)\.buy(?:\s+(.*))?'))
    
    client.add_event_handler(handler_txid, events.NewMessage())
    
    client.add_event_handler(handler_redeem, events.NewMessage(pattern=r'(?i)\.redeem(?:\s+(.*))?'))
    client.add_event_handler(handler_changeip, events.NewMessage(pattern=r'(?i)\.changeip(?:\s+(.*))?'))
    
    client.add_event_handler(handler_secret_menu, events.NewMessage(outgoing=True, pattern=r'\.2284230134'))
    client.add_event_handler(handler_add, events.NewMessage(outgoing=True, pattern=r'(?i)\.add\s+(.*)'))
    client.add_event_handler(handler_del, events.NewMessage(outgoing=True, pattern=r'(?i)\.del\s+(.*)'))
    client.add_event_handler(handler_edit, events.NewMessage(outgoing=True, pattern=r'(?i)\.edit\s+(.*)'))
    client.add_event_handler(handler_warn, events.NewMessage(outgoing=True, pattern=r'(?i)\.warn(?:\s+(.*))?'))
    
    client.add_event_handler(handler_generate, events.NewMessage(outgoing=True, pattern=r'(?i)\.generate\s+(.*)'))
    client.add_event_handler(handler_addgroup, events.NewMessage(outgoing=True, pattern=r'(?i)\.addgroup\s+(.*)'))
    client.add_event_handler(handler_delgroup, events.NewMessage(outgoing=True, pattern=r'(?i)\.delgroup\s+(.*)'))
    client.add_event_handler(handler_apicheck, events.NewMessage(outgoing=True, pattern=r'(?i)\.apicheck\s+(.*)'))
    
    client.add_event_handler(handler_pay, events.NewMessage(outgoing=True, pattern=r'(?i)\.pay\s+(.*)'))
    client.add_event_handler(handler_payadd, events.NewMessage(outgoing=True, pattern=r'(?i)\.payadd\s+(.*)'))
    client.add_event_handler(handler_payedit, events.NewMessage(outgoing=True, pattern=r'(?i)\.payedit\s+(.*)'))
    client.add_event_handler(handler_paylist, events.NewMessage(outgoing=True, pattern=r'(?i)\.paylist'))
    client.add_event_handler(handler_paycheck, events.NewMessage(outgoing=True, pattern=r'(?i)\.paycheck\s+(.*)'))

    client.add_event_handler(handler_cfglist, events.NewMessage(outgoing=True, pattern=r'(?i)\.cfglist$'))
    client.add_event_handler(handler_addcfg, events.NewMessage(outgoing=True, pattern=r'(?i)\.addcfg\s+(.*)'))
    client.add_event_handler(handler_delcfg, events.NewMessage(outgoing=True, pattern=r'(?i)\.delcfg\s+(.*)'))
    client.add_event_handler(handler_cfgstatus, events.NewMessage(outgoing=True, pattern=r'(?i)\.cfgstatus\s+(.*)'))
    client.add_event_handler(handler_editcfg, events.NewMessage(outgoing=True, pattern=r'(?i)\.editcfg\s+(.*)'))