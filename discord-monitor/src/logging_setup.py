import logging, sys

def setup_logging(level: int = logging.INFO):
    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt))
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)
    logging.getLogger("discord.client").setLevel(logging.WARNING)
    logging.getLogger("asyncio_mqtt").setLevel(logging.WARNING)