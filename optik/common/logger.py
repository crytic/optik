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
        else:
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


logger = logging.getLogger("optik")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(ColoredFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)
