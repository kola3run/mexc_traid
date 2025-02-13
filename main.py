import asyncio
import logging
from bot import TradingBot

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