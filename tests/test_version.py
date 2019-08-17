# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_version.py
#
# Performs unit tests on functions and class methods declared in version.py.
# ---------------------------------------------------------------------------

import pytest

import hysplitplot.version

def test_print_version():

    try:
        hysplitplot.version.print_version()
    except:
        pytest.fail("unexpected exception")
