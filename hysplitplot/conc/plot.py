import copy
import datetime
import geopandas
import logging
import math
import matplotlib.gridspec
import matplotlib.pyplot as plt
import numpy
import os
import pytz
import sys

from hysplitdata import io
from hysplitdata.conc import model
from hysplitdata.const import HeightUnit
from hysplitplot import cmdline, util, const, datem, plotbase, mapbox, mapproj, smooth, multipage
from hysplitplot.conc import helper, gisout, cntr


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
        self.QFILE = None
        self.source_label = "\u2606"    # open star
        self.this_is_test = 0
        self.LEVEL1 = 0     # bottom display level defaults to deposition surface
        self.LEVEL2 = 99999 # top level defaults to whole model atmosphere
        self.exposure_unit = const.ExposureUnit.CONCENTRATION # KEXP; -e
        self.KMAP = const.ConcentrationMapType.CONCENTRATION
        self.KAVG = const.ConcentrationType.EACH_LEVEL
        self.NDEP = const.DepositionType.TIME
        self.show_max_conc = 1
        self.mass_unit = "mass"
        self.mass_unit_by_user = False
        self.smoothing_distance = 0
        self.CONADJ = 1.0   # conc unit conversion multiplication factor
        self.DEPADJ = 1.0   # deposition unit conversion multiplication factor
        self.UCMIN = 0.0    # min conc value
        self.UDMIN = 0.0    # min deposition value
        self.IDYNC = 0      # allow colors to change for dyn contours?
        self.KHEMIN = 0     # plot below threshold contour for chemical output
        self.IZRO = 0       # create map(s) even if all values are zero
        self.NSSLBL = 0     # force sample start time label to start of release
        self.color = const.ConcentrationPlotColor.COLOR # KOLOR
        self.gis_alt_mode = const.GISOutputAltitude.CLAMPED_TO_GROUND
        self.KMLOUT = 0
        
        # internally defined
        self.label_source = True
        self.source_label_color= "k"        # black
        self.source_label_font_size = 12    # font size
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
        
        if len(args.unprocessed_args) > 0:
            self.input_file = args.unprocessed_args[-1]
            
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
        
        if args.has_arg(["-u", "-U"]):
            self.mass_unit = args.get_value(["-u", "-U"])
            self.mass_unit_by_user = True
        
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
            
        self.gis_alt_mode = args.get_integer_value(["+a", "+A"], self.gis_alt_mode)
        self.KMLOUT = args.get_integer_value(["-5"], self.KMLOUT)
  
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
            self.contour_levels, self.user_color = self.parse_labeled_contour_levels(str)
            self.user_label = True
        else:
            l = self.parse_simple_contour_levels(str)
            self.contour_levels = [LabelledContourLevel(v) for v in l]
      
        self.contour_level_count = len(self.contour_levels)
        
        # sort by contour level
        self.contour_levels = sorted(self.contour_levels, key=lambda o: o.level)
        logger.debug("sorted contour levels: %s", self.contour_levels)
                
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
        color_set = True
        
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
            else:
                color_set = False
            
            list.append(o)    
            k += 1
            
        return list, color_set

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
        self.time_selector = None
        self.level_selector = None
        self.pollutant_selector = None
        self.smoothing_kernel = None
        self.conc_type = None
        self.conc_map = None
        self.depo_map = None
        self.prev_forecast_time = None
        self.length_factory = None
        
        self.fig = None
        self.conc_outer = None
        self.conc_axes = None
        self.legends_axes = None
        self.text_axes = None
        self.plot_saver = None
        
        self.TFACT = 1.0
        self.initial_time = None
        self.contour_labels = None
        self.current_frame = 1
        self.time_period_count = 0
        self.datem = None
        
  
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
        self.cdump = cdump = model.ConcentrationDump().get_reader().read(self.settings.input_file)
       
        # create selectors               
        self.time_selector = helper.TimeIndexSelector(self.settings.first_time_index,
                                                      self.settings.last_time_index,
                                                      self.settings.time_index_step)
        self.pollutant_selector = helper.PollutantSelector(self.settings.pollutant_index)
        self.level_selector = helper.VerticalLevelSelector(self.settings.LEVEL1, self.settings.LEVEL2)

        # limit time indices. assume that the last concentration grid has the largest time index.
        self.time_selector.normalize(cdump.grids[-1].time_index)
        logger.debug("time iteration is limited to index range [%d, %d]",
                     self.time_selector.first, self.time_selector.last)

        logger.debug("level iteration is limited to height range [%.1f, %.1f] in meters",
                     self.level_selector.min,
                     self.level_selector.max)
                
        # normalize pollutant index and name
        self.pollutant_selector.normalize(len(cdump.pollutants) - 1)
        self.settings.pollutant_index = self.pollutant_selector.index
        self.settings.pollutant = cdump.get_pollutant(self.settings.pollutant_index)

        if len(cdump.pollutants) > 1:
            logger.info("Multiple pollutant species in file")
            for k, name in enumerate(cdump.pollutants):
                if k == self.settings.pollutant_index:
                    logger.info("%d - %s <--- selected", k+1, name)
                else:
                    logger.info("%d - %s", k+1, name)
        
        # if only one non-depositing level, change -d2 to -d1.
        if self.settings.KAVG == const.ConcentrationType.VERTICAL_AVERAGE:
            if len(cdump.release_heights) == 1 or (len(cdump.release_heights) == 2 and cdump.release_heights[0] == 0):
                logger.warning("Changing -d2 to -d1 since single layer")
                self.settings.KAVG = const.ConcentrationType.EACH_LEVEL
        
        self.conc_type = helper.ConcentrationTypeFactory.create_instance(self.settings.KAVG)
        if self.settings.KAVG == 1:
            self.conc_type.set_alt_KAVG(3)  # for the above-ground concentration plots
        if self.labels.has("LAYER"):
            self.conc_type.set_custom_layer_str( self.labels.get("LAYER") )
        
        self.plot_saver = multipage.PlotFileWriterFactory.create_instance(self.settings.frames_per_file,
                                                                          self.settings.output_basename,
                                                                          self.settings.output_suffix)

        self._post_file_processing(self.cdump)
                
        self.conc_map = helper.ConcentrationMapFactory.create_instance(self.settings.KMAP, self.settings.KHEMIN)
        self.depo_map = helper.DepositionMapFactory.create_instance(self.settings.KMAP, self.settings.KHEMIN)
        if self.labels.has("MAPID"):
            self.conc_map.map_id = self.labels.get("MAPID")
            self.depo_map.map_id = self.labels.get("MAPID")
        
        self.depo_sum = helper.DepositSumFactory.create_instance(self.settings.NDEP, self.cdump.has_ground_level_grid())
                
        if self.settings.smoothing_distance > 0:
            self.smoothing_kernel = smooth.SmoothingKernelFactory.create_instance(const.SmoothingKernel.SIMPLE,
                                                                                  self.settings.smoothing_distance)
        
        if self.labels.has("TZONE"):
            self.time_zone = pytz.timezone( self.labels.get("TZONE") )
        if self.settings.use_source_time_zone:
            self.time_zone = self.get_time_zone_at(self.cdump.release_locs[0])
        
        if self.settings.QFILE is not None:
            if os.path.exists(self.settings.QFILE):
                self.datem = datem.Datem().get_reader().read(self.settings.QFILE) 
            
    def _post_file_processing(self, cdump):
        
        self.conc_type.initialize(cdump,
                                  self.level_selector,
                                  self.pollutant_selector)
            
        # find min and max values by examining all grids of interest
        for t_index in self.time_selector:
            t_grids = helper.TimeIndexGridFilter(cdump.grids,
                                                 helper.TimeIndexSelector(t_index, t_index))
            self.conc_type.update_min_max(t_grids)

        self.conc_type.normalize_min_max()
        
        self.conc_type.scale_conc(self.settings.CONADJ,
                                  self.settings.DEPADJ)
        
        self._normalize_settings(cdump)
           
        self.length_factory = util.AbstractLengthFactory.create_factory(self.settings.height_unit)

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
        
        if s.exposure_unit == const.ExposureUnit.CHEMICAL_THRESHOLDS:
            s.KMAP = const.ConcentrationMapType.THRESHOLD_LEVELS
        elif s.exposure_unit == const.ExposureUnit.VOLCANIC_ASH:
            s.KMAP = const.ConcentrationMapType.VOLCANIC_ERUPTION
        elif s.exposure_unit == const.ExposureUnit.MASS_LOADING:
            s.KMAP = const.ConcentrationMapType.MASS_LOADING
        else:
            s.KMAP = s.exposure_unit + 1

        self.update_height_unit(self.labels)
        
        if self.contour_labels is None:
            if self.settings.contour_levels is not None:
                self.contour_labels = [c.label for c in self.settings.contour_levels]
            else:
                self.contour_labels = [""] * self.settings.contour_level_count
                
    def update_height_unit(self, labels):
        # default values from labels.cfg  
        if labels.has("ALTTD"):
            alttd = labels.get("ALTTD")
            if alttd == "feet":
                self.settings.height_unit = HeightUnit.FEET
            elif alttd == "meters":
                self.settings.height_unit = HeightUnit.METERS
            else:
                raise Exception("ALTTD units must be meters or feet in labels.cfg or its equivalent file: {0}".format(alttd))

    @staticmethod
    def _fix_map_color(color, color_mode):
        return color if color_mode != const.ConcentrationPlotColor.BLACK_AND_WHITE else 'k'

    def read_background_map(self):
        self.background_maps = self.load_background_map(self.settings.map_background)

    def layout(self, grid, event_handlers=None):

        fig = plt.figure(
            figsize=(8.5, 11.0),  # letter size
            clear=True,  # clear an existing figure
            constrained_layout=False
        )

        outer_grid = matplotlib.gridspec.GridSpec(2, 1,
                                                  wspace=0.0, hspace=0.075,
                                                  width_ratios=[1.0], height_ratios=[3.25, 1.50])

        inner_grid = matplotlib.gridspec.GridSpecFromSubplotSpec(1, 2,
                                                                 wspace=0.02, hspace=0.0,
                                                                 width_ratios=[2, 1], height_ratios=[1],
                                                                 subplot_spec=outer_grid[0, 0])

        self.fig = fig
        self.conc_outer = fig.add_subplot(outer_grid[0, 0])
        self.conc_axes = fig.add_subplot(inner_grid[0, 0], projection=self.crs)
        self.legends_axes = fig.add_subplot(inner_grid[0, 1])
        self.text_axes = fig.add_subplot(outer_grid[1, 0])

        if event_handlers is not None:
            self._connect_event_handlers(event_handlers)
    
    def make_plot_title(self, conc_grid, conc_map, lower_vert_level, upper_vert_level):
        s = self.settings
        
        fig_title = self.labels.get("TITLE")
        
        conc_unit = self.get_conc_unit(conc_map, s)
        fig_title += "\n"
        fig_title += conc_map.get_map_id_line(self.conc_type, conc_unit, lower_vert_level, upper_vert_level)
        
        dt = self.adjust_for_time_zone(conc_grid.starting_datetime)
        fig_title += dt.strftime("\nIntegrated from %H%M %d %b to")
        
        dt = self.adjust_for_time_zone(conc_grid.ending_datetime)
        fig_title += dt.strftime(" %H%M %d %b %Y (%Z)")
        
        if not conc_grid.is_forward_calculation():
            fig_title += " [backward]"           
        
        pollutant = self.settings.pollutant if self.settings.pollutant_index == -1 else conc_grid.pollutant
        
        if not conc_grid.is_forward_calculation():
            fig_title += "\n{0} Calculation started at".format(pollutant)
        else:
            fig_title += "\n{0} Release started at".format(pollutant)
            
        dt = self.adjust_for_time_zone(conc_grid.parent.release_datetimes[0])
        fig_title += dt.strftime(" %H%M %d %b %Y (%Z)")
        
        return fig_title
    
    def make_ylabel(self, cdump, marker):
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
            height_min = self.length_factory.create_instance(release_heights[0])
            y_label += "      from {0}".format(height_min)
        else:
            height_min = self.length_factory.create_instance(min(release_heights))
            height_max = self.length_factory.create_instance(max(release_heights))
            y_label += "      from {0} to {1}".format(height_min, height_max)
        
        logger.debug("using ylabel %s", y_label)
        return y_label
       
    def make_xlabel(self, g):
        curr_forecast_time = g.ending_datetime - datetime.timedelta(hours=g.ending_forecast_hr)
        
        if g.ending_forecast_hr > 12 and (self.prev_forecast_time is None or self.prev_forecast_time == curr_forecast_time):
            ts = self.adjust_for_time_zone(curr_forecast_time).strftime("%H%M %d %b %Y")
            x_label = "{0} {1} FORECAST INITIALIZATION".format(ts, self.cdump.meteo_model)
        else:
            x_label = "{0} METEOROLOGICAL DATA".format(self.cdump.meteo_model)
            
        self.prev_forecast_time = curr_forecast_time
        
        logger.debug("using xlabel %s", x_label)
        return x_label
    
    def _initialize_map_projection(self, cdump):
        map_opt_passes = 1 if self.settings.ring_number == 0 else 2
        map_box = self._determine_map_limits(cdump, map_opt_passes)

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
                                                                       self.cdump.grid_deltas,
                                                                       map_box)
        self.projection.refine_corners(self.settings.center_loc)

        # copy the map projection because it might have been changed.
        self.settings.map_projection = self.projection.proj_type

        self.crs = self.projection.create_crs()

    def _create_map_box_instance(self, cdump):
        lat_span = cdump.grid_sz[1] * cdump.grid_deltas[1]
        lon_span = cdump.grid_sz[0] * cdump.grid_deltas[0]
        
        # use finer grids for small maps
        if lat_span < 2.0 and lon_span < 2.0:
            mbox = mapbox.MapBox(grid_corner=cdump.grid_loc, grid_size=(lon_span, lat_span), grid_delta=0.10)
        elif lat_span < 5.0 and lon_span < 5.0:
            mbox = mapbox.MapBox(grid_corner=cdump.grid_loc, grid_size=(lon_span, lat_span), grid_delta=0.20)
        else:
            mbox = mapbox.MapBox()
        
        return mbox
    
    def _determine_map_limits(self, cdump, map_opt_passes):
        mbox = self._create_map_box_instance(cdump)

        # summation of all concentration grids of interest
        conc = helper.sum_conc_grids_of_interest(cdump.grids,
                                                 self.level_selector,
                                                 self.pollutant_selector,
                                                 self.time_selector)
        
        for ipass in range(map_opt_passes):
            mbox.allocate()

            # add release points
            for loc in cdump.release_locs:
                if util.is_valid_lonlat(loc):
                    mbox.add(loc)

            # find trajectory hits
            mbox.hit_count = 0
            for j in range(len(cdump.latitudes)):
                for i in range(len(cdump.longitudes)):
                    if conc[j, i] > 0:
                        mbox.add((cdump.longitudes[i], cdump.latitudes[j]))

            if mbox.hit_count == 0:
                if self.settings.IZRO == 0:
                    raise Exception("ALL concentrations are ZERO - no maps")
                else:
                    logger.info("ALL concentrations are ZERO")

            # first pass only refines grid for small plumes
            if ipass == 0 and map_opt_passes == 2:
                mbox.determine_plume_extent()
                if mbox.need_to_refine_grid():
                    mbox.refine_grid()
                else:
                    break

        return mbox

    def draw_concentration_plot(self, conc_grid, scaled_conc, conc_map, contour_levels, fill_colors):
        """
        Draws a concentration contour plot and returns the contour data points.
        """
        contour_set = None
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
            self._draw_concentric_circles(axes,
                                          self.cdump.release_locs[0],
                                          self.settings.ring_number,
                                          self.settings.ring_distance)
          
        logger.debug("Drawing contour at levels %s using colors %s", contour_levels, fill_colors)
        
        # draw a source marker
        if self.settings.label_source:
            x = []; y = []
            for loc in conc_grid.parent.release_locs:
                if util.is_valid_lonlat(loc):
                    x.append(loc[0])
                    y.append(loc[1])
            
            for k in range(len(x)):
                axes.text(x[k], y[k], self.settings.source_label,
                          color=self.settings.source_label_color,
                          fontsize=self.settings.source_label_font_size,
                          horizontalalignment="center", verticalalignment="center", clip_on=True,
                          transform=self.data_crs)

        if conc_grid.nonzero_conc_count > 0:
            # draw filled contours
            contour_set = axes.contourf(conc_grid.longitudes, conc_grid.latitudes, scaled_conc,
                                        contour_levels,
                                        colors=fill_colors, extend="max",
                                        transform=self.data_crs)
            # draw contour lines
            line_colors = ["k"] * len(fill_colors)
            axes.contour(conc_grid.longitudes, conc_grid.latitudes, scaled_conc,
                         contour_levels,
                         colors=line_colors, linewidths=0.25,
                         transform=self.data_crs)

        if self.settings.show_max_conc == 1 or self.settings.show_max_conc == 3:
            if self.settings.color == const.ConcentrationPlotColor.BLACK_AND_WHITE \
              or self.settings.color == const.ConcentrationPlotColor.VAL_3:
                clr = "k"   # blank
            else:
                clr = conc_map.get_color_at_max()
            
            conc_grid.extension.max_locs = helper.find_max_locs(conc_grid)
            dx = conc_grid.parent.grid_deltas[0]
            dy = conc_grid.parent.grid_deltas[1]
            hx = 0.5 * dx
            hy = 0.5 * dy
            for loc in conc_grid.extension.max_locs:
                x, y = loc
                r = matplotlib.patches.Rectangle((x-hx, y-hy), dx, dy,
                                                 color=clr,
                                                 transform=self.data_crs)
                axes.add_patch(r)
        
        # place station locations
        self._draw_stations_if_exists(axes, self.settings)
         
        # draw DATEM data
        if self.datem is not None:
            self._draw_datem(axes,
                             self.settings,
                             self.datem,
                             conc_grid.starting_datetime,
                             conc_grid.ending_datetime)

        if self.settings.noaa_logo:
            self._draw_noaa_logo(axes)

        return contour_set
    
    def get_conc_unit(self, conc_map, settings):
        # default values from labels.cfg  
        mass_unit = self.labels.get("UNITS")
        volume_unit = self.labels.get("VOLUM")
                                      
        if settings.mass_unit_by_user:
            mass_unit = settings.mass_unit
        elif not self.labels.has("UNITS"):
            mass_unit = conc_map.guess_mass_unit(settings.mass_unit)
            
        if not self.labels.has("VOLUM"):
            volume_unit = conc_map.guess_volume_unit(settings.mass_unit)
            
        return "{0}{1}".format(mass_unit, volume_unit)
        
    def draw_contour_legends(self, grid, conc_map, contour_labels, contour_levels, fill_colors):
        axes = self.legends_axes
        s = self.settings
        
        min_conc, max_conc = self.conc_type.get_plot_conc_range(grid)
        logger.debug("concentration plot min %g, max %g", min_conc, max_conc)
                
        self._turn_off_ticks(axes)
        
        font_sz = 9.0 # TODO: to be computed
        small_font_sz = 0.8 * font_sz
        
        line_skip = 1 / 20.0
        small_line_skip = 0.8 * line_skip
        
        x = 0.05
        y = 1.0 - small_line_skip * 0.5;
                
        conc_unit = self.get_conc_unit(conc_map, s)
        
        if conc_map.has_banner():
            str = conc_map.get_banner()
            axes.text(0.5, y, str, color="r", fontsize=small_font_sz,
                      horizontalalignment="center", verticalalignment="top", clip_on=True,
                      transform=axes.transAxes)
            y -= small_line_skip
    
        if grid.nonzero_conc_count == 0:
            return
        
        dy = line_skip if s.contour_level_count <= 16 else line_skip * 0.65
        dx = 0.25
        
        logger.debug("contour_level_count %d", s.contour_level_count)
        logger.debug("contour levels %s", contour_levels)
        logger.debug("contour colors %s", fill_colors)
        logger.debug("contour labels %s", contour_labels)

        labels = copy.deepcopy(contour_labels)
        labels.reverse()
        
        colors = copy.deepcopy(fill_colors)
        colors.reverse()
        
        for k, level in enumerate(reversed(contour_levels)):
            clr = colors[k]
                        
            box = matplotlib.patches.Rectangle((x, y-dy), dx, dy, color=clr,
                                               transform=axes.transAxes)
            axes.add_patch(box)
            
            label = labels[k] if k < len(labels) else ""
            axes.text(x+0.5*dx, y-0.5*dy, label, color="k", fontsize=font_sz,
                      horizontalalignment="center", verticalalignment="center", clip_on=True,
                      transform=axes.transAxes)
            
            v = conc_map.format_conc(level)
            str = ">{0} ${1}$".format(v, conc_unit)
            axes.text(x + dx + x, y-0.5*dy, str, color="k", fontsize=font_sz,
                      horizontalalignment="left", verticalalignment="center", clip_on=True,
                      transform=axes.transAxes)
            
            y -= dy
            
        if max_conc > 0 and (s.show_max_conc ==1 or s.show_max_conc == 2):
            y -= line_skip * 0.5
            
            str = "Maximum: {0:.1e} ${1}$".format(max_conc, conc_unit)
            axes.text(x, y, str, color="k", fontsize=font_sz,
                      horizontalalignment="left", verticalalignment="top", clip_on=True,
                      transform=axes.transAxes)
            y -= line_skip
            
            str = "Minimum: {0:.1e} ${1}$".format(min_conc, conc_unit)
            axes.text(x, y, str, color="k", fontsize=font_sz,
                      horizontalalignment="left", verticalalignment="top", clip_on=True,
                      transform=axes.transAxes)
            y -= line_skip
     
        y = conc_map.draw_explanation_text(axes, x, y, small_font_sz, small_line_skip, labels)
        
        if self.settings.this_is_test:
            y -= small_line_skip * 1.5
            axes.hlines(y-small_line_skip * 0.5, 0.05, 0.95,
                    color="k",
                    linewidth=0.125, 
                    transform=axes.transAxes)
            
            y -= small_line_skip
            axes.text(0.5, y, "THIS IS A TEST", color="r", fontsize=small_font_sz,
                      horizontalalignment="center", verticalalignment="top", clip_on=True,
                      transform=axes.transAxes)
            
            axes.hlines(y-small_line_skip, 0.05, 0.95,
                    color="k",
                    linewidth=0.125, 
                    transform=axes.transAxes)
        
    def draw_bottom_text(self):
        self._turn_off_ticks(self.text_axes)
                         
        alt_text_lines = self.labels.get("TXBOXL")
         
        map_text_filename = self._make_maptext_filename(self.settings.output_suffix)
        if os.path.exists(map_text_filename):
            self._draw_maptext_if_exists(self.text_axes, map_text_filename)
        elif (alt_text_lines is not None) and (len(alt_text_lines) > 0):
            self._draw_alt_text_boxes(self.text_axes, alt_text_lines)
        else:
            self._turn_off_spines(self.text_axes)
    
    def _write_gisout(self, gis_writer, g, lower_vert_level, upper_vert_level, quad_contour_set, contour_levels, color_table):
        if g.extension.max_locs is None:
                g.extension.max_locs = helper.find_max_locs(g)
                
        min_conc, max_conc = self.conc_type.get_plot_conc_range(g)
        
        contour_set = cntr.convert_matplotlib_quadcontourset(quad_contour_set)
        contour_set.raw_colors = color_table.raw_colors
        contour_set.colors = color_table.colors
        contour_set.levels = contour_levels
        contour_set.levels_str = [self.conc_map.format_conc(level) for level in contour_levels]
        contour_set.labels = self.contour_labels
        contour_set.concentration_unit = self.get_conc_unit(self.conc_map, self.settings)
        contour_set.min_concentration = min_conc
        contour_set.max_concentration = max_conc
        contour_set.min_concentration_str = self.conc_map.format_conc(min_conc)
        contour_set.max_concentration_str = self.conc_map.format_conc(max_conc)

        basename = gis_writer.make_output_basename(g,
                                                   self.conc_type,
                                                   self.depo_sum,
                                                   self.settings.output_basename,
                                                   self.settings.output_suffix,
                                                   self.settings.KMLOUT,
                                                   upper_vert_level)

        gis_writer.write(basename, g, contour_set, lower_vert_level, upper_vert_level)
   
    def draw_conc_above_ground(self, g, event_handlers, level_generator, color_table, gis_writer=None, *args, **kwargs):
        
        self.layout(g, event_handlers)
        
        self._turn_off_spines(self.conc_outer)
        self._turn_off_ticks(self.conc_outer)
        
        min_conc, max_conc = self.conc_type.get_plot_conc_range(g)
        level_generator.set_global_min_max(self.conc_type.contour_min_conc, self.conc_type.contour_max_conc)
        contour_levels = level_generator.make_levels(min_conc, max_conc, self.settings.contour_level_count)
        
        LEVEL0 = self.conc_type.get_lower_level(g.vert_level, self.cdump.vert_levels)
        LEVEL2 = self.conc_type.get_upper_level(g.vert_level, self.settings.LEVEL2)
        
        level1 = self.length_factory.create_instance(LEVEL0)
        level2 = self.length_factory.create_instance(LEVEL2)
        
        f = float(g.vert_level - LEVEL0)
        conc_scaling_factor = self.conc_map.scale_exposure(self.TFACT, self.conc_type, f)
        
        scaled_conc = numpy.copy(g.conc)
        if conc_scaling_factor != 1.0:
            scaled_conc *= conc_scaling_factor
        
        if self.smoothing_kernel is not None:
            scaled_conc = self.smoothing_kernel.smooth_with_max_preserved(scaled_conc)
        
        # plot title
        self.conc_outer.set_title(self.make_plot_title(g, self.conc_map, level1, level2))
        self.conc_outer.set_xlabel(self.make_xlabel(g))
        
        quad_contour_set = self.draw_concentration_plot(g, scaled_conc, self.conc_map, contour_levels, color_table.colors)
        self.draw_contour_legends(g, self.conc_map, self.contour_labels, contour_levels, color_table.colors)
        self.draw_bottom_text()
        
        if gis_writer is not None:
            self._write_gisout(gis_writer, g, LEVEL0, LEVEL2, quad_contour_set, contour_levels, color_table)
            
        self.conc_map.undo_scale_exposure(self.conc_type)
        
        if self.settings.interactive_mode:
            plt.show(*args, **kwargs)
        else:
            self.fig.canvas.draw()  # to get the plot spines right.
            self.update_gridlines()
            self.plot_saver.save(self.fig, self.current_frame)
        
        plt.close(self.fig)
        self.current_frame += 1

    def draw_conc_on_ground(self, g, event_handlers, level_generator, color_table, gis_writer=None, *args, **kwargs):
        
        self.layout(g, event_handlers)
        
        self._turn_off_spines(self.conc_outer)
        self._turn_off_ticks(self.conc_outer)

        min_conc, max_conc = self.conc_type.get_plot_conc_range(g)
        level_generator.set_global_min_max(self.conc_type.ground_min_conc, self.conc_type.ground_max_conc)     
        contour_levels = level_generator.make_levels(min_conc, max_conc, self.settings.contour_level_count)
        
        level1 = self.length_factory.create_instance(0)
        level2 = self.length_factory.create_instance(0)
        
        scaled_conc = numpy.copy(g.conc)
        if self.settings.DEPADJ != 1.0:
            scaled_conc *= self.settings.DEPADJ
        
        if self.smoothing_kernel is not None:
            scaled_conc = self.smoothing_kernel.smooth_with_max_preserved(scaled_conc)
        
        # plot title
        self.conc_outer.set_title(self.make_plot_title(g, self.depo_map, level1, level2))
        self.conc_outer.set_xlabel(self.make_xlabel(g))
        
        contour_set = self.draw_concentration_plot(g, scaled_conc, self.depo_map, contour_levels, color_table.colors)
        self.draw_contour_legends(g, self.depo_map, self.contour_labels, contour_levels, color_table.colors)
        self.draw_bottom_text()
         
        if gis_writer is not None:
            self._write_gisout(gis_writer, g, 0, 0, contour_set, contour_levels, color_table)
       
        if self.settings.interactive_mode:
            plt.show(*args, **kwargs)
        else:
            self.fig.canvas.draw()  # to get the plot spines right.
            self.update_gridlines()
            self.plot_saver.save(self.fig, self.current_frame)
            
        plt.close(self.fig)
        self.current_frame += 1       
        
    def draw(self, ev_handlers=None, *args, **kwargs):
        if self.settings.interactive_mode == False:
            plt.ioff()

        level_generator = ContourLevelGeneratorFactory.create_instance(self.settings.contour_level_generator,
                                                                       self.settings.contour_levels,
                                                                       self.settings.UCMIN,
                                                                       self.settings.user_color)
        color_table = ColorTableFactory.create_instance(self.settings)
        
        gis_writer = gisout.GISFileWriterFactory.create_instance(self.settings.gis_output,
                                                                 self.settings.kml_option)
                                                                 
        gis_writer.initialize(self.settings.gis_alt_mode,
                              self.settings.KMLOUT,
                              self.settings.output_suffix,
                              self.settings.KMAP,
                              self.settings.NSSLBL,
                              self.settings.show_max_conc)
        
        self._initialize_map_projection(self.cdump)

        self.depo_sum.initialize(self.cdump.grids, self.time_selector, self.pollutant_selector)
        
        for t_index in self.time_selector:
            t_grids = helper.TimeIndexGridFilter(self.cdump.grids,
                                                 helper.TimeIndexSelector(t_index, t_index))
            
            grids_above_ground, grids_on_ground = self.conc_type.prepare_grids_for_plotting(t_grids)
            logger.debug("grid counts: above the ground %d, on the ground %d",
                         len(grids_above_ground), len(grids_on_ground))

            self.depo_sum.add(grids_on_ground, t_index == self.time_selector.first)
                    
            # concentration unit conversion factor
            self.TFACT = self.settings.CONADJ

            if self.conc_map.need_time_scaling():
                f = abs(grids_above_ground[0].get_duration_in_sec())
                self.TFACT = self.conc_map.scale_time(self.TFACT, self.conc_type, f, initial_timeQ)
            logger.debug("CONADJ %g, TFACT %g", self.settings.CONADJ, self.TFACT)
            
            for g in grids_above_ground:
                self.draw_conc_above_ground(g, ev_handlers, level_generator, color_table, gis_writer, *args, **kwargs)
            
            grids = self.depo_sum.get_grids_to_plot(grids_on_ground, t_index == self.time_selector.last)
            for g in grids:
                self.draw_conc_on_ground(g, ev_handlers, level_generator, color_table, gis_writer, *args, **kwargs)
        
            self.time_period_count += 1
            
        gis_writer.finalize()
        self.plot_saver.close()

    def get_plot_count_str(self):
        if self.plot_saver.file_count > 1:
            return "{} output files".format(self.plot_saver.file_count)
        
        s = "{} time period".format(self.time_period_count)
        if self.time_period_count > 1:
            s += "s"

        return s


class LabelledContourLevel:
    
    def __init__(self, level=0.0, label="NONAME", r=1.0, g=1.0, b=1.0):
        self.level = level
        self.label = label
        self.r = r
        self.g = g
        self.b = b
        
    def __repr__(self):
        return "LabelledContourLevel({0}, {1}, r{2}, g{3}, b{4})".format(self.label, self.level, self.r, self.g, self.b)

    
class ContourLevelGeneratorFactory:
    
    @staticmethod
    def create_instance(generator, cntr_levels, UCMIN, user_colorQ):
        if generator == const.ContourLevelGenerator.EXPONENTIAL_DYNAMIC:
            return ExponentialDynamicLevelGenerator(UCMIN)
        elif generator == const.ContourLevelGenerator.CLG_50:
            return ExponentialDynamicLevelGenerator(UCMIN, force_base_ten=True)
        elif generator == const.ContourLevelGenerator.CLG_51:
            return ExponentialDynamicLevelGenerator(UCMIN, force_base_ten=True)
        elif generator == const.ContourLevelGenerator.EXPONENTIAL_FIXED:
            return ExponentialFixedLevelGenerator(UCMIN)
        elif generator == const.ContourLevelGenerator.LINEAR_DYNAMIC:
            return LinearDynamicLevelGenerator()
        elif generator == const.ContourLevelGenerator.LINEAR_FIXED:
            return LinearFixedLevelGenerator()
        elif generator == const.ContourLevelGenerator.USER_SPECIFIED:
            return UserSpecifiedLevelGenerator(cntr_levels)
        else:
            raise Exception("unknown method {0} for contour level generation".format(generator))


class AbstractContourLevelGenerator:
    
    def __init__(self, **kwargs):
        self.global_min = None
        self.global_max = None
        return

    def set_global_min_max(self, cmin, cmax):
        self.global_min = cmin
        self.global_max = cmax
        

class ExponentialDynamicLevelGenerator(AbstractContourLevelGenerator):
    
    def __init__(self, UCMIN, **kwargs):
        AbstractContourLevelGenerator.__init__(self, **kwargs)
        self.UCMIN = UCMIN
        self.force_base_10 = kwargs.get("force_base_10", False)

    def make_levels(self, min_conc, max_conc, max_levels):
        logger.debug("making %d levels using min_conc %g, max_conc %g", max_levels, min_conc, max_conc)
        
        cint = 10.0; cint_inverse = 0.1
        if (not self.force_base_10) and max_conc > 1.0e+8 * min_conc:
            cint = 100.0; cint_inverse = 0.01

        nexp = int(math.log10(max_conc)) if max_conc > 0 else 0
        if nexp < 0:
            nexp -= 1
        
        levels = numpy.empty(max_levels, dtype=float)
        a = math.pow(10.0, nexp)
        if a < self.UCMIN:
            levels[0] = self.UCMIN
            levels[1:] = 0.0
        else:
            levels[0] = a
            for k in range(1, max_levels):
                a = levels[k - 1] * cint_inverse
                levels[k] = 0.0 if a < self.UCMIN else a
        
        logger.debug("contour levels: %s", levels)
        return numpy.flip(levels)


class ExponentialFixedLevelGenerator(ExponentialDynamicLevelGenerator):
    
    def __init__(self, UCMIN, **kwargs):
        ExponentialDynamicLevelGenerator.__init__(self, UCMIN, **kwargs)
        
    def make_levels(self, min_conc, max_conc, max_levels):
        return ExponentialDynamicLevelGenerator.make_levels(self,
                                                            self.global_min,
                                                            self.global_max,
                                                            max_levels)
    
    
class LinearDynamicLevelGenerator(AbstractContourLevelGenerator):
    
    def __init__(self):
        AbstractContourLevelGenerator.__init__(self)
        
    def make_levels(self, min_conc, max_conc, max_levels):
        nexp = util.nearest_int(math.log10(max_conc * 0.25)) if max_conc > 0 else 0
        if nexp < 0:
            nexp -= 1
        cint = math.pow(10.0, nexp)
        if max_conc > 6 * cint:
            cint *= 2.0
            
        levels = numpy.empty(max_levels, dtype=float)
        for k in range(len(levels)):
            levels[k] = cint * (k + 1)
            
        logger.debug("contour levels: %s using max %g, levels %d", levels, max_conc, max_levels)
        return levels


class LinearFixedLevelGenerator(LinearDynamicLevelGenerator):
    
    def __init__(self):
        LinearDynamicLevelGenerator.__init__(self)
    
    def make_levels(self, min_conc, max_conc, max_levels):
        return LinearDynamicLevelGenerator.make_levels(self,
                                                       self.global_min,
                                                       self.global_max,
                                                       max_levels)


class UserSpecifiedLevelGenerator(AbstractContourLevelGenerator):
    
    def __init__(self, user_specified_levels):
        AbstractContourLevelGenerator.__init__(self)
        self.contour_levels = [o.level for o in user_specified_levels]
    
    def make_levels(self, min_conc, max_conc, max_levels):
        return self.contour_levels
    
    
class ColorTableFactory:
    
    COLOR_TABLE_FILE_NAMES = ["CLRTBL.CFG", "../graphics/CLRTBL.CFG"]

    @staticmethod
    def create_instance(settings):
        ncolors = settings.contour_level_count
        logger.debug("ColorTableFactory::create_instance: color count %d", ncolors)
        
        skip_std_colors = False
        if settings.contour_level_generator == const.ContourLevelGenerator.USER_SPECIFIED:
            skip_std_colors = True
        elif settings.contour_level_generator == const.ContourLevelGenerator.EXPONENTIAL_DYNAMIC and settings.IDYNC != 0:
            skip_std_colors = True
        
        if settings.KMAP == const.ConcentrationMapType.THRESHOLD_LEVELS and settings.KHEMIN == 1:
            ct = DefaultChemicalThresholdColorTable(ncolors, skip_std_colors)
        elif settings.user_color:
            ct = UserColorTable(settings.contour_levels)
        else:
            ct = DefaultColorTable(ncolors, skip_std_colors)
            f = ColorTableFactory._get_color_table_filename()
            if f is not None:
                ct.get_reader().read(f)
                if settings.contour_level_generator == const.ContourLevelGenerator.EXPONENTIAL_DYNAMIC and settings.IDYNC != 0:
                    for k in range(5):
                        ct.set_rgb(k, (1.0, 1.0, 1.0))
        
        if settings.color == const.ConcentrationPlotColor.BLACK_AND_WHITE or settings.color == const.ConcentrationPlotColor.VAL_3:
            ct.change_to_grayscale()
        
        logger.debug("using color table: %s", ct)
        return ct
    
    @staticmethod
    def _get_color_table_filename():      
        for s in ColorTableFactory.COLOR_TABLE_FILE_NAMES:
            if os.path.exists(s):
                return s
            
        return None
    
    
class ColorTable:
    
    def __init__(self, ncolors):
        self.rgbs = []
        self.ncolors = ncolors
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
       
    @staticmethod
    def create_plot_colors(rgbs):
        return [util.make_color(o[0], o[1], o[2]) for o in rgbs]

        
class DefaultColorTable(ColorTable):
    
    def __init__(self, ncolors, skip_std_colors):
        ColorTable.__init__(self, ncolors)
        self.skip_std_colors = skip_std_colors
        self.rgbs = [
            (1.0, 1.0, 1.0), (1.0, 1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0),
            (0.0, 1.0, 1.0), (1.0, 0.0, 0.0), (1.0, 0.6, 0.0), (1.0, 1.0, 0.0),
            (0.8, 1.0, 0.0), (0.0, 0.6, 0.0), (0.0, 1.0, 0.4), (0.0, 1.0, 1.0),
            (0.0, 0.4, 1.0), (0.2, 0.0, 1.0), (0.6, 0.0, 1.0), (0.8, 0.0, 1.0),
            (0.4, 0.0, 0.4), (0.6, 0.0, 0.4), (0.4, 0.0, 0.2), (0.2, 0.0, 0.2),
            (0.6, 0.0, 0.0), (1.0, 0.8, 1.0), (0.4, 0.4, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0)]
        self.__colors = None
        self.__raw_colors = None
    
    @property
    def raw_colors(self):
        if self.__raw_colors is None:
            if self.skip_std_colors:
                self.__raw_colors = self.rgbs[5 + self.ncolors - 1:4:-1]
            else:
                self.__raw_colors = self.rgbs[1 + self.ncolors - 1:0:-1]

        return self.__raw_colors
    
    @property
    def colors(self):
        if self.__colors is None:
            self.__colors = self.create_plot_colors(self.raw_colors)
        
        return self.__colors


class DefaultChemicalThresholdColorTable(ColorTable):
    
    def __init__(self, ncolors, skip_std_colors):
        ColorTable.__init__(self, ncolors)
        self.skip_std_colors = skip_std_colors
        self.__colors = None
        self.__raw_colors = None
        self.rgbs = [
            (1.0, 1.0, 1.0), (0.8, 0.8, 0.8), (1.0, 1.0, 0.0), (1.0, 0.5, 0.0),
            (1.0, 0.0, 0.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0)]
    
    @property
    def raw_colors(self):
        if self.__raw_colors is None:
            if self.skip_std_colors:
                self.__raw_colors = self.rgbs[5 + self.ncolors - 1:4:-1]
            else:
                self.__raw_colors = self.rgbs[1 + self.ncolors - 1:0:-1]

        return self.__raw_colors
    
    @property
    def colors(self):
        if self.__colors is None:
            self.__colors = self.create_plot_colors(self.raw_colors)
        
        return self.__colors


class UserColorTable(ColorTable):
    
    def __init__(self, contour_levels):
        ColorTable.__init__(self, len(contour_levels))
        self.rgbs = [(o.r, o.g, o.b) for o in contour_levels]
        self.__colors = None
    
    @property
    def raw_colors(self):
        return self.rgbs
    
    @property
    def colors(self):
        if self.__colors is None:
            self.__colors = self.create_plot_colors(self.raw_colors)
            
        return self.__colors


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
 
 
 