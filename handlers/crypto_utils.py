import requests
from datetime import datetime, timezone
from dateutil import parser
import re
import random
import config

class CryptoChecker:
    def get_crypto_price(self, symbol):
        symbol = symbol.upper().strip()
        if symbol in ['USDT', 'USDC', 'DAI', 'BUSD']: return 1.0
        
        try:
            token = config.FREE_CRYPTO_API_TOKEN
            url = f"https://api.freecryptoapi.com/v1/getData?symbol={symbol}"
            headers = {"Authorization": f"Bearer {token}", "Accept": "*/*"}
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success' and data.get('symbols'):
                    price = float(data['symbols'][0]['last'])
                    if price > 0: return price
        except: pass

        rates = {'BTC': 96000.0, 'LTC': 100.0, 'ETH': 2700.0, 'TRX': 0.25}
        return rates.get(symbol, 1.0)

    def validate_txid_format(self, symbol, txid):
        if not txid: return False
        txid = txid.strip()
        if symbol in ['BTC', 'LTC']:
            return bool(re.match(r'^[a-fA-F0-9]{64}$', txid))
        return True 

    def check_btc(self, tx_id, expected_address, order_time_dt):
        if not tx_id: return False, 0, 0, "No TXID"
        try:
            url = f"https://mempool.space/api/tx/{tx_id}"
            r = requests.get(url, timeout=10)
            if r.status_code != 200: return False, 0, 0, "TX Not Found"
            data = r.json()
            
            if data['status']['confirmed']:
                tx_ts = data['status']['block_time']
            else:
                tx_ts = datetime.now(timezone.utc).timestamp()

            if tx_ts < (order_time_dt.timestamp() - 7200):
                return False, 0, 0, "Transaction too old"

            amount = sum(out['value'] for out in data['vout'] if out.get('scriptpubkey_address') == expected_address)
            return True, amount / 100000000, 1 if data['status']['confirmed'] else 0, "OK"
        except Exception as e: return False, 0, 0, str(e)

    def check_ltc(self, tx_id, expected_address, order_time_dt):
        if not tx_id: return False, 0, 0, "No TXID"
        try:
            url = f"https://api.blockcypher.com/v1/ltc/main/txs/{tx_id}"
            r = requests.get(url, timeout=10)
            if r.status_code != 200: return False, 0, 0, "TX Not Found"
            data = r.json()
            
            received = parser.parse(data['received']).astimezone(timezone.utc)
            if received.timestamp() < (order_time_dt.timestamp() - 7200):
                return False, 0, 0, "Transaction too old"

            amount = sum(out['value'] for out in data['outputs'] if expected_address in out.get('addresses', []))
            return True, amount / 100000000, data.get('confirmations', 0), "OK"
        except Exception as e: return False, 0, 0, str(e)

crypto_check = CryptoChecker()
