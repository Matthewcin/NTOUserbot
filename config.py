import os

# Telegram
API_ID = int(os.getenv('API_ID', '32541501'))
API_HASH = os.getenv('API_HASH', '66f7a1c72eac5d25705ef1d35275ca4f')
SESSION_STRING = os.getenv('SESSION_STRING')

# Database & Payments
DB_URL = os.getenv('DB_URL')
OXAPAY_KEY = os.getenv('OXAPAY_KEY', 'WGJMFR-0DMVXO-IRCXPB-GDJHED')

# Bot Settings
TARGET_GROUP = 'myConfigCloud'
MY_USER_LINK = 'https://t.me/whois_tyler'