import time
import logging
import asyncio
from config import API_KEY, API_SECRET, BUDGET, MIN_VOLUME_USD, SPREAD_THRESHOLD, ORDER_TIMEOUT, ORDER_CHECK_INTERVAL, \
    LOG_FILE, STOP_LOSS_THRESHOLD
from utils import (
    initialize_exchange, get_supported_symbols, get_balance, place_order,
    cancel_order, get_market_data, calculate_spread, get_best_price
)
from order_utils import reposition_order

# Настройка логирования
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)


class TradingBot:
    def __init__(self):
        self.exchange = None
        self.symbols = []
        self.budget = BUDGET
        self.min_volume_usd = MIN_VOLUME_USD
        self.spread_threshold = SPREAD_THRESHOLD
        self.order_timeout = ORDER_TIMEOUT
        self.order_check_interval = ORDER_CHECK_INTERVAL
        self.active_orders = {}

    async def initialize(self):
        self.exchange = await initialize_exchange(API_KEY, API_SECRET)
        self.symbols = await get_supported_symbols(self.exchange)
        logging.info(f"Trading bot initialized. Found {len(self.symbols)} symbols.")

    async def find_best_symbol(self):
        best_symbol = None
        best_spread = None

        for symbol in self.symbols:
            order_book, ticker = await get_market_data(self.exchange, symbol)
            if not order_book or not ticker:
                continue

            spread, bid, ask = await calculate_spread(order_book)

            if spread and spread >= self.spread_threshold and ticker['quoteVolume'] >= self.min_volume_usd:
                if best_spread is None or spread > best_spread:
                    best_spread = spread
                    best_symbol = symbol

        if best_symbol:
            logging.info(f"Best symbol found: {best_symbol} with spread {best_spread}")
        return best_symbol

    async def trade(self, symbol):
        balance = await get_balance(self.exchange)
        if balance < self.budget:
            logging.warning("Insufficient balance to trade!")
            return

        bid_price, ask_price = await get_best_price(self.exchange, symbol)

        if not bid_price or not ask_price:
            logging.warning(f"Failed to fetch best prices for {symbol}")
            return

        quantity = self.budget / ask_price
        order_id = await place_order(self.exchange, symbol, "buy", quantity, bid_price)
        if order_id:
            self.active_orders[symbol] = order_id
            logging.info(f"Placed buy order for {symbol} at {bid_price}")
            await self.monitor_order(symbol, order_id, quantity)

    async def monitor_order(self, symbol, order_id, quantity):
        while True:
            order_status = await self.exchange.fetch_order(order_id, symbol)
            if order_status['status'] == 'closed':
                logging.info(f"Order filled for {symbol}, placing sell order.")
                sell_price = order_status['price'] * 1.01  # 1% profit target
                sell_order_id = await place_order(self.exchange, symbol, "sell", quantity, sell_price)
                self.active_orders[symbol] = sell_order_id
                return

            current_price = await get_best_price(self.exchange, symbol)

            if current_price and current_price < order_status['price'] * (1 - STOP_LOSS_THRESHOLD):
                logging.warning(f"Stop-loss triggered for {symbol}, selling at market price.")
                await cancel_order(self.exchange, symbol, order_id)
                await place_order(self.exchange, symbol, "sell", quantity, current_price, market=True)
                return

            await asyncio.sleep(self.order_check_interval)

    async def run(self):
        await self.initialize()
        while True:
            best_symbol = await self.find_best_symbol()
            if best_symbol:
                await self.trade(best_symbol)
            await asyncio.sleep(5)  # Ожидание перед следующей проверкой


if __name__ == "__main__":
    bot = TradingBot()
    asyncio.run(bot.run())
