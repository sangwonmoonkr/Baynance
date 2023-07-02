import os

from datetime import datetime
from typing import List, Dict, Any

from slack_sdk import WebClient

from binance import ThreadedWebsocketManager
from binance.client import Client
from binance.enums import (
    FuturesType,
    SIDE_BUY,
    SIDE_SELL,
    ORDER_TYPE_MARKET,
    ORDER_TYPE_LIMIT,
    FUTURE_ORDER_TYPE_STOP_MARKET,
    TIME_IN_FORCE_GTC,
)

from tokens import TokenFutures
from sqlite_db import SQLiteDB
from utils import BinanceLogger


class Binance:
    """
    Class for Binance API

    Attributes:
        client (Client): Binance API client
        tokens (Dict[str, TokenFutures]): Dictionary of TokenFutures objects
    """

    def __init__(self, api_key, api_secret):
        self.client = Client(api_key=api_key, api_secret=api_secret)
        self.futures_client = Binance.FuturesClient(api_key=api_key, api_secret=api_secret)
        self.tokens: Dict[str, TokenFutures] = {}
        self.threaded_websocket_manager = ThreadedWebsocketManager(
            api_key=api_key, api_secret=api_secret
        )
        self.database = SQLiteDB(os.getenv("DATABASE_PATH", "database/db.sqlite"))
        # self.queue = Queue()
        self.logger = BinanceLogger(
            db=self.database, slack_client=WebClient(token=os.getenv("SLACK_API_TOKEN"))
        )

    def get_futures_client(self):
        return self.futures_client

    class WebsocketManager(ThreadedWebsocketManager):
        def __init__(self, api_key: str, api_secret: str):
            super().__init__(api_key=api_key, api_secret=api_secret)

    def start_websocket_manager(self) -> None:
        """
        Start the websocket manager
        """
        try:
            self.threaded_websocket_manager.start()
        except RuntimeError:
            self.logger.warning("Websocket manager already started")
        self.logger.info("Websocket manager started")

    def stop_websocket_manager(self) -> None:
        """
        Stop the websocket manager
        """
        self.threaded_websocket_manager.stop()

    def join_websocket_thread(self) -> None:
        """
        Join the websocket thread
        """
        self.threaded_websocket_manager.join()

    def start_ticker_socket(self, symbol: str) -> str:
        """
        Start a stream for a mini-ticker of a given symbol

        Args:
            symbol (str): symbol name to get ticker

        Returns:
            str: websocket id
        """
        self.database.create_table("tickers")
        return self.threaded_websocket_manager.start_symbol_miniticker_socket(
            callback=lambda msg: self.ticker_handler(msg=msg, is_futures=False),
            symbol=symbol,
        )

    def start_futures_ticker_socket(self, symbol: str | List[str]) -> str:
        """_summary_

        Args:
            symbol (str | List[str]): _description_

        Returns:
            str: _description_
        """
        self.database.create_table("tickers")
        if isinstance(symbol, str):
            return self.threaded_websocket_manager.start_symbol_ticker_futures_socket(
                callback=lambda msg: self.ticker_handler(msg=msg, is_futures=True),
                symbol=symbol,
                futures_type=FuturesType.USD_M,
            )
        if isinstance(symbol, list):
            streams = list(map(lambda s: s.lower() + "@ticker", symbol))
            return self.threaded_websocket_manager.start_futures_multiplex_socket(
                callback=lambda msg: self.ticker_handler(msg=msg, is_futures=True),
                streams=streams,
                futures_type=FuturesType.USD_M,
            )

    def start_kline_socket(self, symbol: str, interval: str) -> str:
        """_summary_

        Args:
            symbol (str): _description_
            interval (str): _description_

        Returns:
            str: _description_
        """
        return self.threaded_websocket_manager.start_kline_socket(
            callback=lambda msg: self.kline_handler(msg=msg),
            symbol=symbol,
            interval=interval,
        )

    def start_user_socket(self) -> str:
        """_summary_

        Returns:
            str: _description_
        """
        return self.threaded_websocket_manager.start_user_socket(
            callback=lambda msg: self.user_handler(msg=msg)
        )

    def ticker_handler(self, msg: Dict[str, Any], is_futures: bool) -> None:
        """
        Handler for ticker websocket

        Args:
            symbol (str): symbol name
            msg (Dict[str, Any]): message from websocket
        """
        if is_futures:
            msg = msg["data"]
        symbol = msg["s"]
        # overhead?
        if symbol not in self.tokens:
            self.tokens[symbol] = TokenFutures(symbol, self.client)
        close_price = float(msg["c"])
        last_close_price = self.tokens[symbol].price_info["close"]

        if last_close_price is None or abs(close_price / last_close_price - 1) > 0.001:  # constant
            self.database.insert_ticker(msg)
            self.save_ticker(msg)

    def kline_handler(self, msg: Dict[str, Any]) -> None:
        """
        Handler for kline websocket

        Args:
            symbol (str): symbol name
            msg (Dict[str, Any]): message from websocket
        """
        print(msg)
        return

    def user_handler(self, msg: Dict[str, Any]) -> None:
        """
        Handler for user websocket

        Args:
            symbol (str): symbol name
            msg (Dict[str, Any]): message from websocket
        """
        print(msg)
        return

    def message_handler(self, msg: Dict[str, Any]) -> None:
        print(msg)

    def save_ticker(self, msg: Dict[str, Any]) -> None:
        """
        Save ticker info to tokens dictionary

        Args:
            msg (Dict[str, Any]): message from ticker stream
        """
        self.tokens[msg["s"]].price_info = {
            "open": float(msg["o"]),
            "close": float(msg["c"]),
            "high": float(msg["h"]),
            "low": float(msg["l"]),
            "volume": float(msg["v"]),
            "quote_asset_volume": float(msg["q"]),
            "timestamp": datetime.fromtimestamp(msg["E"] / 1000),
        }

    def fetch_tokens(self) -> Dict[str, TokenFutures]:
        """_summary_

        Returns:
            Dict[str, TokenFutures]: _description_
        """
        self.tokens = {
            token["symbol"]: TokenFutures(token["symbol"], self.client)
            for token in self.client.get_all_tickers()
            if token["symbol"][-4:] == "USDT"
        }
        return self.tokens

    def get_tokens(self) -> Dict[str, TokenFutures]:
        """
        Returns:
            Dict[str, TokenFutures]: tokens dictionary
        """
        return self.tokens

    class FuturesClient(Client):
        """
        A class that extends the Binance API Client to include futures trading methods.
        """

        def __init__(self, api_key: str, api_secret: str):
            super().__init__(api_key=api_key, api_secret=api_secret)

        def limit_buy_order(self, symbol: str, quantity: float, price: float) -> Dict[str, Any]:
            """
            Places a limit buy order for the given symbol, quantity, and price.

            Args:
                symbol (str): The symbol to buy.
                quantity (float): The quantity to buy.
                price (float): The price to buy at.

            Returns:
                Dict[str, Any]: The order result.
            """
            self.database
            return self.futures_create_order(
                symbol=symbol,
                side=SIDE_BUY,
                type=ORDER_TYPE_LIMIT,
                timeInForce=TIME_IN_FORCE_GTC,
                quantity=quantity,
                price=price,
            )

        def limit_sell_order(self, symbol: str, quantity: float, price: float) -> Dict[str, Any]:
            """
            Places a limit sell order for the given symbol, quantity, and price.

            Args:
                symbol (str): The symbol to sell.
                quantity (float): The quantity to sell.
                price (float): The price to sell at.

            Returns:
                Dict[str, Any]: The order result.
            """
            return self.futures_create_order(
                symbol=symbol,
                side=SIDE_SELL,
                type=ORDER_TYPE_LIMIT,
                timeInForce=TIME_IN_FORCE_GTC,
                quantity=quantity,
                price=price,
            )

        def market_buy_order(self, symbol: str, quantity: float) -> Dict[str, Any]:
            """
            Places a market buy order for the given symbol and quantity.

            Args:
                symbol (str): The symbol to buy.
                quantity (float): The quantity to buy.
            """
            return self.futures_create_order(
                symbol=symbol,
                side=SIDE_BUY,
                type=ORDER_TYPE_MARKET,
                quantity=quantity,
            )

        def market_sell_order(self, symbol: str, quantity: float) -> Dict[str, Any]:
            """
            Places a market sell order for the given symbol and quantity.

            Args:
                symbol (str): The symbol to sell.
                quantity (float): The quantity to sell.
            """
            return self.futures_create_order(
                symbol=symbol,
                side=SIDE_SELL,
                type=ORDER_TYPE_MARKET,
                quantity=quantity,
            )

        def get_open_orders(self, symbol: str) -> Dict[Any, Any]:
            """
            Gets all open orders for the given symbol.

            Args:
                symbol (str): The symbol to get open orders for.

            Returns:
                Dict[Any, Any]: The open orders.
            """
            return self.futures_get_open_orders(symbol=symbol)

        def get_all_open_orders(self) -> Dict[Any, Any]:
            """
            Gets all open orders.

            Returns:
                Dict[Any, Any]: The open orders.
            """
            return self.futures_get_open_orders()

        def cancel_order(self, symbol: str, orderId: int) -> Dict[Any, Any]:
            """
            Cancels the given order.

            Args:
                symbol (str): The symbol of the order to cancel.
                orderId (int): The order ID of the order to cancel.

            Returns:
                Dict[Any, Any]: The result of the cancel.
            """
            return self.futures_cancel_order(symbol=symbol, orderId=orderId)

        def stop_market_order(
            self, symbol: str, quantity: float, stop_price: float
        ) -> Dict[Any, Any]:
            """
            Places a stop market order for the given symbol, quantity, and stop price.

            Args:
                symbol (str): The symbol to buy.
                quantity (float): The quantity to buy.
                stopPrice (float): The stop price to buy at.
            """
            return self.futures_create_order(
                symbol=symbol,
                side=SIDE_BUY,
                type=FUTURE_ORDER_TYPE_STOP_MARKET,
                quantity=quantity,
                stopPrice=stop_price,
            )
