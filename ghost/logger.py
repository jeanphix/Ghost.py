# -*- coding: utf-8 -*-
from logging import (
    Filter,
    Formatter,
    getLogger,
)


class SenderFilter(Filter):
    def filter(self, record):
        record.sender = self.sender
        return True


def configure(name, sender, level, handler):
    logger = getLogger(name)
    # Add `ghost_id` to formater
    ghost_filter = SenderFilter()
    ghost_filter.sender = sender
    logger.addFilter(ghost_filter)
    # Set the level
    logger.setLevel(level)
    # Configure handler formater
    formatter = Formatter(
        '%(asctime)s %(sender)s: %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S.%s',
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
