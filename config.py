API_KEY = "mx0vglSs5ISVvo9h6n"
API_SECRET = "3f58af4ad03e44b6a2526aeaa951a454"

# Торговые параметры
TRADE_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]  # Добавь свои пары
SPREAD_THRESHOLD = 0.002  # Минимальный спред для входа в сделку
ORDER_SIZE = 10  # Размер ордера в USDT
STOP_LOSS_PERCENT = 0.30  # 30% стоп-лосс
MAX_ORDER_LIFETIME = 10  # Время жизни ордера в секундах

# Логирование
LOG_FILE = "trade_log.txt"
LOG_LEVEL = "INFO"

# Тайминги
CHECK_MARKETS_INTERVAL = 1  # Интервал проверки рынка в секундах
ORDER_CHECK_INTERVAL = 0.5  # Интервал проверки ордеров