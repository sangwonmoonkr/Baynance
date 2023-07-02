class TokenFutures:
    def __init__(self, symbol, binance_client):
        self.symbol = symbol
        self.binance_client = binance_client
        self.leverage = 0
        self.isolated = False
        self.price_info = {
            "open": None,
            "close": None,
            "high": None,
            "low": None,
            "volume": None,
            "quote_asset_volume": None,
            "timestamp": None,
        }
        self.long_info = {
            "target": None,
            "amount": None,
            "target_hit": False,
            "filter": {"MT": False, "NY": False, "VT": False},
        }
        self.short_info = {
            "target": None,
            "amount": None,
            "target_hit": False,
            "filter": {"MT": False, "NY": False, "VT": False},
        }

    def __str__(self):
        return self.symbol
