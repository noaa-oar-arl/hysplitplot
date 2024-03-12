# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# plot.py
#
# For trajectory colors.
# ---------------------------------------------------------------------------

from abc import ABC, abstractmethod

from hysplitplot import const


class ColorCycle(ABC):

    _colors = ["#ff0000", "#0000ff", "#00ff00", "#00ffff",  # red, blue, green, cyan
               "#cc00ff", "#ffff00", "#3399cc"]             # magenta, yellow, ?

    def __init__(self, max_colors=7):
        self.max_colors = max(min(7, max_colors), 3)
        self.index = -1

    def next_color(self, height_index, color_code):
        self.index = (self.index + 1) % self.max_colors
        return self._colors[self.index]

    def reset(self):
        self.index = -1


class ItemizedColorCycle(ColorCycle):

    def __init__(self):
        super(ItemizedColorCycle, self).__init__()

    def next_color(self, height_index, color_code):
        k = (int(color_code) - 1) % self.max_colors
        return self._colors[k]


class MonoColorCycle(ColorCycle):

    def __init__(self):
        super(MonoColorCycle, self).__init__()

    def next_color(self, height_index, color_code):
        return "#000000"


class HeightColorCycle(ColorCycle):

    def __init__(self):
        super(HeightColorCycle, self).__init__()

    def next_color(self, height_index, color_code):
        return self._colors[height_index % self.max_colors]


class ColorCycleFactory:

    @staticmethod
    def create_instance(settings, height_count):
        if settings.color == const.Color.COLOR:
            if height_count == 1:
                return ColorCycle(3)
            else:
                return HeightColorCycle()
        elif settings.color == const.Color.ITEMIZED:
            return ItemizedColorCycle()
        else:
            return MonoColorCycle()

