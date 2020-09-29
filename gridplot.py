#!/usr/bin/env python3

# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# gridplot.py
#
# Produces grid plots from a cdump file.
#
# usage: python gridplot.py [OPTIONS] -iCDUMP
# ---------------------------------------------------------------------------

import logging
import os
import sys
import threading
from pandas.plotting import register_matplotlib_converters

import hysplitplot


# Register a converter to avoid a warning message.
register_matplotlib_converters()

logger = logging.getLogger(__name__)
the_plot = None
the_timer = None
call_refresh_overlay = True


def print_usage():

    print("""\
 Create postscript file to show concentration field evolution
 by using color fill of the concentration grid cells, designed
 especially for global grids.
 Science on a Sphere output assumes the concentration file is a
 global lat/lon grid.

 USAGE: gridplot -[options(default)]
   -a[scale: 0-linear, (1)-logarithmic]
   -b[Science on a Sphere output: (0)-No, 1-Yes)]
   -c[concentration/deposition multiplier (1.0)]
   -d[delta interval value (1000.0)]
   -f[(0), 1-ascii text output files for mapped values]
   -g[GIS: 0-none 1-GENERATE(log10) 2-GENERATE(value) 3-KML 4-partial KML]
   -h[height of level to display (m) (integer): (0 = dep)]
   -i[input file name (cdump.bin)]
   -j[graphics map background file name: (arlmap)]
   -k[KML options: 0-none 1-KML with no extra overlays]
   -l[lowest interval value (1.0E-36), -1 = use data minimum]
   -m[multi frames one file (0)] 
   -n[number of time periods: (0)-all, numb, min:max, -incr]
   -o[output name (plot.ps)]     
   -p[process output file name suffix]
   -r[deposition: (1)-each time, 2-sum]
   -s[species number to display: (1); 0-sum]
   -u[mass units (ie, kg, mg, etc)]
   -x[longitude offset (0), e.g., -90.0: U.S. center; 90.0: China center]
   -y[latitude center (0), e.g., 40.0: U.S. center]
   -z[zoom: (0=no zoom, 99=most zoom)]

   --debug                      print debug messages
   --interactive                show an interactive plot
   --more-formats=f1[,f2,...]   specify one or more additional output format(s)
                                where f1 = jpg, pdf, png, tif, etc.
   --source-time-zone           show local time at the source location
   --street-map[=n]             show street map in the background; n = 0 or 1.
   --time-zone=tz               show local time at a time zone; tz = US/Eastern, US/Central, etc.

 NOTE: leave no space between option and value""")


def refresh_overlay(event):
    the_plot.on_update_plot_extent()

    # next on_draw() should not call this.
    global call_refresh_overlay
    call_refresh_overlay = False
    event.canvas.draw()


def delayed_refresh_overlay(event):
    if the_plot.settings.interactive_mode:
        global the_timer
        if the_timer is not None:
            the_timer.cancel()
        the_timer = threading.Timer(the_plot.settings.street_map_update_delay,
                                    refresh_overlay,
                                    args=(event,))
        the_timer.start()
    else:
        refresh_overlay(event)


def on_draw(event):
    global call_refresh_overlay
    if call_refresh_overlay:
        # Consecutive on_draw() calls are contracted to one call.
        delayed_refresh_overlay(event)
    else:
        call_refresh_overlay = True


def on_resize(event):
    logger.debug("on_resize: event %s", event)
    logger.debug("canvas width %d, height %d (pixel)", event.width,
                 event.height)

    # Important to call canvas.draw() here to get spines of the initial
    # plot right.
    event.canvas.draw()


def main():
    global the_plot

    hysplitplot.print_version()
    the_plot = hysplitplot.GridPlot()

    the_plot.merge_plot_settings(None, sys.argv[1:])
    the_plot.read_custom_labels_if_exists()
    the_plot.read_data_files()

    logger.info("Started Grid Drawing")

    the_plot.draw({"resize_event": on_resize, "draw_event": on_draw})
    logger.info("Complete Gridplot: {}".format(the_plot.get_plot_count_str()))

    return 0


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print_usage()
        sys.exit(1)
    else:
        if "SHAPE_RESTORE_SHX" not in os.environ:
            # when reading a shapefile and its corresponding shx file is
            # missing, automatically generate the missing file.
            os.environ['SHAPE_RESTORE_SHX'] = 'YES'
        if sys.argv.count("--debug") > 0:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO
        hysplitplot.run(main, "GRIDPLOT", log_level=log_level)
