import os
import time
from datetime import datetime, timedelta

from dotenv import load_dotenv

from exchange import Binance


def main():
    load_dotenv(verbose=True)
    binance = Binance(os.getenv("BINANCE_API_KEY"), os.getenv("BINANCE_API_SECRET"))
    binance.fetch_tokens()
    # sqlite_db = SQLiteDB(os.getenv("DATABASE_PATH", "database/db.sqlite"))

    # slack_client = WebClient(token=os.getenv("SLACK_API_TOKEN"))

    # logger = Logger(db=sqlite_db, slack_client=slack_client)
    binance.start_websocket_manager()
    # binance.start_ticker_socket("BTCUSDT")
    # binance.start_ticker_socket("ETHUSDT")
    # binance.start_user_socket()
    # binance.start_kline_socket("BTCUSDT", "1m")
    binance.start_futures_ticker_socket(["BTCUSDT", "ETHUSDT"])
    print("done")
    futures = binance.get_futures_client()
    print(futures.limit_buy_order("BTCUSDT", 0.0001, 1000))
    while True:
        time.sleep(5)
        # print(
        #     binance.database.query_ticker(
        #         symbol="BTCUSDT", start=datetime.now() - timedelta(hours=1), end=datetime.now()
        #     )
        # )
        print("tick")


if __name__ == "__main__":
    main()
