# hysplit_graf

This project is to replace the postscript graphics of HYSPLIT with Python
graphics.  The source code is written using Python 3.7 and it requires a few
external packages.  See setup.py for the external packages that are required.

To install this package, run

    $ python setup.py install

To generate a trajectory plot using a trajectory dump file, say, tdump found
in HYSPLIT's working directory, run

    $ python ~/hysplit_graf/trajplot.py -itdump

It is assumed that hysplit_graf is unpacked at the top-level of your home
directory.  If the hysplit_graf directory is located elsewhere, use that path
to run trajplot.py.  The command-line arguments for the trajplot.py script
have the same format and meaning as the TRAJPLOT program in HYSPLIT.

Unit tests are written using the pytest framework. You will need to install
pytest if it is not.  To run the unit tests, do

    $ cd tests
    $ pytest
    
To update the HTML documentation, go to the docs/ directory and execute

    $ make html

The updated document can be accessed by pointing a web browser to
docs/build/html/index.html.  Please note that the documentation is a working
progress and it will stay incomplete until the source code matures.
