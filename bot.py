from datetime import datetime, time
import pytz
import time as t
import pyotp
from SmartApi.smartConnect import SmartConnect

# ================= TIMEZONE =================
IST = pytz.timezone("Asia/Kolkata")

# ================= USER CONFIG =================
SYMBOL = "IDEA-EQ"
TOKEN = "14366"
SIDE = "BUY"            # BUY or SELL
QTY = 1

LIMIT_PRICE = 12.05
TARGET_PRICE = 12.18
STOPLOSS_PRICE = 11.00
TARGET_POINTS = round(TARGET_PRICE - LIMIT_PRICE, 2)
STOPLOSS_POINTS = round(LIMIT_PRICE - STOPLOSS_PRICE, 2)

MAX_RETRIES = 5
RETRY_INTERVAL = 300    # 5 minutes
EXCHANGE = "NSE"
# =============================================

# ================= LOGIN DETAILS (MANUAL) =================
API_KEY = "RZFN84RY"
CLIENT_CODE = "AAAA624603"
PASSWORD = "8320"
TOTP_SECRET = "23HF32I3BXUB74NY6PZNLC7F3I"
# ==========================================================


def angel_login():
    totp = pyotp.TOTP(TOTP_SECRET).now()
    api = SmartConnect(api_key=API_KEY)
    session = api.generateSession(CLIENT_CODE, PASSWORD, totp)

    if not session or not session.get("status"):
        raise Exception("❌ Angel login failed")

    print("✅ Angel login successful")
    return api


def place_robo_order(api):
    print("📤 Placing ROBO order")

    return api.placeOrder({
        "variety": "ROBO",
        "tradingsymbol": SYMBOL,
        "symboltoken": TOKEN,
        "transactiontype": SIDE,
        "exchange": EXCHANGE,
        "ordertype": "LIMIT",
        "producttype": "INTRADAY",
        "duration": "DAY",
        "price": LIMIT_PRICE,
        "quantity": QTY,
        "squareoff": TARGET_POINTS,
        "stoploss": STOPLOSS_POINTS,
    })


def auto_square_off(api):
    print("⏰ 3:00 PM reached → Auto square-off")

    try:
        positions = api.position()
        data = positions.get("data")

        if not data:
            print("ℹ️ No open positions")
            return

        for pos in data:
            qty = int(pos.get("netqty", 0))
            if qty == 0:
                continue

            side = "SELL" if qty > 0 else "BUY"

            api.placeOrder({
                "variety": "NORMAL",
                "tradingsymbol": pos["tradingsymbol"],
                "symboltoken": pos["symboltoken"],
                "transactiontype": side,
                "exchange": pos["exchange"],
                "ordertype": "MARKET",
                "producttype": "INTRADAY",
                "duration": "DAY",
                "quantity": abs(qty)
            })

            print(f"✅ Squared off {pos['tradingsymbol']} | Qty {abs(qty)}")

        print("🟢 Auto square-off completed")

    except Exception as e:
        print(f"❌ Square-off error: {e}")


def run_bot():
    now = datetime.now(IST).time()

    # 🔴 AUTO SQUARE-OFF AT 3 PM
    if now >= time(15, 0):
        api = angel_login()
        auto_square_off(api)
        return

    # 🟡 MARKET HOURS CHECK
    if not time(9, 15) <= now < time(15, 0):
        print("⏰ Outside market hours")
        return

    api = angel_login()

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"🔁 Attempt {attempt}/{MAX_RETRIES}")

        order = place_robo_order(api)
        order_id = order.get("data", {}).get("orderid")

        if order_id:
            print(f"✅ ROBO order placed | Order ID: {order_id}")
            return

        print("❌ Order failed → retrying in 5 minutes")
        t.sleep(RETRY_INTERVAL)

    print("🚨 All retry attempts failed")


if __name__ == "__main__":
    run_bot()
