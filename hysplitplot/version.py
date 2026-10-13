# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# version.py
#
# Provides source code version information.
# ---------------------------------------------------------------------------

import logging

import hysplitdata
from . import __version__

logger = logging.getLogger(__name__)


def print_version():
    logger.info("HYSPLITDATA version {}".format(hysplitdata.__version__))
    logger.info("HYSPLITPLOT version {}".format(__version__))
