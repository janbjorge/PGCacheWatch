import logging
from typing import Final

logger: Final = logging.getLogger("pgcachewatch")
logger.addHandler(logging.NullHandler())
