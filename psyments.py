import requests
from config import OXAPAY_KEY, MY_USER_LINK

def create_invoice(amount, order_id, description):
    url = "https://api.oxapay.com/merchants/request"
    payload = {
        "merchant": OXAPAY_KEY,
        "amount": amount,
        "currency": "USDT",
        "life_time": 60,
        "fee_paid_by_payer": 0,
        "return_url": MY_USER_LINK,
        "description": description,
        "order_id": order_id
    }
    try:
        response = requests.post(url, json=payload).json()
        if response.get("result") != 100:
            print(f"⚠️ OXAPAY ERROR: {response}")
            return None
        return {"url": response.get("pay_url"), "track_id": response.get("trackId")}
    except Exception as e:
        print(f"⚠️ API EXCEPTION: {e}")
        return None
