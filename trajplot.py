#!/usr/bin/env python3

# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# trajplot.py
#
# Produces trajectory plots from one or more tdump files.
#
# usage: python trajplot.py [OPTIONS] -iTDUMP
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
 USAGE: trajplot -[options (default)]
   -a[GIS output: (0)-none 1-GENERATE_points 3-KML 4-partial_KML 5-GENERATE_lines]'
   -A[KML options: 0-none 1-no extra overlays 2-no endpoints 3-Both 1&2]'
   -e[End hour to plot: #, (all) ]'
   -f[Frames: (0)-all files on one  1-one per file]'
   -g[Circle overlay: ( )-auto, #circ(4), #circ:dist_km]'
   -h[Hold map at center lat-lon: (source point), lat:lon]'
   -i[Input files: name1+name2+... or +listfile or (tdump)]'
   -j[Map background file: (arlmap) or shapefiles.<(txt)|process suffix>]'
   -k[Kolor: 0-B&W, (1)-Color, N:colortraj1,...colortrajN]'
      1=red,2=blue,3=green,4=cyan,5=magenta,6=yellow,7=olive'
   -l[Label interval: ... -12, -6, 0, (6), 12, ... hrs '
      <0=with respect to traj start, >0=synoptic times)]'
   -L[LatLonLabels: none=0 auto=(1) set=2:value(tenths)]'
   -m[Map proj: (0)-Auto 1-Polar 2-Lambert 3-Merc 4-CylEqu 5-WebMerc]'
   -o[Output file name: (trajplot.ps)]'
   -p[Process file name suffix: (ps) or process ID]'
   -s[Symbol at trajectory origin: 0-no (1)-yes]'
   -v[Vertical: 0-pressure (1)-agl, 2-theta 3-meteo 4-none]'
   -z[Zoom factor:  0-least zoom, (50), 100-most zoom]'

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
    the_plot = hysplitplot.TrajectoryPlot()

    the_plot.merge_plot_settings(None, sys.argv[1:])
    the_plot.read_custom_labels_if_exists()
    the_plot.read_data_files()

    logger.info("Started Trajectory Drawing")

    the_plot.draw({"resize_event": on_resize, "draw_event": on_draw})

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
        hysplitplot.run(main, "TRAJPLOT", log_level=log_level)
