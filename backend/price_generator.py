
import random
import threading
import time
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, time as market_time

from zoneinfo import ZoneInfo
import holidays

def is_market_open():

    now = datetime.now(ZoneInfo("America/New_York"))

    if now.weekday() >= 5:
        return False

    nyse_holidays = holidays.NYSE()

    if now.date() in nyse_holidays:
        return False

    return market_time(9, 30) <= now.time() < market_time(16, 0)


def generate_random_price(current_price):
    current_price = Decimal(str(current_price))

    # Randomly increase or decrease the price by up to 2%
    change = Decimal(str(random.uniform(-0.02, 0.02)))

    new_price = current_price * (1 + change)

    # Prevent prices from becoming zero or negative
    new_price = max(Decimal("0.01"), new_price)

    return new_price.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def start_price_generator(update_prices):
    def run():
        while True:
            try:
                if is_market_open():
                    update_prices()
                else:
                    print("Market is closed.")
            except Exception as error:
                print("Price update error:", error)

            time.sleep(5)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()