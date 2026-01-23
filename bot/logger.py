import logging
import os


def setup_logging(level_name):
    log_level = getattr(logging, level_name.upper(), logging.INFO)
    logger = logging.getLogger("crypto_bot")
    if logger.handlers:
        return logger

    logger.setLevel(log_level)
    logger.propagate = False

    formatter = logging.Formatter(
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
