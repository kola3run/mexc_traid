import asyncio
import logging
from bot import TradingBot

if __name__ == '__main__':
    bot = TradingBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logging.info("Trading bot stopped manually.")