import logging
from utils import cancel_order, place_order

async def reposition_order(exchange, symbol, order_id, amount, new_price, order_side='buy'):
    try:
        await cancel_order(exchange, order_id, symbol)
        logging.info(f"Cancelled {order_side} order {order_id} for {symbol}")

        new_order = await place_order(exchange, symbol, order_side, amount, new_price, 'limit')
        logging.info(f"Placed new {order_side} order for {amount} {symbol} at price {new_price}")
        return new_order
    except Exception as e:
        logging.error(f"Error repositioning order: {e}")
        return None

async def stop_loss(exchange, symbol, order_id, amount):
    try:
        await cancel_order(exchange, order_id, symbol)
        logging.info(f"Cancelled order {order_id} for {symbol}")
        await place_order(exchange, symbol, 'sell', amount, order_type='market')
        logging.info(f"Placed market sell order for {amount} {symbol} due to stop loss")
    except Exception as e:
        logging.error(f"Error executing stop loss: {e}")