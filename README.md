# hysplitplot

This project is to replace the postscript graphics of HYSPLIT with Python
graphics.  The source code is written using Python 3.7 and it requires a few
external packages.  See setup.py for the external packages that are required.

To install this package, run

    $ python setup.py install

A timezonefinder database including oceans is necessary to determine the
timezone at a given latitude and longitude location. You would need to
download a geojson file, say, timezones-with-oceans.geojson.zip. Here are
steps to update the timezone database:

    $ mkdir ~/timezones
    $ cd ~/timezones
    $ unzip timezones-with-oceans.geojson.zip

Rename your geojson file to combined.json or create a symbolic link.
Note that the actual path and/or name of your geojson file might be different.

    $ ln -s dist/timezones-with-oceans.geojson combined.json

Run the timezone file converter:

    $ python -m timezonefinder.file_converter

Copy all *.bin files and timezone_names.json to where the timezonefinder
module is installed. (On the author's Linux computer, the destination was
~/anaconda3/envs/hysplit/lib/python3.7/site-packages/timezonefinder-4.1.0-py3.7.egg/timezonefinder.)

To generate a trajectory plot using a trajectory dump file, say, tdump found
in HYSPLIT's working directory, run

    $ python ~/hysplitplot/trajplot.py -itdump

It is assumed that hysplitplot is unpacked at the top-level of your home
directory.  If the hysplitplot directory is located elsewhere, use that path
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
