# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# version.py
#
# Provides source code version information.
# ---------------------------------------------------------------------------

import hysplitdata
import hysplitplot
import logging


logger = logging.getLogger(__name__)


def print_version():
    logger.info("HYSPLITDATA version {}".format(hysplitdata.__version__))
    logger.info("HYSPLITPLOT version {}".format(hysplitplot.__version__))
