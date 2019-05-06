# Adapted from https://nbviewer.jupyter.org/gist/ajdawson/dd536f786741e987ae4e
# TODO: copyright notice for the original author??
import logging
import shapely
import cartopy
import numpy


logger = logging.getLogger(__name__)


def projection_xticks(ax, ticks):
    """
    Determine tick labels and positions on the top x-axis for a map projection
    """
    x1, x2, _, y2 = ax.get_extent()
    axis_line = [(x1, y2), (x2, y2)]
    te = lambda xy: xy[0]
    lc = lambda t, n, b: numpy.vstack((numpy.zeros(n) + t, numpy.linspace(b[2], b[3], n))).T
    xticks, xticklabels = _projection_ticks(ax, ticks, axis_line, lc, te)
    ax.set_xticks(xticks)
    ax.set_xticklabels(xticklabels)

def projection_yticks(ax, ticks):
    """
    Determine tick labels and positions on the right y-axis for a map projection
    """
    _, x2, y1, y2 = ax.get_extent()
    axis_line = [(x2, y1), (x2, y2)]
    te = lambda xy: xy[1]
    lc = lambda t, n, b: numpy.vstack((numpy.linspace(b[0], b[1], n), numpy.zeros(n) + t)).T
    yticks, yticklabels = _projection_ticks(ax, ticks, axis_line, lc, te)
    ax.set_yticks(yticks)
    ax.set_yticklabels(yticklabels)

def _add_margin(extent, frac):
    """
    Increase the spatial extent in the WGS84 CRS by a small amount
    """
    x1, x2, y1, y2 = extent
    if x1 > x2:
        x1, x2 = x2, x1
    if y1 > y2:
        y1, y2 = y2, y1
    dx = (x2-x1) * frac
    dy = (y2-y1) * frac
    x1 = max(x1 - dx, -180.0)
    y1 = max(y1 - dy,  -90.0)
    x2 = min(x2 + dx,  180.0)
    y2 = min(y2 + dy,   90.0)
    ex2 = (x1, x2, y1, y2)
    logger.debug("addMargin: %s -> %s", extent, ex2)
    return ex2

def _projection_ticks(ax, ticks, axis_line, line_constructor, coord_picker):
    """
    Determine the tick locations and labels for an axis
    """
    axis = shapely.geometry.LineString(axis_line)

    # extend the bounding box by a small percentage to ensure intersection
    extent = _add_margin(ax.get_extent(cartopy.crs.PlateCarree()), 0.025)

    n_steps = 30
    _ticks = []; ticklabels = []
    for t in ticks:
        xy = line_constructor(t, n_steps, extent)
        proj_xyz = ax.projection.transform_points(cartopy.crs.Geodetic(), xy[:, 0], xy[:, 1])
        xyt = proj_xyz[..., :2]
        ls = shapely.geometry.LineString(xyt.tolist())
        locs = axis.intersection(ls)
        logger.debug("intersection for tick %s: %s", t, locs)
        if locs:
            tick = coord_picker(locs.xy)
            _ticks.append(tick[0])
            ticklabels.append(t)

    return _ticks, ticklabels
