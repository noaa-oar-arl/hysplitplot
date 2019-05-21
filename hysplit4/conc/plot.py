import logging
import sys
import geopandas
import matplotlib.gridspec
import matplotlib.pyplot as plt

from hysplit4 import cmdline, util, const, plotbase, mapbox, mapproj
from hysplit4.conc import model


logger = logging.getLogger(__name__)


class ConcentrationPlotSettings(plotbase.AbstractPlotSettings):
    
    def __init__(self):
        plotbase.AbstractPlotSettings.__init__(self)

        self.input_files = "cdump"
        self.output_postscript = "concplot.ps"
        
    def dump(self, stream):
        """Dumps the settings to an output stream.

        """
        stream.write("----- begin ConcentrationPlotSettings\n")
        for k, v in self.__dict__.items():
            stream.write("{0} = {1}\n".format(k, v))
        stream.write("----- end ConcentrationPlotSettings\n")

    def get_reader(self):
        return ConcentrationPlotSettingsReader(self)

    def process_command_line_arguments(self, args0):
        """Processes command-line arguments and updates settings.

        :param args0: arguments excluding the program name.
        """
        args = cmdline.CommandLineArguments(args0)
        
        # process options common to trajplot, concplot, etc.
        self._process_cmdline_args(args)
        

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
        s.ring = util.convert_integer_to_boolean(int(lines[14])) # 1 or 0
        s.map_center = int(lines[15]) # 1 or 0
        s.ring_number = int(lines[16])
        s.ring_distance = float(lines[17])
        # qpnt, l 19
        s.center_loc[1] = float(lines[19])
        s.center_loc[0] = float(lines[20])
        
        return s


class ConcentrationPlot(plotbase.AbstractPlot):

    def __init__(self):
        plotbase.AbstractPlot.__init__(self)
        self.settings = ConcentrationPlotSettings()
        self.data_list = None
    
    def update_gridlines(self):
        self._update_gridlines(self.conc_axes,
                               self.settings.map_color,
                               self.settings.lat_lon_label_interval_option,
                               self.settings.lat_lon_label_interval)
        return
    
    def get_gridline_spacing(self, corners_lonlat):
        if self.settings.lat_lon_label_interval_option == const.LatLonLabel.NONE:
            return 0.0
        elif self.settings.lat_lon_label_interval_option == const.LatLonLabel.SET:
            return self.settings.lat_lon_label_interval
        else:
            return self.calc_gridline_spacing(corners_lonlat)

    def merge_plot_settings(self, filename, args):
        if filename is not None:
            self.settings.get_reader().read(filename)
        self.settings.process_command_line_arguments(args)
    
    def read_data_files(self):
        input_files = util.make_file_list(self.settings.input_files)

        self.data_list = []
        for inp in input_files:
            c = model.ConcentrationDump()
            r = c.get_reader()
            r.read(inp)
            self.data_list.append(c)
            
    def read_background_map(self):
        self.background_maps = self.load_background_map(self.settings.map_background)

    def layout(self, ev_handlers=None):

        self._initialize_map_projection()

        fig = plt.figure(
            figsize=(8.5, 11.0),  # letter size
            clear=True,  # clear an existing figure
            constrained_layout=False
        )

        outer_grid = matplotlib.gridspec.GridSpec(3, 1,
                                                  wspace=0.0, hspace=0.0,  # no spaces between subplots
                                                  width_ratios=[1.0], height_ratios=[3.0, 1.0, 0.75])

        inner_grid = matplotlib.gridspec.GridSpecFromSubplotSpec(3, 3,
                                                                 wspace=0.0, hspace=0.0,
                                                                 width_ratios=[1, 8, 1], height_ratios=[1, 6, 3],
                                                                 subplot_spec=outer_grid[1, 0])

        self.fig = fig
        self.conc_axes = fig.add_subplot(outer_grid[0, 0], projection=self.crs)
        self.height_axes_outer = fig.add_subplot(outer_grid[1, 0])
        self.height_axes = fig.add_subplot(inner_grid[1, 1])
        self.text_axes = fig.add_subplot(outer_grid[2, 0])

        if ev_handlers is not None:
            self._connect_event_handlers(ev_handlers)

    def _initialize_map_projection(self):
        map_opt_passes = 1 if self.settings.ring_number == 0 else 2
        map_box = self._determine_map_limits(self.data_list[0], map_opt_passes)

#         # TODO: check if we are using pbot and ptop.
#         pbot, ptop = self._determine_vertical_limit(self.data_list[0], self.settings.vertical_coordinate)

        self.settings.center_loc = [-84, 40] # TODO
#         if self.settings.center_loc == [0.0, 0.0]:
#             self.settings.center_loc = self.data_list[0].trajectories[0].starting_loc

#         if self.settings.ring and self.settings.ring_number >= 0:
#             map_box.determine_plume_extent()
#             map_box.clear_hit_map()
#             map_box.set_ring_extent(self.settings)

        self.projection = mapproj.MapProjectionFactory.create_instance(self.settings.map_projection,
                                                                       self.settings.zoom_factor,
                                                                       self.settings.center_loc,
                                                                       1.3,
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
                if loc != (99.0, 99.0):     # TODO: need this? check with FORTRAN code
                    mb.add(loc)

            # find trajectory hits
            mb.hit_count = 0
            for cg in cdump.conc_grids:
                # TODO: check storage convention. to loop efficiently.
                for j in range(len(cg.latitudes)):
                    for i in range(len(cg.longitudes)):
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

    def draw_concentration_plot(self):
        axes = self.conc_axes

#         # plot title
#         axes.set_title(self.make_plot_title(self.data_list[0]))
#         
#         # reset line color and marker cycles to be in sync with the height profile plot
#         self.settings.color_cycle.reset()
#         self.settings.reset_marker_cycle()

        # keep the plot size after zooming
        axes.set_aspect("equal", adjustable="datalim")

        # turn off ticks and tick labels
        axes.tick_params(left="off", labelleft="off",
                         right="off", labelright="off",
                         top="off", labeltop="off",
                         bottom="off", labelbottom="off")

#         # y-label
#         axes.set_ylabel(self.make_ylabel(self.data_list[0],
#                                          self.settings.source_label,
#                                          self.settings.time_label_interval))
       
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

#         # draw optional concentric circles
#         if self.settings.ring and self.settings.ring_number > 0:
#             self._draw_concentric_circles(axes)

#         # place station locations
#         self._draw_stations_if_exists(axes, self.make_stationplot_filename())

        for plotData in self.data_list:
            for k, cg in enumerate(plotData.conc_grids):
                # TODO: check storage convention. to loop efficiently.
                for j in range(0, len(cg.latitudes), 5):
                    for i in range(0, len(cg.longitudes), 5):
                        if cg.conc[i, j] > 0:
                            axes.scatter(cg.longitudes[i], cg.latitudes[j],
                                         transform=self.data_crs)
#                 # draw a source marker
#                 if self.settings.label_source == 1:
#                     if util.is_valid_lonlat(t.starting_loc):
#                         axes.scatter(t.starting_loc[0], t.starting_loc[1],
#                                      s=self.settings.source_marker_size,
#                                      marker=self.settings.source_marker,
#                                      c=self.settings.source_marker_color, clip_on=True,
#                                      transform=self.data_crs)
#                 # gather data points
#                 lats = t.latitudes
#                 lons = t.longitudes
#                 if len(lats) == 0 or len(lons) == 0:
#                     continue
#                 # draw a trajectory
#                 clr = self.settings.color_cycle.next_color(t.starting_level_index, t.color)
#                 ms = self.settings.next_marker()
#                 axes.plot(lons, lats, clr, transform=self.data_crs)
#                 # draw interval markers
#                 interval_symbol_drawer.draw(t, lons, lats, c=clr, marker=ms, clip_on=True,
#                                             transform=self.data_crs)

        if self.settings.noaa_logo:
            self._draw_noaa_logo(axes)
    
    def draw(self, *args, **kw):
        if self.settings.interactive_mode == False:
            plt.ioff()
            
        self.draw_concentration_plot()
        #self.draw_bottom_plot()
        #self.draw_bottom_text()
        
        if self.settings.interactive_mode:
            plt.show(*args, **kw)
        else:
            self.fig.canvas.draw()  # to get the plot spines right.
            self.update_gridlines()
            plt.savefig(self.settings.output_postscript,
                        papertype="letter")
            
        plt.close(self.fig)
