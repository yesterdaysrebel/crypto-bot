import logging
import os
from datetime import datetime


def get_local_timezone():
    """Detect and return the device's local timezone"""
    return datetime.now().astimezone().tzinfo


class LocalTimezoneFormatter(logging.Formatter):
    """Custom formatter that uses device's local timezone for log timestamps"""
    def formatTime(self, record, datefmt=None):
        local_tz = get_local_timezone()
        ct = datetime.fromtimestamp(record.created, tz=local_tz)
        if datefmt:
            return ct.strftime(datefmt)
        return ct.strftime(self.default_time_format)


def setup_logging(level_name):
    log_level = getattr(logging, level_name.upper(), logging.INFO)
    logger = logging.getLogger("crypto_bot")
    if logger.handlers:
        return logger

    logger.setLevel(log_level)
    logger.propagate = False

    formatter = LocalTimezoneFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    os.makedirs("logs", exist_ok=True)
    file_handler = logging.FileHandler("logs/bot.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
