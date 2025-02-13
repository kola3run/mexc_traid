# order_utils.py
import time
import ccxt
import logging
from config import API_KEY, API_SECRET, STOP_LOSS_PERCENT, MAX_ORDER_LIFETIME

# Настройка логирования
logging.basicConfig(filename="trade_log.txt", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Подключение к MEXC
exchange = ccxt.mexc({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "rateLimit": 1200,
    "enableRateLimit": True,
})


def place_limit_order(symbol, side, price, amount):
    """Размещает лимитный ордер."""
    try:
        order = exchange.create_limit_order(symbol, side, amount, price)
        logging.info(f"Создан {side} ордер {amount} {symbol} по цене {price}")
        return order
    except Exception as e:
        logging.error(f"Ошибка при размещении ордера: {e}")
        return None


def cancel_order(order_id, symbol):
    """Отменяет ордер по ID."""
    try:
        exchange.cancel_order(order_id, symbol)
        logging.info(f"Отменен ордер {order_id} на {symbol}")
    except Exception as e:
        logging.error(f"Ошибка при отмене ордера {order_id}: {e}")


def check_and_update_order(order, symbol, target_price):
    """Проверяет ордер и обновляет его, если необходимо."""
    try:
        order_info = exchange.fetch_order(order["id"], symbol)
        if order_info["status"] == "open":
            current_price = exchange.fetch_ticker(symbol)["last"]

            # Если цена изменилась значительно, переставляем ордер
            if abs(current_price - target_price) / target_price > 0.001:
                cancel_order(order["id"], symbol)
                new_order = place_limit_order(symbol, order["side"], target_price, order["amount"])
                return new_order
        return order
    except Exception as e:
        logging.error(f"Ошибка при проверке ордера: {e}")
        return None


def execute_spread_trade(symbol, bid_price, ask_price, amount):
    """Открывает сделку по спреду."""
    buy_order = place_limit_order(symbol, "buy", bid_price, amount)
    if not buy_order:
        return None, None

    sell_order = place_limit_order(symbol, "sell", ask_price, amount)
    if not sell_order:
        cancel_order(buy_order["id"], symbol)
        return None, None

    return buy_order, sell_order


def stop_loss_check(order, symbol, entry_price):
    """Проверяет, не упала ли цена на 30%, и продает по рынку при необходимости."""
    try:
        current_price = exchange.fetch_ticker(symbol)["last"]
        if current_price <= entry_price * (1 - STOP_LOSS_PERCENT):
            cancel_order(order["id"], symbol)
            exchange.create_market_sell_order(symbol, order["amount"])
            logging.warning(f"Сработал стоп-лосс! Продажа {order['amount']} {symbol} по рыночной цене {current_price}")
    except Exception as e:
        logging.error(f"Ошибка при проверке стоп-лосса: {e}")


def monitor_orders(buy_order, sell_order, symbol, entry_price):
    """Следит за ордерами и корректирует их."""
    start_time = time.time()
    while True:
        if time.time() - start_time > MAX_ORDER_LIFETIME:
            logging.info(f"Время жизни ордеров истекло, отменяем сделки на {symbol}")
            cancel_order(buy_order["id"], symbol)
            cancel_order(sell_order["id"], symbol)
            return

        buy_order = check_and_update_order(buy_order, symbol, buy_order["price"])
        sell_order = check_and_update_order(sell_order, symbol, sell_order["price"])

        stop_loss_check(buy_order, symbol, entry_price)
        stop_loss_check(sell_order, symbol, entry_price)

        time.sleep(1)
