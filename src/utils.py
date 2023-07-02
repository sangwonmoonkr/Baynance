import os
import logging

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from sqlite_db import SQLiteDB
from enums import Table


class BinanceLogger(logging.Logger):
    """
    logger class

    Args:
        logging (_type_): _description_
    """

    def __init__(self, db: SQLiteDB | None = None, slack_client: WebClient | None = None) -> None:
        super().__init__(__name__)
        self.setLevel(logging.DEBUG)
        if db is not None:
            self.addHandler(SQLiteHandler(db=db))
        if slack_client is not None:
            self.addHandler(SlackHandler(slack_client=slack_client))


class SQLiteHandler(logging.Handler):
    """
    Logging handler for SQLite.
    """

    def __init__(self, db: SQLiteDB) -> None:
        logging.Handler.__init__(self)
        self.database = db
        self.database.create_table(Table.LOG)

    def emit(self, record: logging.LogRecord) -> None:
        self.database.log(record.levelname, record.msg, record.created)


class SlackHandler(logging.Handler):
    """
    Logging handler for Slack.
    """

    def __init__(self, slack_client: WebClient) -> None:
        logging.Handler.__init__(self)
        self.slack_channel_id = os.getenv("SLACK_CHANNEL", "#general")
        self.client = slack_client

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a record.
        Only send messages with level >= INFO.

        Args:
            record (logging.LogRecord): The record to be logged
        """
        if record.levelno < logging.INFO:
            return
        text = f"{record.levelname}: {record.msg}"
        try:
            self.client.chat_postMessage(channel=self.slack_channel_id, text=text)
        except SlackApiError as slack_error:
            print(f"Slack Error: {slack_error.response['error']}")
