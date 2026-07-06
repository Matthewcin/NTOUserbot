import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode

BINANCE_API_KEY = "TojHj1UOmgb5un1DIOyT0zI3mfESxe7Mgthnn2jlJ4qQy6pUL1gSTBAa5ti6DL2v"
BINANCE_SECRET_KEY = "jyZTLpFyDQ8XiVnUEUjVqzPq4w2kZno85Sa9rtrVoXNXNIf3n03HmLlradhanjOq"
BASE_URL = "https://api.binance.com"
TEST_MODE = True

def ping_binance():
    try:
        response = requests.get(f"{BASE_URL}/api/v3/ping")
        response.raise_for_status()
        return True
    except:
        return False

def get_coin_price(symbol="LTCUSDT"):
    try:
        response = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={"symbol": symbol.upper()})
        response.raise_for_status()
        data = response.json()
        return float(data["price"])
    except:
        return 0.0

def get_deposit_address(coin, network=None):
    endpoint = "/sapi/v1/capital/deposit/address"
    timestamp = int(time.time() * 1000)
    
    params = {
        "coin": coin.upper(),
        "timestamp": timestamp
    }
    
    if network:
        params["network"] = network.upper()
        
    query_string = urlencode(params)
    signature = hmac.new(
        BINANCE_SECRET_KEY.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    params["signature"] = signature
    headers = {
        "X-MBX-APIKEY": BINANCE_API_KEY
    }
    
    try:
        response = requests.get(BASE_URL + endpoint, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("address"), data.get("tag", "")
    except:
        return None, None

def get_deposit_address_list(coin):
    endpoint = "/sapi/v1/capital/deposit/address/list"
    timestamp = int(time.time() * 1000)
    
    params = {
        "coin": coin.upper(),
        "timestamp": timestamp
    }
    
    query_string = urlencode(params)
    signature = hmac.new(
        BINANCE_SECRET_KEY.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    params["signature"] = signature
    headers = {
        "X-MBX-APIKEY": BINANCE_API_KEY
    }
    
    try:
        response = requests.get(BASE_URL + endpoint, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except:
        return []

def get_binance_deposits(coin="USDT", limit=10):
    endpoint = "/sapi/v1/capital/deposit/hisrec"
    timestamp = int(time.time() * 1000)
    
    params = {
        "coin": coin,
        "timestamp": timestamp,
        "limit": limit
    }
    
    query_string = urlencode(params)
    signature = hmac.new(
        BINANCE_SECRET_KEY.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    params["signature"] = signature
    headers = {
        "X-MBX-APIKEY": BINANCE_API_KEY
    }
    
    try:
        response = requests.get(BASE_URL + endpoint, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except:
        return []

def check_txid_exists(txid, coin="USDT"):
    if TEST_MODE and txid.startswith("TEST"):
        return {"txId": txid, "status": 1, "amount": 999999.0}

    deposits = get_binance_deposits(coin=coin, limit=50)
    for deposit in deposits:
        if deposit.get("txId") == txid:
            return deposit
    return None

def verify_payment(txid, expected_amount, coin="USDT"):
    if TEST_MODE and txid.startswith("TEST"):
        return True, "CONFIRMED"

    deposit = check_txid_exists(txid, coin)
    
    if not deposit:
        return False, "NOT_FOUND"
        
    status = deposit.get("status")
    amount = float(deposit.get("amount", 0))
    
    if status != 1:
        return False, "PENDING"
        
    if amount < expected_amount:
        return False, "INSUFFICIENT_AMOUNT"
        
    return True, "CONFIRMED"