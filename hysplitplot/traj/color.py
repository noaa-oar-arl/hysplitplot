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

    _colors = [
          "#ff0000", "#0000ff", "#00ff00", # red, blue, green
          "#00ffff", "#cc00ff", "#ffff00", # cyan, magenta, yellow
          "#3399cc", "#ff9900", "#eda4ff", # olive, orange, pink
          "#ccff00", "#009900", "#0066ff", # light green, dark green, light blue
          "#9900ff", "#000000", "#666666", # light magenta, black, gray
          "#660066", "#ff6600", "#330033"  # brown, orange, dark brown
    ] 

    def __init__(self, max_colors=18):
        self.max_colors = max(min(18, max_colors), 3)
        self.index = -1

    def next_color(self, height_index, color_code):
        self.index = (self.index + 1) % self.max_colors
        return self._colors[self.index]

    def reset(self):
        self.index = -1


class ItemizedColorCycle(ColorCycle):

    def __init__(self):
        super(ItemizedColorCycle, self).__init__()

    def next_color(self, height_index: int, color_code: str):
        """
        Note color_code is a single character and its value
        can be digits ('1', '2', ..., '9') and alphabets
        ('a', 'b', ..., 'i'). 
        """
        v = 1
        if isinstance(color_code, int):
            v = color_code + 1
        elif isinstance(color_code, str) and len(color_code) > 0:
            c = color_code.lower()
            if c.isdecimal():
               v = int(c[0])
            elif c.isalpha():
               v = 10 + ord(c[0]) - ord('a')
        k = (v - 1) % self.max_colors
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

