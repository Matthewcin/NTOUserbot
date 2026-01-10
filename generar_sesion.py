from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID = 32541501
API_HASH = '66f7a1c72eac5d25705ef1d35275ca4f'

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print("👇 COPIA TODO LO QUE ESTÁ ABAJO DE ESTA LÍNEA 👇")
    print(client.session.save())
    print("👆 COPIA TODO LO QUE ESTÁ ARRIBA DE ESTA LÍNEA 👆")
    print("¡Guarda este código largo en un lugar seguro! Es tu acceso a Render.")
