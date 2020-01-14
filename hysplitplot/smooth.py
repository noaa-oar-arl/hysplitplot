# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# smooth.py
#
# For smoothing data points in a two-dimensional array.
# ---------------------------------------------------------------------------

from abc import ABC
import logging
import numpy

from hysplitplot import const


logger = logging.getLogger(__name__)


class SmoothingKernelFactory:

    @staticmethod
    def create_instance(method, half_sz):
        return SimpleSmoothingKernel(half_sz)


class SmoothingKernel(ABC):

    def __init__(self, half_sz):
        self.half_sz = half_sz
        self.n = 2 * half_sz + 1
        self.kernel = numpy.zeros((self.n, self.n), dtype=float)

    # TODO: use FFT-based convolution.
    def smooth(self, a):
        b = numpy.empty(a.shape, dtype=float)

        for j in range(a.shape[0]):
            for i in range(a.shape[1]):
                i_start = max(0, i - self.half_sz)
                i_end = min(a.shape[1], i + self.half_sz + 1)

                k_start = i_start - i + self.half_sz
                k_end = i_end - i + self.half_sz

                s = 0.0
                for dj in range(-self.half_sz, self.half_sz + 1):
                    if j + dj >= 0 and j + dj < a.shape[0]:
                        s += numpy.inner(
                            a[j + dj, i_start: i_end],
                            self.kernel[dj + self.half_sz, k_start: k_end])

                b[j, i] = s

        return b

    def smooth_with_max_preserved(self, xconc):
        v = numpy.amax(xconc)
        if v > 0:
            loc = numpy.where(xconc == v)

        conc = self.smooth(xconc)

        if v > 0:
            for c in list(zip(loc[0], loc[1])):
                conc[c] = v

        return conc


class SimpleSmoothingKernel(SmoothingKernel):

    def __init__(self, half_sz):
        super(SimpleSmoothingKernel, self).__init__(half_sz)
        self.fill()
        self.normalize()

    def fill(self, w=2.0):
        # at the center
        ic = jc = self.half_sz
        self.kernel[ic, jc] = w

        for k in range(1, self.half_sz + 1):
            w *= 0.5

            # walk to the right
            i = ic - k
            j = jc - k
            for l in range(-k, k):
                self.kernel[i, j] = w
                i += 1

            # walk down
            for l in range(-k, k):
                self.kernel[i, j] = w
                j += 1

            # walk to the left
            for l in range(-k, k):
                self.kernel[i, j] = w
                i -= 1

            # walk to top
            for l in range(-k, k):
                self.kernel[i, j] = w
                j -= 1

    def normalize(self):
        a = self.kernel.sum()

        if a != 0:
            self.kernel *= 1.0 / a
