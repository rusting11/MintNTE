#logui.py
#Github\NTE_boheAI\UI\logui.py
import logging
from logging.handlers import RotatingFileHandler
import sys

_logger = None

def setup_logging(log_file="nte_bohe.log", console_level=logging.INFO, file_level=logging.DEBUG):
    global _logger
    if _logger is not None:
        return _logger
    logger = logging.getLogger("NTE_Bohe")
    logger.setLevel(logging.DEBUG)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(console_level)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
    console.setFormatter(console_format)
    logger.addHandler(console)

    with open(log_file, "w", encoding="utf-8"):
        pass
    file_handler = RotatingFileHandler(log_file, maxBytes=2*1024*1024, backupCount=3, encoding='utf-8')
    file_handler.setLevel(file_level)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    _logger = logger
    return logger

def get_logger():
    if _logger is None:
        setup_logging()
    return _logger

def info(msg):
    get_logger().info(msg)

def error(msg):
    get_logger().error(msg)

def warning(msg):
    get_logger().warning(msg)

def debug(msg):
    get_logger().debug(msg)

def critical(msg):
    get_logger().critical(msg)