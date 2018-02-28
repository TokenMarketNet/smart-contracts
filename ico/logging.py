import logging
import sys
import os


def setup_console_logging(log_level=None):
    """Setup console logging.

    Aimed to give easy sane defaults for loggig in command line applications.

    Don't use logging settings from INI, but use hardcoded defaults.
    """

    formatter = logging.Formatter("[%(asctime)s] [%(name)s] %(message)s")  # same as default

    # setup `RainbowLoggingHandler`
    # and quiet some logs for the test output
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.handlers = [handler]

    # Allow log level override by environment variable
    env_level = os.environ.get("LOG_LEVEL", "info")
    log_level = log_level or getattr(logging, env_level.upper())
    logger.setLevel(log_level)

    # Limit dependency package noisiness
    logger = logging.getLogger("requests.packages.urllib3.connectionpool")
    logger.setLevel(logging.ERROR)

    logger = logging.getLogger("anyconfig")
    logger.setLevel(logging.ERROR)

    logger = logging.getLogger("populus.compilation")
    logger.setLevel(logging.ERROR)
