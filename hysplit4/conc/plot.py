import logging
import os
import sys
import geopandas
import math
import numpy
import matplotlib.gridspec
import matplotlib.pyplot as plt

from hysplit4 import cmdline, util, const, plotbase, mapbox, mapproj, io, smooth
from hysplit4.conc import model, prop
from builtins import str


logger = logging.getLogger(__name__)


class ConcentrationPlotSettings(plotbase.AbstractPlotSettings):
    
    def __init__(self):
        plotbase.AbstractPlotSettings.__init__(self)

        self.input_file = "cdump"
        self.output_postscript = "concplot.ps"
        self.output_basename = "concplot"
        
        # Index of the selected pollutant. It is 1-based for now but it will be changed to 0-based.
        # If the index is -1 after the change, all pollutants are selected. 
        self.pollutant_index = 1
        
        self.first_time_index = 1   # 1-based index for now. 
        self.last_time_index = 9999 # 1-based index for now. 
        self.time_index_step = 1
        self.contour_level_generator = const.ContourLevelGenerator.EXPONENTIAL_DYNAMIC
        self.QFILE = "undefined"
        self.source_label = "\u2606"    # open star
        self.this_is_test = 0
        self.LEVEL1 = 0 # bottom display level defaults to deposition surface
        self.LEVEL2 = 99999 # top level default to whole model atmosphere
        self.exposure_unit = const.ExposureUnit.CONC
        self.KAVG = const.ConcentrationType.EACH_LEVEL
        self.NDEP = const.DepositionSum.TIME
        self.show_max_conc = 1
        self.default_mass_unit = "mass"
        self.smoothing_distance = 0
        self.CONADJ = 1.0   # conc unit conversion multiplication factor
        self.DEPADJ = 1.0   # deposition unit conversion multiplication factor
        self.UCMIN = 0.0    # min conc value
        self.UDMIN = 0.0    # min deposition value
        self.IDYNC = 0      # allow colors to change for dyn contours?
        self.KHEMIN = 0     # plot below threshold contour for chemical output
        self.IZRO = 0       # create map(s) even if all values are zero
        self.NSSLBL = 0     # force sample start time label to start of release
        self.color = const.ConcentrationPlotColor.COLOR
        
        # internally defined
        self.label_source = False
        self.source_marker = "*"
        self.source_marker_color= "r"     # red
        self.source_marker_size = 8*8
        self.user_color = False
        self.user_label = False
        self.contour_levels = None
        self.contour_level_count = 4
        self.pollutant = ""         # name of the selected pollutant
        self.SCALE = 1.0
        self.station_marker = "o"
        self.station_marker_color= "k"     # black
        self.station_marker_size = 6*6
        
    def dump(self, stream):
        """Dumps the settings to an output stream.

        """
        stream.write("----- begin ConcentrationPlotSettings\n")
        for k, v in self.__dict__.items():
            stream.write("{0} = {1}\n".format(k, v))
        stream.write("----- end ConcentrationPlotSettings\n")

    def process_command_line_arguments(self, args0):
        """Processes command-line arguments and updates settings.

        :param args0: arguments excluding the program name.
        """
        args = cmdline.CommandLineArguments(args0)
        
        # process options common to trajplot, concplot, etc.
        self._process_cmdline_args(args0)
    
        self.contour_level_generator = args.get_integer_value(["-c", "-C"], self.contour_level_generator)
        self.input_file              = args.get_string_value(["-i", "-I"], self.input_file)
        
        if args.has_arg("-l"):
            self.source_label = self.parse_source_label(args.get_value("-l"))
            self.label_source = True
        
        if args.has_arg(["-k", "-K"]):
            self.color= args.get_integer_value(["-k", "-K"], self.color)
            self.color= max(0, min(3, self.color))

        if args.has_arg("+l"):
            self.this_is_test = args.get_integer_value("+l", self.this_is_test)
            self.this_is_test = max(0, min(1, self.this_is_test))
 
        if args.has_arg(["-n", "-N"]):
            self.parse_time_indices(args.get_value(["-n", "-N"]))
        self.first_time_index -= 1      # to 0-based indices
        self.last_time_index -= 1
        
        self.QFILE                   = args.get_string_value(["-q", "-Q"], self.QFILE)
        
        self.pollutant_index = args.get_integer_value(["-s", "-S"], self.pollutant_index)
        self.pollutant_index -= 1       # to 0-based index
        
        self.LEVEL1 = args.get_integer_value(["-b", "-B"], self.LEVEL1)
        self.LEVEL1 = max(0, self.LEVEL1)
        
        self.LEVEL2 = args.get_integer_value(["-t", "-T"], self.LEVEL2)
        self.LEVEL2 = max(0, self.LEVEL2)
        
        if self.LEVEL1 > self.LEVEL2:
            self.LEVEL1, self.LEVEL2 = self.LEVEL2, self.LEVEL1

        self.exposure_unit = args.get_integer_value(["-e", "-E"], self.exposure_unit)
        self.exposure_unit = max(0, min(4, self.exposure_unit))
        
        self.KAVG = args.get_integer_value(["-d", "-D"], self.KAVG)
        self.KAVG = max(1, min(2, self.KAVG))
        
        self.NDEP = args.get_integer_value(["-r", "-R"], self.NDEP)
        self.NDEP = max(0, min(3, self.NDEP))
        
        self.show_max_conc = args.get_integer_value(["+m", "+M"], self.show_max_conc)
        self.show_max_conc = max(0, min(3, self.show_max_conc))
        
        self.default_mass_unit = args.get_string_value(["-u", "-U"], self.default_mass_unit)
        
        self.smoothing_distance = args.get_integer_value(["-w", "-W"], self.smoothing_distance)
        self.smoothing_distance = max(0, min(99, self.smoothing_distance))
        
        self.CONADJ = args.get_float_value(["-x", "-X"], self.CONADJ)
        self.DEPADJ = args.get_float_value(["-y", "-Y"], self.DEPADJ)
        self.UCMIN = args.get_float_value("-1", self.UCMIN)
        self.UDMIN = args.get_float_value("-2", self.UDMIN)
        self.IDYNC = args.get_integer_value("-3", self.IDYNC)
        self.KHEMIN = args.get_integer_value("-4", self.KHEMIN)
        self.IZRO = args.get_integer_value("-8", self.IZRO)
        self.NSSLBL = args.get_integer_value("-9", self.NSSLBL)
        
        if args.has_arg("-v"):
            self.parse_contour_levels(args.get_value("-v"))
            self.contour_level_generator = const.ContourLevelGenerator.USER_SPECIFIED
  
    @staticmethod
    def parse_source_label(str):
        c = int(str)
        if c == 72:
            return "*"
        elif c == 73:
            return "\u2606"    # open star
        else:
            return chr(c)
        
    def parse_time_indices(self, str):
        if str.count(":") > 0:
            divider = str.index(":")
            self.first_time_index = int(str[:divider]) 
            self.last_time_index = int(str[divider+1:])
            if self.first_time_index > self.last_time_index:
                self.first_time_index = 1
        else:
            self.last_time_index = int(str)
            if self.last_time_index < 0:
                self.time_index_step = abs(self.last_time_index)
                self.last_time_index = 9999

    def parse_contour_levels(self, str):
        if str.count(":") > 0:
            self.contour_levels = self.parse_labeled_contour_levels(str)
            self.user_label = True
            if len(self.contour_levels) > 1:
                self.user_color = True
        else:
            l = self.parse_simple_contour_levels(str)
            self.contour_levels = [LabelledContourLevel(v) for v in l]
      
        self.contour_level_count = len(self.contour_levels)
        
        # sort by contour level
        if self.user_color:
            self.contour_levels = sorted(self.contour_levels, key=lambda o: o.level)
                
    @staticmethod
    def parse_simple_contour_levels(str):
        """Parse a string that contains floating-point values separated by '+' and return the values
        
        For example, an input of '1E+3+100+10' returns [1000.0, 100.0, 10.0].
        """
        f = []
        
        tokens = str.split("+")
        
        k = 0
        while k < len(tokens):
            if tokens[k][-1].upper() == "E":
                t = tokens[k] + tokens[k+1]
                k += 1
            else:
                t = tokens[k]
            f.append(float(t))
            k += 1
        
        return f

    @staticmethod
    def parse_labeled_contour_levels(str):
        """Parse a string that contains contour levels, colors, and labels and 
        return a list of ContourLevel objects.
        
        For example, an input of '10E+2:USER1:100050200+10E+3:USER2:100070200' returns
        two ContourLevel objects with respective contour levels 1000.0 and 10000.0.
        """
        list = []
        
        tokens = str.split("+")
        
        k = 0
        while k < len(tokens):
            if tokens[k][-1].upper() == "E":
                s = tokens[k] + tokens[k+1]
                k += 1
            else:
                s = tokens[k]
                
            a = s.split(":")
            
            o = LabelledContourLevel()
            o.level = float(a[0])
            o.label = a[1]
            if len(a) > 2:
                o.r = int(a[2][0:3]) / 255.0
                o.g = int(a[2][3:6]) / 255.0
                o.b = int(a[2][6:9]) / 255.0
            
            list.append(o)    
            k += 1
            
        return list

    def get_reader(self):
        return ConcentrationPlotSettingsReader(self)
    
class ConcentrationPlotSettingsReader:
    
    def __init__(self, settings):
        self.settings = settings
        
    def read(self, filename):
        logger.debug("reading text file %s", filename)
        with open(filename, "r") as f:
            lines = f.read().splitlines()
            f.close()

        s = self.settings
    
        s.map_background = lines[0]
        s.map_projection = int(lines[1])
        # num_polid, l 3
        s.zoom_factor = s.parse_zoom_factor(lines[3])
        s.color = int(lines[4]) # 1 or 0
        # cval, l 6
        # fixed, l 7
        # cscale, l 8
        # dscale, l 9
        # smooth, l 10
        # remove, l 11
        # expose, l 12
        # frame, l 13
        # mass, l 14
        s.ring = util.convert_int_to_bool(int(lines[14])) # 1 or 0
        s.map_center = int(lines[15]) # 1 or 0
        s.ring_number = int(lines[16])
        s.ring_distance = float(lines[17])
        # qpnt, l 19
        s.center_loc[1] = float(lines[19])
        s.center_loc[0] = float(lines[20])
        
        return s


class ConcentrationPlot(plotbase.AbstractPlot):

    MAX_CONTOUR_LEVELS = 32
    
    def __init__(self):
        plotbase.AbstractPlot.__init__(self)
        self.settings = ConcentrationPlotSettings()
        self.cdump = None
        self.data_properties = None
        self.time_selector = None
        self.level_selector = None
        self.pollutant_selector = None
        self.smoothing_kernel = None
        
        self.fig = None
        self.conc_outer = None
        self.conc_axes = None
        self.legends_axes = None
        self.text_axes = None
  
    def merge_plot_settings(self, filename, args):
        if filename is not None:
            self.settings.get_reader().read(filename)
        self.settings.process_command_line_arguments(args)
          
    def update_gridlines(self):
        self._update_gridlines(self.conc_axes,
                               self.settings.map_color,
                               self.settings.lat_lon_label_interval_option,
                               self.settings.lat_lon_label_interval)
        return
    
    def read_data_files(self):
        if not os.path.exists(self.settings.input_file):
            raise Exception("File not found: {0}".format(self.settings.input_file))
        
        # read only one file.
        self.cdump = c = model.ConcentrationDump()
        r = c.get_reader()
        r.read(self.settings.input_file)
       
        # create selectors               
        self.time_selector = prop.TimeIndexSelector(self.settings.first_time_index,
                                                    self.settings.last_time_index,
                                                    self.settings.time_index_step)
        self.pollutant_selector = prop.PollutantSelector(self.settings.pollutant_index)
        self.level_selector = prop.VerticalLevelSelector(self.settings.LEVEL1, self.settings.LEVEL2)

        # limit time indices. assume that last conc grid is the largest time index.
        self.time_selector.normalize(c.conc_grids[-1].time_index)
        logger.debug("time iteration is limited to index range [%d, %d]",
                     self.time_selector.first, self.time_selector.last)

        # normalize pollutant index
        self.pollutant_selector.normalize(len(c.pollutants) - 1)
        self.settings.pollutant_index = self.pollutant_selector.index
        self.settings.pollutant = "SUM" if self.settings.pollutant_index == -1 else c.pollutants[self.settings.pollutant_index]

        if len(c.pollutants) > 1:
            logger.info("Multiple pollutant species in file")
            for k, name in enumerate(c.pollutants):
                if k == self.settings.pollutant_index:
                    logger.info("%d - %s <--- selected", k+1, name)
                else:
                    logger.info("%d - %s", k+1, name)
        
        # if only one non-depositing level, change -d2 to -d1.
        if self.settings.KAVG == const.ConcentrationType.VERTICAL_AVERAGE:
            if len(c.release_heights) == 1 or (len(c.release_heights) == 2 and c.release_heights[0] == 0):
                logger.warning("Changing -d2 to -d1 since single layer")
                self.settings.KAVG = const.ConcentrationType.EACH_LEVEL
        
        self.data_properties = self._post_file_processing(self.cdump)
        
        if self.settings.smoothing_distance > 0:
            self.smoothing_kernel = smooth.SmoothingKernelFactory.create_instance(const.SmoothingKernel.SIMPLE, self.settings.smoothing_distance)
            
    def _post_file_processing(self, cdump):
        
        p = prop.ConcentrationDumpProperty(cdump)
        vavg_calc = prop.VerticalAverageCalculator(cdump, self.level_selector)
        
        # find min and max values
        for t_index in self.time_selector:
            t_grids = prop.TimeIndexGridFilter(cdump.conc_grids,
                                               prop.TimeIndexSelector(t_index, t_index))
            
            if self.settings.KAVG == const.ConcentrationType.VERTICAL_AVERAGE:
                v_grids = prop.sum_over_pollutants_per_level(t_grids,
                                                             self.level_selector,
                                                             self.pollutant_selector)
                v_avg = vavg_calc.average(v_grids)
                min, max = prop.find_nonzero_min_max(v_avg)
                p.update_average_min_max(min, max)
            
            for g in t_grids:
                min, max = prop.find_nonzero_min_max(g.conc)
                p.update_min_max_at_level(min, max, g.vert_level_index)
        
        p.scale_conc(self.settings.KAVG,
                     self.settings.CONADJ,
                     self.settings.DEPADJ)
        
        self._normalize_settings(cdump)
            
        return p

    def _normalize_settings(self, cdump):
        s = self.settings
        
        if s.LEVEL1 < cdump.vert_levels[0]:
            s.LEVEL1 = cdump.vert_levels[0]
        if s.LEVEL2 > cdump.vert_levels[-1]:
            s.LEVEL2 = cdump.vert_levels[-1]
        logger.debug("normalized LEVELs to %f, %f", s.LEVEL1, s.LEVEL2)
        
        if s.contour_level_generator > const.ContourLevelGenerator.EXPONENTIAL_FIXED:
            s.UCMIN = 0.0
            s.UDMIN = 0.0
        
        if s.exposure_unit == const.ExposureUnit.CHEM_THRESHOLDS:
            s.KMAP = const.ConcentrationMapType.THRESHOLD_LEVELS #4
        elif s.exposure_unit == const.ExposureUnit.VA:
            s.KMAP = const.ConcentrationMapType.VOCANIC_ERUPTION #5
        elif s.exposure_unit == const.ExposureUnit.VAL_4:
            s.KMAP = const.ConcentrationMapType.MASS_LOADING #7
        else:
            s.KMAP = s.exposure_unit + 1

    @staticmethod
    def _fix_map_color(clr, color_mode):
        return clr if color_mode != const.ConcentrationPlotColor.BLACK_AND_WHITE else 'k'

    def read_background_map(self):
        self.background_maps = self.load_background_map(self.settings.map_background)

    def layout(self, ev_handlers=None):

        self._initialize_map_projection()

        fig = plt.figure(
            figsize=(8.5, 11.0),  # letter size
            clear=True,  # clear an existing figure
            constrained_layout=False
        )

        outer_grid = matplotlib.gridspec.GridSpec(2, 1,
                                                  wspace=0.0, hspace=0.05,
                                                  width_ratios=[1.0], height_ratios=[3.25, 1.50])

        inner_grid = matplotlib.gridspec.GridSpecFromSubplotSpec(1, 2,
                                                                 wspace=0.05, hspace=0.0,
                                                                 width_ratios=[8, 2], height_ratios=[1],
                                                                 subplot_spec=outer_grid[0, 0])

        self.fig = fig
        self.conc_outer = fig.add_subplot(outer_grid[0, 0])
        self.conc_axes = fig.add_subplot(inner_grid[0, 0], projection=self.crs)
        self.legends_axes = fig.add_subplot(inner_grid[0, 1])
        self.text_axes = fig.add_subplot(outer_grid[1, 0])

        if ev_handlers is not None:
            self._connect_event_handlers(ev_handlers)
    
    def make_plot_title(self, conc_grid):
        fig_title = self.labels.get("TITLE")
        
        fig_title += "\nTODO"
        
        fig_title += conc_grid.starting_datetime.strftime("\nIntegrated from %H%M %d %b to")
        fig_title += conc_grid.ending_datetime.strftime(" %H%M %d %b %y (UTC)")
        if not conc_grid.is_forward_calculation():
            fig_title += " [backward]"           
        
        pollutant = self.settings.pollutant if self.settings.pollutant_index == -1 else conc_grid.pollutant
        
        if not conc_grid.is_forward_calculation():
            fig_title += "\n{0} Calculation started at".format(pollutant)
        else:
            fig_title += "\n{0} Release started at".format(pollutant)
        fig_title += conc_grid.parent.release_datetime[0].strftime(" %H%M %d %b %y (UTC)")
        
        return fig_title
    
    @staticmethod
    def make_ylabel(cdump, marker):
        y_label = "Source {0} at".format(marker)

        release_locs = cdump.get_unique_start_locations()
        if len(release_locs) == 1:
            lon, lat = release_locs[0]
            y_label += "  {0:5.2f} {1}".format(abs(lat), "N" if lat >= 0 else "S")
            y_label += "  {0:6.2f} {1}".format(abs(lon), "E" if lon >= 0 else "W")
        else:
            y_label += " multiple locations"

        release_heights = cdump.get_unique_start_levels()
        if len(release_heights) == 1:
            height_min = util.nearest_int(release_heights[0])
            y_label += "      from {0} m".format(height_min) # TODO: m or ft
        else:
            height_min = util.nearest_int(min(release_heights))
            height_max = util.nearest_int(max(release_heights))
            y_label += "      from {0} to {1} m".format(height_min, height_max) # TODO: m or ft
        
        logger.debug("using ylabel %s", y_label)
        return y_label
    
    def _initialize_map_projection(self):
        map_opt_passes = 1 if self.settings.ring_number == 0 else 2
        map_box = self._determine_map_limits(self.cdump, map_opt_passes)

        if self.settings.center_loc == [0.0, 0.0]:
            self.settings.center_loc = self.cdump.release_locs[0]

        if self.settings.ring and self.settings.ring_number >= 0:
            map_box.determine_plume_extent()
            map_box.clear_hit_map()
            map_box.set_ring_extent(self.settings)

        self.projection = mapproj.MapProjectionFactory.create_instance(self.settings.map_projection,
                                                                       self.settings.zoom_factor,
                                                                       self.settings.center_loc,
                                                                       self.settings.SCALE,
                                                                       (map_box.grid_delta, map_box.grid_delta),
                                                                       map_box)
        self.projection.refine_corners(self.settings.center_loc)

        # map projection might have changed.
        self.settings.map_projection = self.projection.proj_type

        self.crs = self.projection.create_crs()

    def _determine_map_limits(self, cdump, map_opt_passes):
        mb = mapbox.MapBox()

        for ipass in range(map_opt_passes):
            mb.allocate()

            # add release points
            for loc in cdump.release_locs:
                if util.is_valid_lonlat(loc):
                    mb.add(loc)

            # find trajectory hits
            mb.hit_count = 0
            for cg in cdump.conc_grids:
                for i in range(len(cg.longitudes)):
                    for j in range(len(cg.latitudes)):
                        if cg.conc[i, j] > 0:
                            mb.add((cg.longitudes[i], cg.latitudes[j]))

            if mb.hit_count == 0:
                raise Exception("no concentration data to plot")

            # first pass only refines grid for small plumes
            if ipass == 0 and map_opt_passes == 2:
                mb.determine_plume_extent()
                if mb.need_to_refine_grid():
                    mb.refine_grid()
                else:
                    break

        return mb

    def draw_concentration_plot(self, conc_grid, scaled_conc, contour_levels, contour_colors):
        axes = self.conc_axes

        # keep the plot size after zooming
        axes.set_aspect("equal", adjustable="datalim")

        # turn off ticks and tick labels
        axes.tick_params(left="off", labelleft="off",
                         right="off", labelright="off",
                         top="off", labeltop="off",
                         bottom="off", labelbottom="off")

        # y-label
        axes.set_ylabel(self.make_ylabel(self.cdump,
                                         self.settings.source_label))
       
        # set_yticks([]) is necessary to make the y-label visible.
        axes.set_yticks([])

        # set the data range
        axes.set_extent(self.projection.corners_lonlat, self.data_crs)

        # draw the background map
        for o in self.background_maps:
            if isinstance(o.map, geopandas.geoseries.GeoSeries):
                background_map = o.map.to_crs(self.crs.proj4_init)
            else:
                background_map = o.map.copy()
                background_map['geometry'] = background_map['geometry'].to_crs(self.crs.proj4_init)
            clr = self._fix_map_color(o.linecolor, self.settings.color)
            background_map.plot(ax=axes, linestyle=o.linestyle, linewidth=o.linewidth, color=o.linecolor)

        # draw optional concentric circles
        if self.settings.ring and self.settings.ring_number > 0:
            self._draw_concentric_circles(axes)

        # place station locations
        self._draw_stations_if_exists(axes, self.settings)

        logger.debug("contour levels %s", contour_levels)
        logger.debug("contour colors %s", contour_colors)

        logger.debug("Drawing contour")
        
        # draw a source marker
        if self.settings.label_source == 1:
            x = []; y = []
            for loc in conc_grid.parent.release_locs:
                if util.is_valid_lonlat(loc):
                    x.append(loc[0])
                    y.append(loc[1])
                    
            if len(x) > 0:
                axes.scatter(x, y,
                             s=self.settings.source_marker_size,
                             marker=self.settings.source_marker,
                             c=self.settings.source_marker_color, clip_on=True,
                             transform=self.data_crs)

        # draw filled contours
        axes.contourf(conc_grid.longitudes,
                      conc_grid.latitudes,
                      scaled_conc,
                      contour_levels,
                      colors=contour_colors,
                      extend="max",
                      transform=self.data_crs)
        
        if self.settings.noaa_logo:
            self._draw_noaa_logo(axes)

    def draw_contour_legends(self):
        self._turn_off_ticks(self.legends_axes)
#                         
#         alt_text_lines = self.labels.get("TXBOXL")
#         
#         maptext_fname = self.make_maptext_filename()
#         if os.path.exists(maptext_fname):
#             self._draw_maptext_if_exists(self.text_axes, maptext_fname)
#         elif (alt_text_lines is not None) and (len(alt_text_lines) > 0):
#             self._draw_alt_text_boxes(self.text_axes, alt_text_lines)
#         else:
#             top_spineQ = self.settings.vertical_coordinate != const.Vertical.NONE
#             self._turn_off_spines(self.text_axes, top=top_spineQ)

    def draw_bottom_text(self):
        self._turn_off_ticks(self.text_axes)
#                         
#         alt_text_lines = self.labels.get("TXBOXL")
#         
#         maptext_fname = self.make_maptext_filename()
#         if os.path.exists(maptext_fname):
#             self._draw_maptext_if_exists(self.text_axes, maptext_fname)
#         elif (alt_text_lines is not None) and (len(alt_text_lines) > 0):
#             self._draw_alt_text_boxes(self.text_axes, alt_text_lines)
#         else:
#             top_spineQ = self.settings.vertical_coordinate != const.Vertical.NONE
#             self._turn_off_spines(self.text_axes, top=top_spineQ)
     
    def draw(self, ev_handlers=None, *args, **kw):
        if self.settings.interactive_mode == False:
            plt.ioff()

        initial_time = None
        current_frame = 1
        
        clg = ContourLevelGeneratorFactory.create_instance(self.settings.contour_level_generator,
                                                           self.settings.contour_levels,
                                                           self.settings.user_color)
        ct = ColorTableFactory.create_instance(self.settings)
        cc = ContourColorFactory.create_instance(ct,
                                                 self.settings.KMAP,
                                                 self.settings.contour_level_generator,
                                                 self.settings.KHEMIN,
                                                 self.settings.IDYNC)
        vavg_calc = prop.VerticalAverageCalculator(self.cdump, self.level_selector)

        for t_index in self.time_selector:
            t_grids = prop.TimeIndexGridFilter(self.cdump.conc_grids,
                                               prop.TimeIndexSelector(t_index, t_index))
            
            if self.settings.KAVG == const.ConcentrationType.VERTICAL_AVERAGE:
                v_grids = prop.sum_over_pollutants_per_level(t_grids,
                                                             self.level_selector,
                                                             self.pollutant_selector)
                v_avg = vavg_calc.average(v_grids)
                grids = [v_avg]
            else:
                grids = prop.VerticalLevelGridFilter(t_grids, self.level_selector)

            # TODO: move?
            if self.settings.exposure_unit == const.ExposureUnit.EXPOSURE:
                g = grids[0]
                
                # air conc to exposure
                TFACT = self.settings.CONADJ * abs(g.get_duration_in_sec())
                if t_index == self.time_selector.first:
                    f = abs(g.get_duration_in_sec())
                    p.scale_exposure(self.settings.KAVG, f)
            else:
                # conc unit conversion factor
                TFACT = self.settings.CONADJ
            
            # save the initial time for internal summation
            if t_index == self.time_selector.first:
                initial_time = grids[0].starting_datetime
                
            for g in grids:
                self.layout(ev_handlers)
                
                # plot title
                self._turn_off_spines(self.conc_outer)
                self._turn_off_ticks(self.conc_outer)
                self.conc_outer.set_title(self.make_plot_title(g))
                
                contour_levels = clg.make_levels(self.data_properties.min_concs[-1],
                                                 self.data_properties.max_concs[-1],
                                                 self.settings.contour_level_count)
                
                # TODO: correction for mapping.
                xconc = numpy.copy(g.conc)
                xconc *= TFACT
                
                if self.smoothing_kernel is not None:
                    xconc = self.smoothing_kernel.smooth_with_max_preserved(xconc)
                
                self.draw_concentration_plot(g, xconc, contour_levels, cc.colors)
                self.draw_contour_legends()
                self.draw_bottom_text()
                
                if self.settings.interactive_mode:
                    plt.show(*args, **kw)
                else:
                    self.fig.canvas.draw()  # to get the plot spines right.
                    self.update_gridlines()
                    filename = self.make_plot_filename(self.settings, current_frame)
                    logger.info("Saving a plot to file %s", filename)
                    plt.savefig(filename, papertype="letter")
                
                #self.fig.clf()
                plt.close(self.fig)
                current_frame += 1
    

class LabelledContourLevel:
    
    def __init__(self, level=0.0, label="NONAME", r=1.0, g=1.0, b=1.0):
        self.level = level
        self.label = label
        self.r = r
        self.g = g
        self.b = b
    
    
class ContourLevelGeneratorFactory:
    
    @staticmethod
    def create_instance(generator, cntr_levels, user_colorQ):
        if generator == const.ContourLevelGenerator.EXPONENTIAL_DYNAMIC:
            return ExponentialDynamicLevelGenerator()
        elif generator == const.ContourLevelGenerator.EXPONENTIAL_FIXED:
            return ExponentialFixedLevelGenerator()
        elif generator == const.ContourLevelGenerator.LINEAR_DYNAMIC:
            return LinearDynamicLevelGenerator()
        elif generator == const.ContourLevelGenerator.LINEAR_FIXED:
            return LinearFixedLevelGenerator()
        elif generator == const.ContourLevelGenerator.USER_SPECIFIED:
            return UserSpecifiedLevelGenerator(cntr_levels)
        else:
            raise Exception("unknown method {0} for contour level generation".format(generator))


class AbstractContourLevelGenerator:
    
    def __init__(self):
        return


class ExponentialDynamicLevelGenerator(AbstractContourLevelGenerator):
    
    def __init__(self):
        AbstractContourLevelGenerator.__init__(self)
    
    @staticmethod
    def make_levels(cmin, cmax, max_levels):
        nexp = int(math.log10(cmax))
        if nexp < 0:
            nexp -= 1
        levels = numpy.empty(max_levels, dtype=float)
        levels[1] = math.pow(10.0, nexp)
        levels[0] = 10.0 * levels[1]
        for k in range(2, len(levels)):
            levels[k] = 0.1 * levels[k - 1] * 0.1
        return numpy.flip(levels)


class ExponentialFixedLevelGenerator(AbstractContourLevelGenerator):
    
    def __init__(self):
        AbstractContourLevelGenerator.__init__(self)

    @staticmethod
    def make_levels(cmin, cmax, max_levels):
        return ExponentialDynamicLevelGenerator.make_levels(cmin, cmax, max_levels)
        
        
class LinearDynamicLevelGenerator(AbstractContourLevelGenerator):
    
    def __init__(self):
        AbstractContourLevelGenerator.__init__(self)
        
    @staticmethod
    def make_levels(cmin, cmax, max_levels):
        nexp = util.nearest_int(math.log10(cmax * 0.25))
        if nexp < 0:
            nexp -= 1
        cint = math.pow(10.0, nexp)
        if cmax / cint > 6:
            cint *= 2.0
        levels = numpy.empty(max_levels, dtype=float)
        for k in range(len(levels)):
            levels[k] = cint * (k + 1)
        return levels


class LinearFixedLevelGenerator(AbstractContourLevelGenerator):
    
    def __init__(self):
        AbstractContourLevelGenerator.__init__(self)

    @staticmethod
    def make_levels(cmin, cmax, max_levels):
        return LinearDynamicLevelGenerator.make_levels(cmin, cmax, max_levels)
    
    
class UserSpecifiedLevelGenerator(AbstractContourLevelGenerator):
    
    def __init__(self, user_specified_levels):
        AbstractContourLevelGenerator.__init__(self)
        self.contour_levels = [o.level for o in user_specified_levels]
    
    def make_levels(self, cmin, cmax, max_levels):
        return self.contour_levels
    
    
class ColorTableFactory:
    
    COLOR_TABLE_FILE_NAMES = ["CLRTBL.CFG", "../graphics/CLRTBL.CFG"]

    @staticmethod
    def create_instance(settings):
        if settings.KMAP == const.ConcentrationMapType.THRESHOLD_LEVELS and settings.KHEMIN == 1:
            ct = DefaultChemicalThresholdColorTable()
        elif settings.user_color:
            ct = UserColorTable(settings.contour_levels)
        else:
            ct = DefaultColorTable()
            f = ColorTableFactory._get_color_table_filename()
            if f is not None:
                ct.get_reader().read(f)
                if settings.contour_level_generator == const.ContourLevelGenerator.EXPONENTIAL_DYNAMIC and settings.IDYNC != 0:
                    for k in range(5):
                        ct.set_rgb(k, (1.0, 1.0, 1.0))
        
        if settings.color == const.ConcentrationPlotColor.BLACK_AND_WHITE or settings.color == const.ConcentrationPlotColor.VAL_3:
            ct.change_to_grayscale()
        
        return ct
    
    @staticmethod
    def _get_color_table_filename():      
        for s in ColorTableFactory.COLOR_TABLE_FILE_NAMES:
            if os.path.exists(s):
                return s
            
        return None
    
    
class ColorTable:
    
    def __init__(self):
        self.__colors = None
        self.rgbs = []
        return
    
    def get_reader(self):
        return ColorTableReader(self)
    
    def set_rgb(self, k, rgb):
        self.rgbs[k] = rgb
    
    def change_to_grayscale(self):
        for k, rgb in enumerate(self.rgbs):
            l = self.get_luminance(rgb)
            self.rgbs[k] = (l, l, l)
            
    @staticmethod
    def get_luminance(rgb):
        r, g, b = rgb
        return 0.299*r + 0.587*b + 0.114*b
    
    @property
    def colors(self):
        if self.__colors is None:
            self.__colors = self.create_plot_colors(self.rgbs)
            
        return self.__colors
    
    @staticmethod
    def create_plot_colors(rgbs):
        return [util.make_color(o[0], o[1], o[2]) for o in rgbs]

        
class DefaultColorTable(ColorTable):
    
    def __init__(self):
        ColorTable.__init__(self)
        self.rgbs = [
            (1.0, 1.0, 1.0), (1.0, 1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0),
            (0.0, 1.0, 1.0), (1.0, 0.0, 0.0), (1.0, 0.6, 0.0), (1.0, 1.0, 0.0),
            (0.8, 1.0, 0.0), (0.0, 0.6, 0.0), (0.0, 1.0, 0.4), (0.0, 1.0, 1.0),
            (0.0, 0.4, 1.0), (0.2, 0.0, 1.0), (0.6, 0.0, 1.0), (0.8, 0.0, 1.0),
            (0.4, 0.0, 0.4), (0.6, 0.0, 0.4), (0.4, 0.0, 0.2), (0.2, 0.0, 0.2),
            (0.6, 0.0, 0.0), (1.0, 0.8, 1.0), (0.4, 0.4, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0)]


class DefaultChemicalThresholdColorTable(ColorTable):
    
    def __init__(self):
        ColorTable.__init__(self)
        self.rgbs = [
            (1.0, 1.0, 1.0), (0.8, 0.8, 0.8), (1.0, 1.0, 0.0), (1.0, 0.5, 0.0),
            (1.0, 0.0, 0.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0)]
        

class UserColorTable(ColorTable):
    
    def __init__(self, contour_levels):
        ColorTable.__init__(self)
        self.rgbs = [(o.r, o.g, o.b) for o in contour_levels]


class ColorTableReader(io.FormattedTextFileReader):
    
    def __init__(self, color_table):
        io.FormattedTextFileReader.__init__(self)
        self.color_table = color_table
        
    def read(self, filename):
        self.open(filename)
        
        # skip two header lines
        self.fetch_line()
        self.fetch_line()
        
        w = 1.0 / 255.0
        rgbs = []
        k = 0
        while self.has_next() and k < 32:
            v = self.parse_line("A15,I3,4X,I3,4X,I3")
            logger.debug("color [%s], r %d, g %d, b %d", v[0], v[1], v[2], v[3])
            rgbs.append((v[1]*w, v[2]*w, v[3]*w))
            k += 1
        
        self.color_table.rgbs = rgbs
        self.close()
        
        return self.color_table
    
    
class ContourColorFactory:
    
    @staticmethod
    def create_instance(color_table, *args):
        return ContourColor(color_table)
    

class ContourColor:
    
    def __init__(self, color_table):
        c = color_table.colors
        self.colors = [c[8], c[7], c[6], c[5]]