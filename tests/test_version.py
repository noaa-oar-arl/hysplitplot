# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_version.py
#
# Performs unit tests on functions and class methods declared in version.py.
# ---------------------------------------------------------------------------

import pytest

from ..hysplitplot import version

def test_print_version():

    try:
        version.print_version()
    except:
        pytest.fail("unexpected exception")
