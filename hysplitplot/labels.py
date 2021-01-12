# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# labels.py
#
# For reading a LABELS.CFG file.
# ---------------------------------------------------------------------------

import logging

from hysplitdata.const import HeightUnit
from hysplitplot import const


logger = logging.getLogger(__name__)


class LabelsConfig():

    def __init__(self):
        self.cfg = dict()
        self.cfg["TITLE"] = "NOAA HYSPLIT MODEL"
        return

    def has(self, name):
        return name in self.cfg

    def get(self, name, default_value=""):
        return self.cfg[name] if name in self.cfg else default_value

    def get_reader(self):
        return LabelsConfigReader(self)

    def after_reading_file(self, settings):
        if self.get("VUNIT") == "FEET":
            settings.height_unit = HeightUnit.FEET


class LabelsConfigReader():

    def __init__(self, cfg):
        self.obj = cfg

    def read(self, filename):
        if not self.check_consistency(filename):
            raise Exception("Consistency check failed. Please fix "
                            "{0}".format(filename))

        with open(filename, "rt") as f:
            for ln in f:
                k, v = self.parse_line(ln.rstrip("\n"))
                v = self.escape(v)
                if k == "TXBOXL":
                    if k in self.obj.cfg:
                        self.obj.cfg[k].append(v)
                    else:
                        self.obj.cfg[k] = [v]
                else:
                    self.obj.cfg[k] = v

        return self.obj

    def escape(self, v):
        # replace % with \% for matplotlib.
        return v.replace('%', '\%')

    def check_consistency(self, filename):
        with open(filename, "rt") as f:
            expected_count = tbox_count = 0
            state = 0
            for ln in f:
                k, v = self.parse_line(ln.rstrip("\n"))
                if state == 0:
                    # looking for the NTXBOXL line
                    if k == "NTXBOXL":
                        expected_count = int(v)
                        tbox_count = 0
                        state = 1
                    elif k == "TXBOXL":
                        logger.error("NTXBOXL line must proceed TXBOXL "
                                     "line(s)")
                        return False
                elif state == 1:
                    # already found the NTXBOXL line
                    if k == "TXBOXL":
                        tbox_count += 1
                    elif k == "NTXBOXL":
                        if tbox_count != expected_count:
                            logger.error("%d text box lines must follow "
                                         "NTXBOXL in %s", expected_count,
                                         filename)
                            return False
                        expected_count = int(v)
                        tbox_count = 0
            if expected_count > 0 and tbox_count != expected_count:
                logger.error("%d text box lines must follow NTXBOXL in %s",
                             expected_count, filename)
                return False

        return True

    def parse_line(self, ln):
        list = []
        state = 0
        start = 0
        field = ""
        for k, c in enumerate(ln):
            if state == 0:  # looking for opening quote
                if c == "'":
                    state = 1
            elif state == 1:
                if c == "'":
                    state = 2
                else:
                    field += c
            elif state == 2:
                if c == "'":  # escaped single quote
                    field += c
                    state = 1
                elif c == ",":
                    list.append(field)
                    field = ""
                    state = 0
        if state != 0:
            list.append(field)

        return list[0].rstrip("&"), list[1].rstrip("&")
