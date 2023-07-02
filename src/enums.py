from enum import Enum


class Table(Enum):
    LOG = "logs"
    TICKER = "tickers"
    TRADE = "trades"
    ORDER = "orders"


# Log levels
DEBUG = "DEBUG"
INFO = "INFO"
WARNING = "WARNING"
ERROR = "ERROR"
CRITICAL = "CRITICAL"
