from loguru import logger
from datetime import datetime
import sys


logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

logger.info("Initial logger setup complete.")


def setup_logger_from_config(console_level, file_level, log_dir):
    logger.remove()

    format_console = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    format_file = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{line: <3} - {message}"
    )

    logger.level("DEBUG", color="<blue>")
    logger.level("INFO", color="<green>")
    logger.level("WARNING", color="<yellow>")
    logger.level("ERROR", color="<red>")
    logger.level("CRITICAL", color="<bold red>")

    logger.add(sys.stdout, colorize=True, format=format_console, level=console_level)

    logger.add(
        f"{log_dir}/{{time:YYYY_MM_DD}}.log",
        format=format_file,
        level=file_level,
        rotation="00:00",
        retention="7 days"
    )

    logger.info("Logger setup from config complete.")
