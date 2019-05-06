# trajplot.py

import logging
import os
import sys
import hysplit4


logger = logging.getLogger(__name__)
the_plot = None


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
   -m[Map proj: (0)-Auto 1-Polar 2-Lambert 3-Merc 4-CylEqu]'
   -o[Output file name: (trajplot.ps)]'
   -p[Process file name suffix: (ps) or process ID]'
   -s[Symbol at trajectory origin: 0-no (1)-yes]'
   -v[Vertical: 0-pressure (1)-agl, 2-theta 3-meteo 4-none]'
   -z[Zoom factor:  0-least zoom, (50), 100-most zoom]'
   
 NOTE: leave no space between option and value""")


def on_resize(event):
    logger.debug("on_resize: event %s", event)
    logger.debug("canvas width %d, height %d (pixel)", event.width, event.height)

    # Important to call canvas.draw() here to get spines of the initial plot right.
    event.canvas.draw()

    the_plot.update_gridlines()


def main():
    global the_plot

    the_plot = hysplit4.TrajectoryPlot()

    # omit the program name from the arguments
    #the_plot.merge_plot_settings("default_tplot", sys.argv[1:])
    the_plot.merge_plot_settings(None, sys.argv[1:])
    the_plot.read_custom_labels_if_exists(the_plot.make_labels_filename())
    the_plot.read_data_files()

    logger.info("Started Trajectory Drawing")
    hysplit4.print_version()

    the_plot.read_background_map()

    the_plot.layout({"resize_event" : on_resize})
    the_plot.draw()

    return 0


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print_usage()
        sys.exit(1)
    else:
        if "SHAPE_RESTORE_SHX" not in os.environ:
            # when reading a shapefile and its corresponding shx file is missing,
            # automatically generate the missing file.
            os.environ['SHAPE_RESTORE_SHX']='YES'
        hysplit4.run(main, "TRAJPLOT")
