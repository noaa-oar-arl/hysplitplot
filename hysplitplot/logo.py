# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# logo.py
#
# Draws the NOAA logo to a plot.
# ---------------------------------------------------------------------------

import logging
import math
import matplotlib.patches
import numpy

from hysplitplot import util


logger = logging.getLogger(__name__)


class NOAALogoDrawer:

    # NOAA logo is a 400x400 bit circle sitting in a box
    # of dimensions 480x480 with the center at (240, 240)

    _bot = [
      49., 300.6491,  54., 297.4863,  59., 294.2104,  63., 291.2323,
      66., 288.8176,  70., 285.3888,  74., 281.7560,  80., 276.0039,
      86., 269.9912,  95., 260.7160, 103., 252.4435, 109., 246.3477,
      115., 240.4270, 121., 234.7451, 129., 227.6344, 135., 222.7078,
      144., 216.0513, 153., 210.3397, 162., 205.6037, 169., 202.5871,
      178., 199.5206, 188., 197.0726, 198., 195.4423, 206., 194.5501,
      215., 193.7590, 224., 192.9194, 232., 191.8681, 238., 191.2200,
      235., 189.4353, 231., 186.8327, 224., 183.1644, 216., 179.6956,
      207., 176.0158, 200., 173.0948, 193., 170.1800, 184., 166.8959,
      180., 165.8443, 174., 164.9000, 178., 162.2996, 183., 159.9238,
      188., 158.2339, 193., 157.1687, 198., 156.6691, 203., 156.6779,
      210., 157.4400, 216., 158.6911, 224., 161.0617, 230., 163.2609,
      239., 167.0543, 247., 170.7538, 255., 174.6005, 263., 178.4537,
      270., 181.7301, 279., 185.6835, 285., 188.0916, 291., 190.2733,
      301., 193.3184, 307., 194.7459, 315., 196.1369, 325., 196.9983,
      332., 197.6300, 331., 199.6559, 328., 202.9838, 326., 204.5860,
      323., 206.2241, 319., 207.2845, 315., 207.4395, 307., 206.3916,
      299., 205.1746, 295., 204.8848, 290., 204.9325, 287., 205.1631,
      285., 205.3811, 283., 206.2000, 286., 207.6836, 292., 209.6952,
      297., 211.6371, 303., 214.2869, 309., 217.2861, 317., 221.8297,
      326., 227.6852, 331., 231.2783, 337., 235.9097, 344., 241.7523,
      351., 248.0657, 357., 253.8493, 364., 261.0279, 369., 266.4372,
      375., 273.2354, 382., 281.5857, 387., 287.8231, 393., 295.6044,
      398., 302.3326, 404., 310.6948, 410., 319.3665, 414., 325.3168,
      417., 329.8671, 419., 332.9419]

    _top = [
      83., 352.0953,  88., 351.0599,  91., 349.9423,  98., 346.0323,
      103., 342.2440, 109., 336.7567, 116., 329.2594, 123., 320.8134,
      130., 311.6486, 136., 303.3857, 143., 293.4512, 150., 283.3823,
      156., 274.7810, 163., 264.9279, 170., 255.4173, 177., 246.3907,
      184., 237.9764, 191., 230.2898, 198., 223.4326, 207., 215.9767,
      212., 212.5492, 219., 208.6612, 227., 205.5741, 233., 204.2389,
      239., 203.7600, 246., 204.2919, 252., 205.6819, 257., 207.4925,
      262., 209.8871, 266., 212.2152, 271., 215.6279, 277., 220.4356,
      282., 225.0099, 289., 232.2284, 294., 237.9256, 299., 244.0355,
      304., 250.5203, 308., 255.9509, 313., 263.0053, 317., 268.8324,
      322., 276.3036, 328., 285.4730, 332., 291.6639, 336., 297.8813,
      340., 304.0928, 344., 310.2645, 349., 317.8697, 354., 325.2859,
      361., 335.2072, 366., 341.8563, 372., 349.2221, 378., 355.7763,
      384., 361.3609, 390., 365.8111, 394., 368.0629]
    _DEG2RAD = math.pi / 180.0

    def __init__(self):
        # logo size and center position
        self.logo_width = 480.0
        self.logo_height = 480.0
        self.cx = 240.0
        self.cy = 240.0
        self.R = 200.0
        self.base_font_sz = 12.0   # to be computed
        self.font_sz1 = 2.5*12.0   # to be computed
        self.font_sz2 = 1.1*12.0   # to be computed
        self.plot_objs = []

    def clear(self):
        for t in self.plot_objs:
            t.remove()
        self.plot_objs.clear()

    def draw(self, axes, bbox):
        # bbox in the axes coordinates
        (x0, y0), (x1, y1) = bbox
        w_axes = abs(x1 - x0)
        h_axes = abs(y1 - y0)
        tr = matplotlib.transforms.Affine2D() \
            .scale(w_axes/self.logo_width, h_axes/self.logo_height) \
            .translate(x0, y0) + axes.transAxes

        # 10% of the radius is the font size
        pts_dis = tr.transform(((0, 0), (0, 0.10*self.R)))
        pts_fig = axes.figure.transFigure.inverted().transform(pts_dis)
        self.base_font_sz = 72.0 * axes.figure.get_figheight() \
            * (pts_fig[1, 1] - pts_fig[0, 1])  # inch to pt
        self.font_sz1 = 2.75 * self.base_font_sz
        self.font_sz2 = 0.8 * self.base_font_sz
        logger.debug("base font size %f pt", self.base_font_sz)

        # above the seagull
        clr = util.make_color(0.0, 0.0, 0.7)
        pts = numpy.zeros((107+55, 2))
        for k in range(40, 147):
            pts[k - 40, 0] = self.R*math.cos(k*self._DEG2RAD) + self.cx
            pts[k - 40, 1] = self.R*math.sin(k*self._DEG2RAD) + self.cy
        for k in range(55):
            pts[107 + k, 0] = self._top[k*2]
            pts[107 + k, 1] = self._top[k*2 + 1]
        sg1 = matplotlib.patches.Polygon(pts, color=clr, fill=True,
                                         zorder=3, transform=tr)
        axes.add_patch(sg1)
        self.plot_objs.append(sg1)

        # below the seagull
        clr = util.make_color(0.0, 0.6, 1.0)
        pts = numpy.zeros((215+98, 2))
        for k in range(18, -198, -1):
            pts[18 - k, 0] = self.R*math.cos(k*self._DEG2RAD) + self.cx
            pts[18 - k, 1] = self.R*math.sin(k*self._DEG2RAD) + self.cy
        for k in range(98):
            pts[215 + k, 0] = self._bot[k*2]
            pts[215 + k, 1] = self._bot[k*2 + 1]
        sg2 = matplotlib.patches.Polygon(pts, color=clr, fill=True,
                                         zorder=3, transform=tr)
        axes.add_patch(sg2)
        self.plot_objs.append(sg2)

        # NOAA label above the seagull
        t = axes.text(235.0, 330.0, "noaa", fontsize=self.font_sz1,
                      fontweight="bold", horizontalalignment="center",
                      verticalalignment="center", clip_on=True, color="w",
                      zorder=4, transform=tr)
        self.plot_objs.append(t)

        # self._draw_top_label(axes, tr)
        # self._draw_bottom_label(axes, tr)

        # self._draw_ref_circ(axes, tr)

    def _draw_top_label(self, axes, tr):
        # top label angular range 190 degrees
        noaa1 = "NATIONAL OCEANIC AND ATMOSPHERIC ADMINISTRATION"
        noaa1_len = len(noaa1)
        delta_ang = 190.0 / noaa1_len
        ang = 90.0 + ((noaa1_len - 1) / 2) * delta_ang
        for c in noaa1:
            xp = (self.R + 15.0) * math.cos(ang * self._DEG2RAD) + self.cx
            yp = (self.R + 15.0) * math.sin(ang * self._DEG2RAD) + self.cy
            axes.text(xp, yp, c, fontsize=self.font_sz2, rotation=(ang-90.0),
                      horizontalalignment="center",
                      verticalalignment="center", clip_on=True, color="k",
                      transform=tr)
            ang -= delta_ang

    def _draw_bottom_label(self, axes, tr):
        # bottom label angular range 130 degrees
        noaa2 = "U.S. DEPARTMENT OF COMMERCE"
        noaa2_len = len(noaa2)
        delta_ang = 130.0 / noaa2_len
        ang = 270.0 - ((noaa2_len - 1) / 2) * delta_ang
        for c in noaa2:
            xp = (self.R + 15.0) * math.cos(ang * self._DEG2RAD) + self.cx
            yp = (self.R + 15.0) * math.sin(ang * self._DEG2RAD) + self.cy
            axes.text(xp, yp, c, fontsize=self.font_sz2, rotation=(ang+90.0),
                      horizontalalignment="center",
                      verticalalignment="center", clip_on=True, color="k",
                      transform=tr)
            ang += delta_ang

    def _draw_ref_circ(self, axes, tr):
        # reference circle for debugging
        circ = matplotlib.patches.Circle((self.cx, self.cy),
                                         radius=(self.R+15), color="r",
                                         fill=False, transform=tr)
        axes.add_patch(circ)
