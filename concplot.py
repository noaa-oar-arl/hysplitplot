#!/usr/bin/env python3

# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# concplot.py
#
# Produces concentration plots from a cdump file.
#
# usage: python concplot.py [OPTIONS] -iCDUMP
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
 USAGE: concplot -[options (default)]
   -a[Arcview GIS: 0-none 1-log10 2-value 3-KML 4-partial KML]
   +a[KML altitude mode: (0)-clampedToGround, 1-relativeToGround]
   -A[KML options: 0-none 1-KML with no extra overlays]
   -b[Bottom display level: (0) m]
   -c[Contours: (0)-dyn/exp 1-fix/exp 2-dyn/lin 3-fix/lin 4-set 50-0,interval 10 51-1,interval 10]
   -d[Display: (1)-by level, 2-levels averaged]
   -e[Exposure units flag: (0)-concentrations, 1-exposure, 2-chemical threshold,
                                 3-hypothetical volcanic ash, 4-mass loading]
   -f[Frames: (0)-all frames one file, 1-one frame per file]
   -g[Circle overlay: ( )-auto, #circ(4), #circ:dist_km]
   -h[Hold map at center lat-lon: (source point), lat:lon]
   -i[Input file name: (cdump)]
   -j[Graphics map background file name: (arlmap) or shapefiles.<(txt)|process suffix>]
   -k[Kolor: 0-B&W, (1)-Color, 2-No Lines Color, 3-No Lines B&W]
   -l[Label options: ascii code, (73)-open star]
   +l[Use THIS IS A TEST label: (0)-no, 1-yes]
   -L[LatLonLabels: none=0 auto=(1) set=2:value(tenths)]
   -m[Map projection: (0)-Auto 1-Polar 2-Lamb 3-Merc 4-CylEqu 5-WebMerc]
   +m[Maximum square value: 0=none, (1)=both, 2=value, 3=square]
   -n[Number of time periods: (0)-all, numb, min:max, -incr]
   -o[Output file name: (concplot.ps)]
   -p[Process file name suffix: (ps) or process ID]
   -q[Quick data plot: ( )-none, filename]
   -r[Removal: 0-none, (1)-each time, 2-sum, 3-total]
   -s[Species: 0-sum, (1)-select, #-multiple]
   -t[Top display level: (99999) m]
   -u[Units label for mass: (mass), see "labels.cfg" file]
   -v[Values[:labels:RRRGGGBBB color (optional,but must have 2 colons to specify color without label)
        for <= 25 fixed contours: val1:lab1:RGB1+val2:lab2:RGB2+val3:lab3:RGB3+val4:lab4:RGB4]
   -w[Grid point scan for contour smoothing (0)-none 1,2,3, grid points]
   -x[Concentration multiplier: (1.0)]
   -y[Deposition multiplier:    (1.0)]
   -z[Zoom factor: 0-least zoom, (50), 100-most zoom]
   -1[Minimum concentration contour value when -c=0 or 1: (0.0)-none, ( )-value]
   -2[Minimum deposition contour value when -c=0 or 1: (0.0)-none, ( )-value]
   -3[Allow colors to change for dynamic contours (-c=0 or 2): (0)-no, 1-yes]
   -4[Plot below threshold minimum contour for chemical output (-e=2): (0)-no, 1-yes]
   -5[Use -o prefix name for output kml file when -a=3 or 4: (0)-no, 1-yes]
   -8[Create map(s) even if all values zero: (0)-no, 1-yes]
   -9[Force sample start time label to start of release: (0)-no, 1-yes]

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
    the_plot = hysplitplot.ConcentrationPlot()

    the_plot.merge_plot_settings(None, sys.argv[1:])
    the_plot.read_custom_labels_if_exists()
    the_plot.read_data_files()

    logger.info("Started Concentration Drawing")

    the_plot.draw({"resize_event": on_resize, "draw_event": on_draw})
    logger.info("Complete Concplot: {}".format(the_plot.get_plot_count_str()))

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
        hysplitplot.run(main, "CONCPLOT", log_level=log_level)
