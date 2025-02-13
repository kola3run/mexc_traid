import logging
import asyncio
from config import API_KEY, API_SECRET, ORDER_SIZE, SPREAD_THRESHOLD, ORDER_CHECK_INTERVAL, LOG_FILE, STOP_LOSS_PERCENT
from utils import initialize_exchange, get_supported_symbols, get_balance, place_order, cancel_order, get_market_data, calculate_spread
from order_utils import reposition_order, stop_loss
import time

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
        self.order_size = ORDER_SIZE
        self.spread_threshold = SPREAD_THRESHOLD
        self.order_check_interval = ORDER_CHECK_INTERVAL
        self.stop_loss_percent = STOP_LOSS_PERCENT
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

            if spread and spread >= self.spread_threshold:
                if best_spread is None or spread > best_spread:
                    best_spread = spread
                    best_symbol = symbol

        if best_symbol:
            logging.info(f"Best symbol found: {best_symbol} with spread {best_spread}")
        return best_symbol

    async def trade(self, symbol):
        balance = await get_balance(self.exchange)
        if balance < self.order_size:
            logging.warning(f"Insufficient balance. Available: {balance} USDT, Required: {self.order_size} USDT")
            return

        order_book, ticker = await get_market_data(self.exchange, symbol)
        if not order_book or not ticker:
            logging.error(f"Failed to fetch market data for {symbol}")
            return

        spread, bid, ask = await calculate_spread(order_book)
        if not spread or spread < self.spread_threshold:
            logging.info(f"Spread {spread} for {symbol} is below threshold {self.spread_threshold}")
            return

        amount = self.order_size / ask
        logging.info(f"Placing buy order for {amount} {symbol} at price {ask}")
        buy_order = await place_order(self.exchange, symbol, 'buy', amount, ask, 'limit')

        if not buy_order:
            logging.error(f"Failed to place buy order for {symbol}")
            return

        await self.monitor_order(symbol, buy_order['id'], amount, ask, 'buy')

    async def monitor_order(self, symbol, order_id, amount, initial_price, side):
        start_time = time.time()
        last_check_time = start_time

        while time.time() - start_time < self.order_check_interval:
            order_status = await self.exchange.fetch_order(order_id, symbol)
            logging.info(f"Order status for {side} order {order_id} : {order_status}")

            if order_status['status'] == 'closed':
                logging.info(f"{side.capitalize()} order {order_id} executed.")
                if side == 'buy':
                    sell_price = initial_price * 1.01  # 1% profit target
                    logging.info(f"Placing sell order for {amount} {symbol} at price {sell_price}")
                    sell_order = await place_order(self.exchange, symbol, 'sell', amount, sell_price, 'limit')
                    if sell_order:
                        await self.monitor_order(symbol, sell_order['id'], amount, sell_price, 'sell')
                return

            current_time = time.time()
            if current_time - last_check_time > self.order_check_interval:
                order_book, ticker = await get_market_data(self.exchange, symbol)
                spread, bid, ask = await calculate_spread(order_book)

                if side == 'buy' and abs(order_status['price'] - ask) > 0.1 * ask:
                    logging.info(f"Repositioning buy order for {amount} {symbol} at new price {ask}")
                    buy_order = await reposition_order(self.exchange, symbol, order_id, amount, ask, 'buy')
                    last_check_time = current_time

                if side == 'sell' and abs(order_status['price'] - bid) > 0.1 * bid:
                    logging.info(f"Repositioning sell order for {amount} {symbol} at new price {bid}")
                    sell_order = await reposition_order(self.exchange, symbol, order_id, amount, bid, 'sell')
                    last_check_time = current_time

                if side == 'buy' and bid < initial_price * (1 - self.stop_loss_percent / 100):
                    logging.info(f"Stop loss triggered for {symbol}. Cancelling buy order and selling at market price.")
                    await stop_loss(self.exchange, symbol, order_id, amount)
                    return

            await asyncio.sleep(1)

        await cancel_order(self.exchange, order_id, symbol)
        logging.info(f"Order timeout reached for {symbol}. Trying another pair.")

    async def run(self):
        await self.initialize()
        while True:
            best_symbol = await self.find_best_symbol()
            if best_symbol:
                await self.trade(best_symbol)
            await asyncio.sleep(1)

    async def close(self):
        if self.exchange:
            await self.exchange.close()

if __name__ == '__main__':
    bot = TradingBot()
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot.run())
    except KeyboardInterrupt:
        logging.info("Trading bot stopped manually.")
    finally:
        loop.run_until_complete(bot.close())
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()