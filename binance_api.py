import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode

BINANCE_API_KEY = "TojHj1UOmgb5un1DIOyT0zI3mfESxe7Mgthnn2jlJ4qQy6pUL1gSTBAa5ti6DL2v"
BINANCE_SECRET_KEY = "jyZTLpFyDQ8XiVnUEUjVqzPq4w2kZno85Sa9rtrVoXNXNIf3n03HmLlradhanjOq"
BASE_URL = "https://api.binance.com"
TEST_MODE = False

def get_server_time():
    try:
        response = requests.get(f"{BASE_URL}/api/v3/time")
        return response.json()['serverTime']
    except:
        return int(time.time() * 1000)

def get_coin_price(symbol="LTCUSDT"):
    try:
        response = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={"symbol": symbol.upper()})
        return float(response.json()["price"])
    except:
        return 0.0

def get_deposit_address(coin, network=None):
    endpoint = "/sapi/v1/capital/deposit/address"
    timestamp = get_server_time()
    params = {"coin": coin.upper(), "timestamp": timestamp, "recvWindow": 60000}
    if network: params["network"] = network.upper()
    
    query_string = urlencode(params)
    signature = hmac.new(BINANCE_SECRET_KEY.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()
    params["signature"] = signature
    
    try:
        response = requests.get(BASE_URL + endpoint, headers={"X-MBX-APIKEY": BINANCE_API_KEY}, params=params)
        data = response.json()
        return data.get("address"), data.get("tag", "")
    except:
        return None, None

def get_binance_deposits(coin="USDT", limit=10):
    endpoint = "/sapi/v1/capital/deposit/hisrec"
    timestamp = get_server_time()
    params = {"coin": coin, "timestamp": timestamp, "recvWindow": 60000, "limit": limit}
    
    query_string = urlencode(params)
    signature = hmac.new(BINANCE_SECRET_KEY.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()
    params["signature"] = signature
    
    try:
        response = requests.get(BASE_URL + endpoint, headers={"X-MBX-APIKEY": BINANCE_API_KEY}, params=params)
        return response.json()
    except:
        return []

def verify_payment(txid, expected_amount, coin="USDT"):
    if TEST_MODE and txid.startswith("TEST"):
        return True, "CONFIRMED", expected_amount

    deposits = get_binance_deposits(coin=coin, limit=50)
    for deposit in deposits:
        if deposit.get("txId") == txid:
            status = deposit.get("status")
            amount = float(deposit.get("amount", 0))
            
            # Devolvemos: (Éxito, Motivo, MontoRecibido)
            if status != 1: return False, "PENDING", amount
            if amount < (expected_amount * 0.98): # Margen de error del 2%
                return False, "INSUFFICIENT_AMOUNT", amount
            return True, "CONFIRMED", amount
            
    return False, "NOT_FOUND", 0.0