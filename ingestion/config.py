import os


class Config:
    # --- Exchange WebSocket endpoints ---
    BINANCE_WS_URL = os.getenv(
        "BINANCE_WS_URL",
        "wss://stream.binance.com:9443/ws/btcusdt@ticker/ethusdt@ticker/ethbtc@ticker",
    )
    BYBIT_WS_URL = os.getenv("BYBIT_WS_URL", "wss://stream.bybit.com/v5/public/spot")
    OKX_WS_URL = os.getenv("OKX_WS_URL", "wss://ws.okx.com:8443/ws/v5/public")

    # --- Kafka ---
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "market-data")

    # --- Redis ---
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

    # --- Connection resilience ---
    INITIAL_RECONNECT_DELAY = float(os.getenv("INITIAL_RECONNECT_DELAY", "1"))
    MAX_RECONNECT_DELAY = float(os.getenv("MAX_RECONNECT_DELAY", "60"))
    HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "30"))

    # --- Queue ---
    QUEUE_MAX_SIZE = int(os.getenv("QUEUE_MAX_SIZE", "10000"))

    # --- Runtime ---
    DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
