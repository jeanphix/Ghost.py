# -*- coding: utf-8 -*-
from datetime import datetime

from logging import (
    Filter,
    Formatter,
    getLogger,
)


class SenderFilter(Filter):
    def filter(self, record):
        record.sender = self.sender
        return True


class MillisecFormatter(Formatter):
    converter = datetime.fromtimestamp

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt is not None:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%Y-%m-%dT%H:%M:%S")
            s = "%s.%03dZ" % (t, record.msecs)
        return s


def configure(name, sender, level, handler=None):
    logger = getLogger(name)
    # Add `ghost_id` to formater
    ghost_filter = SenderFilter()
    ghost_filter.sender = sender
    logger.addFilter(ghost_filter)
    # Set the level
    logger.setLevel(level)
    # Configure handler formater
    formatter = MillisecFormatter(
        fmt='%(asctime)s [%(levelname)-8s] %(sender)s: %(message)s',
    )
    if handler is not None:
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
