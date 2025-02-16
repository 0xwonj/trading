import logging
import logging.config
import os

# Define the base logging configuration template
BASE_LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "DEBUG",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}


def create_bot_logger(bot_name: str, log_dir: str = "logs") -> logging.Logger:
    """
    Create a logger instance specific to a bot.

    Args:
        bot_name: Name of the bot, used for both logger name and log file name
        log_dir: Directory where log files will be stored

    Returns:
        Logger instance configured for the specific bot
    """
    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)

    # Get or create the logger
    logger = logging.getLogger(f"bot.{bot_name}")

    # If the logger already has handlers, assume it's configured
    if logger.handlers:
        return logger

    # Create a copy of the base config
    bot_config = BASE_LOGGING_CONFIG.copy()

    # Add bot-specific file handler
    log_file = os.path.join(log_dir, f"{bot_name}.log")
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=10485760,  # 10MB
        backupCount=3,
        encoding="utf8",
    )
    file_handler.setFormatter(
        logging.Formatter(bot_config["formatters"]["standard"]["format"])
    )
    file_handler.setLevel(logging.INFO)

    # Add the file handler to the logger
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)

    return logger


def setup_logging():
    """
    Configure base logging using the defined dictionary.
    """
    logging.config.dictConfig(BASE_LOGGING_CONFIG)
