# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# clist.py
#
# Provides utilities for reading a cluster list file.
# ---------------------------------------------------------------------------

import logging

from hysplitplot import util


logger = logging.getLogger(__name__)


class ClusterList:

    def __init__(self, start_index):
        self.percent = dict()
        self.start_index = start_index  # 0 or 1
        self.total_traj = 0

    def get_label(self, k):
        if k in self.percent:
            return "{0} ({1}%)".format(k + self.start_index, self.percent[k])
        return ""

    def get_reader(self):
        return ClusterListReader(self)

    def clear(self):
        self.percent.clear()
        self.total_traj = 0


class ClusterListReader:

    def __init__(self, clist):
        self.clist = clist

    def read(self, filename):
        self.clist.clear()

        total_traj = 0
        holder = dict()

        with open(filename, "rt") as f:
            lines = f.read().splitlines()
            k = 0
            while k < len(lines):
                ln = lines[k]
                w = ln.split()
                logger.error("ln %s; w %s", ln, w)
                logger.debug("cluster list entry %s %s", w[0], w[1])
                c = int(w[0]) - self.clist.start_index
                n = int(w[1])
                holder[c] = n
                if c >= 0:
                    total_traj += n
                k += n

        self.clist.total_traj = total_traj
        logger.debug("total trajectory count %d", total_traj)

        for k, v in holder.items():
            self.clist.percent[k] = percent = \
                util.nearest_int((100.0*v) / total_traj)
            logger.debug("trajectory %d: percentage %d", k, percent)

        return self.clist
