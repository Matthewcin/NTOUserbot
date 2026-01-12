import os

# 🔐 Credenciales Telegram y DB
API_ID = int(os.getenv('API_ID', '32541501'))
API_HASH = os.getenv('API_HASH', '66f7a1c72eac5d25705ef1d35275ca4f')
SESSION_STRING = os.getenv('SESSION_STRING')
DB_URL = os.getenv('DB_URL')
OXAPAY_KEY = os.getenv('OXAPAY_KEY', 'WGJMFR-0DMVXO-IRCXPB-GDJHED')

# ☁️ OpenBullet API (SmarterASP)
OB_URL = "http://cloudfig6-001-site1.qtempurl.com/top"
OB_SECRET = "ZjBmYjQ2ZTdiMmRiZTdmYzAxNjY1Nzc1MjVkNGNlY2JjYmU3NWQwYjNiNGIzMWU0MTVlYTcxMWM5MmY3MWRkNmQzMzU1MjYzOGY4OWZjMjg2NzlhMjg1ZjZhMTEyOWZmMmJiZjYyMGM1Y2VhMjMwMDE3YzdmODJiNGJjM2RmN2Q="

# ⚙️ Configuración del Bot
TARGET_GROUP = 'myConfigCloud'
MY_USER_LINK = 'https://t.me/whois_tyler'
STICKER_FILENAME = 'sticker.tgs'

# 💬 Textos
MSG_WELCOME_1 = "Hello mate, I'm VirusNTO From Config Cloud Channel. How can I help you?"
MSG_WELCOME_2 = "I'm a Live person but I created a Userbot to make things easier. Please use .cmds to see what I can do."
