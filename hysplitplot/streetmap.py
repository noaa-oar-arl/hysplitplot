import contextily
import logging
import matplotlib.pyplot as plt
import numpy
import urllib


logger = logging.getLogger(__name__)


class StreetMap:
    
    def __init__(self):
        self.min_zoom = 0   # from openstreetmap.org
        self.max_zoom = 15  # 19 from openstreetmap.org. Reduced to 15 to avoid HTTP errors.
        self.tile_widths = self._compute_tile_widths()
        self.last_extent = None
    
    def _compute_tile_widths(self):
        tile_widths = numpy.empty(self.max_zoom - self.min_zoom + 1, dtype=float)
        w = 360.0
        for k in range(len(tile_widths)):
            tile_widths[k] = w; w *= 0.5
        return tile_widths

    def _compute_initial_zoom(self, lonl, latb, lonr, latt):
        """Find a zoom level that yields about 1 tile horizontally."""
        dlon = abs(lonr - lonl)
        for k in range(len(self.tile_widths)):
            tile_count = dlon / self.tile_widths[k]
            if int(tile_count) >= 1:
                return k
        return self.max_zoom
    
    def draw(self, ax, corners_xy, corners_lonlat, url=contextily.sources.ST_TERRAIN):
        # Do nothing if the spatial extent has not changed.
        if self.last_extent == ax.axis():
            return
        
        lonl, lonr, latb, latt = corners_lonlat
        zoom = self._compute_initial_zoom(lonl, latb, lonr, latt)
            
        # The return value of ax.axis() is assumed to be the same as corners_xy. 
        xmin, xmax, ymin, ymax = corners_xy
        
        continueQ = True
        while continueQ:
            try:
                contextily.howmany(xmin, ymin, xmax, ymax, zoom)
                basemap, extent = contextily.bounds2img(xmin, ymin, xmax, ymax, zoom=zoom, url=url)
                continueQ = False
            except urllib.error.HTTPError as ex:
                logger.error("Could not pull street map images at zoom level {}: {}".format(zoom, ex))
                if zoom == 0:
                    continueQ = False
                else:
                    zoom -= 1
                
        # Ad hoc fix because ax.imshow() incorrectly shows the basemap.
        #ax.imshow(basemap, extent=extent, interpolation="bilinear")
        saved = None if ax is plt.gca() else plt.gca()
        if saved is not None:
            plt.sca(ax)
                
        plt.imshow(basemap, extent=extent, interpolation='bilinear')
            
        if saved is not None:
            plt.sca(saved)
    
        self.last_extent = corners_xy 
        ax.axis( self.last_extent )
