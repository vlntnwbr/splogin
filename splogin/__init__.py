import logging


class CredentialsException(BaseException):
    pass


def get_logger(name: str, level: int | str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter(
        "%(name)s - %(levelname)-8s - %(message)s"
    )
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger
