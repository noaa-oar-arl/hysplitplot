# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# debug.py
#
# For debugging.
# ---------------------------------------------------------------------------

import cartopy.crs
import logging


logger = logging.getLogger(__name__)


def debug_axes(axes):
    """
    Print properties of a plot, or Axes in PyPlot term.
    """
    logger.debug("******************** BEGIN AXES PROPERTIES "
                 "********************")
    logger.debug("axes.get_extent (deg) %s",
                 axes.get_extent(cartopy.crs.PlateCarree()))
    # logger.debug("axes.get_extent %s", axes.get_extent())
    logger.debug("axes.get_xlim %s", axes.get_xlim())
    logger.debug("axes.get_ylim %s", axes.get_ylim())
    logger.debug("axes.viewLim %s", axes.viewLim)
    logger.debug("axes.transLimits %s", axes.transLimits)
    # logger.debug("axes.transProjection %s", axes.transProjection)
    # logger.debug("axes.transAffine %s", axes.transAffine)
    logger.debug("axes.transData %s", axes.transData)
    logger.debug("axes.transAxes %s", axes.transAxes)
    logger.debug("axes.projection %s", axes.projection)

    fig = axes.get_figure()
    logger.debug("figure %s, dpi %f", fig, fig.dpi)

    # x1, x2, y1, y2 = axes.get_extent()
    # poly = matplotlib.patches.Circle((x1, y1), radius=25000, color="g", clip_on=False)
    # axes.add_patch(poly)
    # poly = matplotlib.patches.Circle((x2, y2), radius=25000, color="g", clip_on=False)
    # axes.add_patch(poly)

    logger.debug("axes.get_xgridlines() %s", axes.get_xgridlines())
    logger.debug("axes.get_ygridlines() %s", axes.get_ygridlines())

    debug_axis(axes.xaxis)
    debug_axis(axes.yaxis)

    logger.debug("******************** END AXES PROPERTIES "
                 "********************")


def debug_axis(axis):
    """
    Print properties of x- or y-axis.
    """
    major_loc = axis.get_major_locator()
    logger.debug("******************** BEGIN AXIS PROPERTIES "
                 "********************")
    logger.debug("axis.label %s", axis.label)
    logger.debug("axis.majorTicks %s", axis.majorTicks)
    logger.debug("axis.majorTicks %s", [axis.major.formatter(val, k)
                                        for k, val in enumerate(axis.majorTicks)])
    logger.debug("axis.minorTicks %s", axis.minorTicks)
    logger.debug("axis.minorTicks %s", [axis.minor.formatter(val, k)
                                        for k, val in enumerate(axis.minorTicks)])
    logger.debug("axis.get_major_locator() %s", axis.get_major_locator())
    logger.debug("axis.get_minor_locator() %s", axis.get_minor_locator())
    logger.debug("axis.get_major_ticks() %s", axis.get_major_ticks(10))
    logger.debug("******************** END AXIS PROPERTIES "
                 "********************")
