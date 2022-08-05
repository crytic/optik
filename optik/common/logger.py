import logging
import sys

# From https://stackoverflow.com/a/56944256
class ColoredFormatter(logging.Formatter):

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    blue = "\x1b[34m"
    green = "\x1b[32m"

    def colored_fmt(color: str, whole=False) -> str:
        reset = "\x1b[0m"
        if whole:
            return f"{color}%(asctime)s - %(levelname)s - %(message)s{reset}"
        return f"%(asctime)s - {color}%(levelname)s{reset} - %(message)s"

    FORMATS = {
        logging.DEBUG: colored_fmt(blue),
        logging.INFO: colored_fmt(green),
        logging.WARNING: colored_fmt(yellow),
        logging.ERROR: colored_fmt(red, whole=True),
        logging.CRITICAL: colored_fmt(bold_red, whole=True),
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


handler = logging.StreamHandler(sys.stdout)
logger = logging.getLogger("optik")
logger.setLevel(logging.DEBUG)
logger.propagate = False  # Otherwise slither duplicates Optik's logs


def init_logging(f: str = "stdout") -> None:
    """Initialize Optik's logger

    :param f: file where to write the logs. If 'stdout', logs are written
    to sys.stdout
    """
    global handler
    global logger
    if f == "stdout":
        handler = logging.StreamHandler(sys.stdout)
    else:
        handler = logging.FileHandler(f)
    handler.setFormatter(ColoredFormatter())
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)


def set_logging_level(lvl: int) -> None:
    """Set the logging level for Optik's logger"""
    global handler
    handler.setLevel(lvl)


def disable_logging() -> None:
    """Disable Optik's logger"""
    global logger
    logger.handlers = []
    logger.setLevel(logging.CRITICAL)
