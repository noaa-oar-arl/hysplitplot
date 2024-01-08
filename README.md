# HYSPLITPLOT

The HYSPLITPLOT package provides Python classes for creating plots using
the results from HYSPLIT trajectory/dispersion runs. The source code is
written using Python 3 and the package requires external packages to run:
please see setup.py for the required external packages. HYSPLITPLOT is part of
a precompiled HYSPLIT distribution. For detailed installation instructions,
refer to https://www.ready.noaa.gov/documents/Tutorial/html/disp_python.html.

To upgrade HYSPLITPLOT that is installed along with your HYSPLIT distribution,
first activate the hysplit anaconda environment:

    $ conda activate hysplit

then execute the setup.py script as shown below

    $ python setup.py install

To verify the installation is correctly done, run unit tests. The unit tests for
HYSPLITPLOT are written using the pytest framework. pytest is installed when python
packages are installed for HYSPLIT. To run the unit tests, change directory
to the tests subdirectory and run pytest:

    $ cd tests
    $ pytest

No error should have occurred. There may be warning messages but they may be ignored.

To plot a trajectory dump file, say, tdump in the current directory,
run

    $ python ~/hysplitplot/trajplot.py -itdump

It is assumed that hysplitplot is unpacked at the top-level of your home
directory.  If the hysplitplot directory is located elsewhere, use that path
to run trajplot.py.  The command-line arguments for the trajplot.py script
have the same format and meaning as the TRAJPLOT program in HYSPLIT.
