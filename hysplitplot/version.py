# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# version.py
#
# Provides source code version information.
# ---------------------------------------------------------------------------

import hysplitdata
from . import __version__
import logging

logger = logging.getLogger(__name__)


def print_version():
    logger.info("HYSPLITDATA version {}".format(hysplitdata.__version__))
    logger.info("HYSPLITPLOT version {}".format(__version__))
