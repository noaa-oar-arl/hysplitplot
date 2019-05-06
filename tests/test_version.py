import pytest
import hysplit4.version

def test_print_version():

    try:
        hysplit4.version.print_version()
    except:
        pytest.fail("unexpected exception")
