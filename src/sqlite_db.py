from datetime import datetime
from typing import Generator, List
from contextlib import contextmanager
from logging import getLevelName, INFO, ERROR

from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.exc import IntegrityError


from enums import Table

Base: DeclarativeMeta = declarative_base()


class SQLiteDB:
    """
    A class for interacting with a SQLite database using SQLAlchemy ORM.

    Attributes:
        engine (sqlalchemy.engine.base.Engine): The SQLAlchemy engine object used to connect to the database.
        session_local (sqlalchemy.orm.session.sessionmaker): The SQLAlchemy sessionmaker object used to create sessions.
    """

    def __init__(self, db_name: str):
        """
        Initialize a new SQLiteDB object.

        Args:
            db_name (str): The name of the SQLite database file to connect to.
        """
        self.engine = create_engine(f"sqlite:///{db_name}")
        self.Session = sessionmaker(  # pylint: disable=C0103
            autocommit=False, autoflush=False, bind=self.engine
        )

    @contextmanager
    def session(self, autocommit: bool = True) -> Generator[Session, None, None]:
        """_summary_

        Args:
            autocommit (bool, optional): Whether to commit the session after the context manager exits. Defaults to True.

        Yields:
            Generator[Session, None, None]: yields a session object
        """
        session = self.Session()
        try:
            yield session
            if autocommit:
                session.commit()
        except IntegrityError as integrity_error:
            session.rollback()
            self.log(ERROR, str(integrity_error), datetime.now().timestamp())
        finally:
            session.close()

    def create_table(self, table: Table | str) -> None:
        """
        Create a table in the database with the given table name.
        If exists, do nothing.

        Args:
            table (Table | str): Table name enum object or a table name string.
        """
        if isinstance(table, Table):
            table_name = table.value
        elif isinstance(table, str):
            table_name = table

        if table_name in Base.metadata.tables:
            Base.metadata.tables[table_name].create(bind=self.engine, checkfirst=True)
        else:
            raise ValueError(f"No table found with name {table_name}")

    class Log(Base):
        """
        "logs" table in the sqlite database.

        Attributes:
            id (int): The unique identifier of the log message.
            level (str): The log level. One of "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL".
            msg (str): The log message.
            datetime (datetime): The timestamp of the log message.
        """

        __tablename__ = Table.LOG.value

        id = Column(Integer, primary_key=True, index=True)
        level = Column(String)
        msg = Column(String)
        datetime = Column(DateTime)

    def log(self, level: str | int, msg: str, created: float) -> None:
        """
        Insert a row into a table.

        Args:
            level (str | int): The log level.
            msg (str): The log message.
            created (float): The timestamp of the log message in seconds since the epoch.
        """
        if isinstance(level, int):
            level = getLevelName(level)

        with self.session() as session:
            log = self.Log(level=level, msg=msg, datetime=datetime.fromtimestamp(created))
            session.add(log)

    class Ticker(Base):
        """
        "tickers" table in the sqlite database.

        Attributes:
            timestamp (datetime): The timestamp of the ticker data.
            symbol (str): The symbol of the ticker data.
            close (float): The close price of the ticker data.
            open (float): The open price of the ticker data.
            high (float): The high price of the ticker data.
            low (float): The low price of the ticker data.
            volume (float): The volume of the ticker data.
            quote_asset_volume (float): The quote asset volume of the ticker data.
        """

        __tablename__ = Table.TICKER.value

        id = Column(Integer, primary_key=True, index=True)
        timestamp = Column(DateTime)
        symbol = Column(String)
        close = Column(Float)
        open = Column(Float)
        high = Column(Float)
        low = Column(Float)
        volume = Column(Float)
        quote_asset_volume = Column(Float)

    def insert_ticker(self, data: dict) -> None:
        """
        Insert a row into a table.

        Args:
            data (dict): The ticker data.
        """
        with self.session() as session:
            ticker = self.Ticker(
                timestamp=datetime.fromtimestamp(float(data["E"]) / 1000),
                symbol=data["s"],
                close=float(data["c"]),
                open=float(data["o"]),
                high=float(data["h"]),
                low=float(data["l"]),
                volume=float(data["v"]),
                quote_asset_volume=float(data["q"]),
            )
            session.add(ticker)

    def query_ticker(self, symbol: str, start: datetime, end: datetime) -> List[dict]:
        """
        Query the ticker table for a given symbol and time range.

        Args:
            symbol (str): The symbol to query.
            start (datetime): The start of the time range.
            end (datetime): The end of the time range.

        Returns:
            List[dict]: A list of ticker data.
        """
        with self.session() as session:
            query = session.query(self.Ticker).filter(
                self.Ticker.symbol == symbol,
                self.Ticker.timestamp >= start,
                self.Ticker.timestamp <= end,
            )
            return [row.__dict__ for row in query.all()]


if __name__ == "__main__":
    db = SQLiteDB("database/test.sqlite")
    db.create_table(Table.LOG)
    db.create_table(Table.TICKER)
    db.log(INFO, "This is a test", datetime.now().timestamp())
    db.insert_ticker(
        {
            "e": "24hrMiniTicker",
            "E": datetime.now().timestamp() * 1000,
            "s": "BTCUSDT",
            "c": "30160.84000000",
            "o": "30734.00000000",
            "h": "30769.96000000",
            "l": "30009.00000000",
            "v": "36756.60526000",
            "q": "1116195819.19090940",
        }
    )
