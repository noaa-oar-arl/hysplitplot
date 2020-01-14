# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# helper.py
#
# Helper functions and classes for producing time-of-arrival plots.
# ---------------------------------------------------------------------------

from abc import ABC, abstractmethod
import copy
import datetime
import logging
import numpy

from hysplitplot.conc import helper


logger = logging.getLogger(__name__)


class TimeOfArrivalGenerator:

    def __init__(self, time_selector, conc_type):
        # Time-of-arrivals in hour at 6, 12, 18, ....
        self.hours = numpy.linspace(6, 72, num=12)
        # Bitmasks 1, 2, 4, ... for time-of-arrivals 6, 12, 18, ...,
        # respectively.
        self.bitmasks = [(1 << k) for k in range(len(self.hours))]
        self.grid = None
        self.above_ground_toa_bits = None
        self.deposition_toa_bits = None
        self.time_selector = time_selector
        self.conc_type = conc_type
        self.time_period_count = 0

    def _get_bitmasks(self, day):
        if day == TimeOfArrival.DAY_0:
            return [1, 2, 4, 8]
        elif day == TimeOfArrival.DAY_1:
            return [16, 32, 64, 128]
        else:
            return [256, 512, 1024, 2048]

    def _get_lumped_bitmasks_before(self, day):
        if day == TimeOfArrival.DAY_0:
            return None
        elif day == TimeOfArrival.DAY_1:
            return 0x0f
        else:
            return 0x0ff

    def _get_toa_hours_for(self, day):
        if day == TimeOfArrival.DAY_0:
            return self.hours[0:4]
        elif day == TimeOfArrival.DAY_1:
            return self.hours[4:8]
        else:
            return self.hours[8:]

    def _check_cdump_consistency(self, cdump):
        if cdump.grids is None or len(cdump.grids) < 1:
            logger.error("No concentration grid is available "
                         "to check sampling interval")
            return False

        for g in cdump.grids:
            dt = g.ending_datetime - g.starting_datetime
            ts = dt.total_seconds()

            if ts <= 0:
                logger.error("Time-of-arrival analysis is not supported "
                             "for a backward run")
                return False
            elif ts > 6*3600:
                logger.error("Sampling interval (%f hrs) exceeds "
                             "6 hours", ts/3600.0)
                return False

            if ((6*3600) % ts) != 0:
                logger.error("Sampling interval (%f min) does not add "
                             "up to 6 hours", ts/60.0)
                return False

        return True

    def process_conc_data(self, cdump):
        if not self._check_cdump_consistency(cdump):
            raise Exception("The concentration dump file is not suitable "
                            "for time-of-arrival analysis: see the error "
                            "message above")

        self.above_ground_toa_bits = numpy.zeros(
            cdump.grids[0].conc.shape, dtype=int)
        self.deposition_toa_bits = numpy.zeros(
            cdump.grids[0].conc.shape, dtype=int)

        conc_sum = numpy.zeros(cdump.grids[0].conc.shape, dtype=float)

        hour_index = 0
        release_date_time = cdump.release_datetimes[0]
        dt_range_lower = release_date_time
        dt_range_upper = release_date_time \
            + datetime.timedelta(hours=self.hours[hour_index])

        for t_index in self.time_selector:
            t_grids = helper.TimeIndexGridFilter(
                cdump.grids, helper.TimeIndexSelector(t_index, t_index))

            if t_grids[0].ending_datetime > dt_range_upper:
                if hour_index + 1 < len(self.hours):
                    hour_index += 1
                    dt_range_lower = dt_range_upper
                    dt_range_upper = release_date_time \
                        + datetime.timedelta(hours=self.hours[hour_index])
                else:
                    logger.debug("passed 72-hours: skip processing "
                                 "the remaining grids.")
                    break

            grids_above_ground, grids_on_ground = \
                self.conc_type.prepare_grids_for_plotting(t_grids)
            logger.debug("grid counts: above the ground %d, on the ground %d",
                         len(grids_above_ground), len(grids_on_ground))

            if t_grids[0].starting_datetime >= dt_range_lower \
                    and t_grids[0].ending_datetime <= dt_range_upper:
                logger.debug("time-of-arrival: start time {}, "
                             "hour {}".format(t_grids[0].starting_datetime,
                                              self.hours[hour_index]))
                if self.grid is None:
                    self.grid = t_grids[0].clone_except_conc()
                    self.grid.nonzero_conc_count = 0

                for g in grids_above_ground:
                    loc = numpy.where(g.conc > 0)
                    self.above_ground_toa_bits[loc] |= \
                        self.bitmasks[hour_index]
                    self.grid.nonzero_conc_count += len(loc[0])

                for g in grids_on_ground:
                    loc = numpy.where(g.conc > 0)
                    self.deposition_toa_bits[loc] |= self.bitmasks[hour_index]
                    self.grid.nonzero_conc_count += len(loc[0])

            self.time_period_count += 1

    def make_deposition_data(self, day, fill_colors):
        toa = DepositionTimeOfArrival(self.grid)
        toa.create_contour(self.deposition_toa_bits,
                           self._get_bitmasks(day),
                           self._get_toa_hours_for(day),
                           self._get_lumped_bitmasks_before(day),
                           fill_colors)
        return toa

    def make_plume_data(self, day, fill_colors):
        toa = PlumeTimeOfArrival(self.grid)
        toa.create_contour(self.above_ground_toa_bits,
                           self._get_bitmasks(day),
                           self._get_toa_hours_for(day),
                           self._get_lumped_bitmasks_before(day),
                           fill_colors)
        return toa


class TimeOfArrival(ABC):

    DAY_0 = 0
    DAY_1 = 1
    DAY_2 = 2

    def __init__(self, parent):
        self.grid = parent
        self.contour_levels = None
        self.display_levels = None
        self.fill_colors = None
        self.data_count = 0

    def has_data(self):
        return self.data_count > 0

    @property
    def longitudes(self):
        return self.grid.longitudes

    @property
    def latitudes(self):
        return self.grid.latitudes

    @property
    def data(self):
        return self.grid.conc

    @abstractmethod
    def get_map_id_line(self, lower_vert_level, upper_vert_level,
                        starting_dt, ending_dt):
        pass

    def create_contour(self, toa_bits, toa_bitmasks, toa_hours, prev_bitmask,
                       fill_colors):
        self.grid.conc = numpy.zeros(toa_bits.shape, dtype=int)

        # Assume toa_bitmasks has ascending order.
        toa_bitmasks = copy.copy(toa_bitmasks)
        toa_bitmasks.reverse()

        # For contouring, the highest bit is assigned the lowest contour value.
        contour_values = [1, 2, 3, 4]

        self.data_count = 0
        for k, mask in enumerate(toa_bitmasks):
            c = numpy.copy(toa_bits)
            c &= mask
            loc = numpy.where(c > 0)
            self.grid.conc[loc] = contour_values[k]
            self.data_count += len(loc[0])
            logger.debug("Time-of-arrival: bitmask {}, value {}, "
                         "count {}".format(mask, contour_values[k],
                                           len(loc[0])))

        if prev_bitmask is not None:
            c = numpy.copy(toa_bits)
            c &= prev_bitmask
            loc = numpy.where(c > 0)
            self.grid.conc[loc] = 5
            self.data_count += len(loc[0])
            contour_values.append(5)

        # self.save_data("toa_data.txt")

        n = len(contour_values) - len(fill_colors)
        if n <= 0:
            self.fill_colors = fill_colors[0:len(contour_values)]
        else:
            self.fill_colors = copy.copy(list(fill_colors))
            for k in range(n):
                self.fill_colors.append("#808080")  # add gray

        self.contour_levels = contour_values

        self.time_intervals = []
        self.display_levels = []
        hours = numpy.flip(toa_hours)
        for hr in hours:
            hr = int(hr)
            self.display_levels.append("{}-{} hours".format(hr - 6, hr))
            self.time_intervals.append((hr - 6, hr))

        if prev_bitmask is not None:
            hr = int(hours[-1]) - 6
            self.display_levels.append("{}-{} hours".format(0, hr))
            self.time_intervals.append((0, hr))

        self.grid.starting_datetime = self.grid.parent.release_datetimes[0]
        self.grid.ending_datetime = self.grid.starting_datetime \
            + datetime.timedelta(hours=hours[0])

    def save_data(self, filename):
        g = self.grid.conc
        with open(filename, "wt") as f:
            h, w = g.shape
            for j in range(h):
                for i in range(w):
                    f.write("{} {} {}\n".format(i, j, g[j, i]))
                f.write("\n")


class DepositionTimeOfArrival(TimeOfArrival):

    def __init__(self, parent):
        super(DepositionTimeOfArrival, self).__init__(parent)

    def get_map_id_line(self, lower_vert_level, upper_vert_level,
                        starting_dt, ending_dt):
        str = "Time of arrival (h) at ground-level"
        str += starting_dt.strftime("\nIntegrated from %H%M %d %b to")
        str += ending_dt.strftime(" %H%M %d %b %Y (%Z)")
        return str


class PlumeTimeOfArrival(TimeOfArrival):

    def __init__(self, parent):
        super(PlumeTimeOfArrival, self).__init__(parent)

    def get_map_id_line(self, lower_vert_level, upper_vert_level,
                        starting_dt, ending_dt):
        str = "Time of arrival (h) averaged " \
              "between {} and {}".format(lower_vert_level, upper_vert_level)
        str += starting_dt.strftime("\nIntegrated from %H%M %d %b to")
        str += ending_dt.strftime(" %H%M %d %b %Y (%Z)")
        return str
