import pytest

import hysplitplot.version

def test_print_version():

    try:
        hysplitplot.version.print_version()
    except:
        pytest.fail("unexpected exception")
