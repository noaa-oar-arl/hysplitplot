# ---------------------------------------------------------------------------
# NOAA Air Resources Laboratory
#
# test_smooth.py
#
# Performs unit tests on functions and class methods declared in smooth.py.
# ---------------------------------------------------------------------------

import numpy
import pytest

from hysplitplot import smooth, const


def test_SmoothingKernelFactory_create_instance():
    k = smooth.SmoothingKernelFactory.create_instance(const.SmoothingKernel.SIMPLE, 1)
    assert isinstance(k, smooth.SimpleSmoothingKernel)


def test_SmoothingKernel___init__():
    k = smooth.SmoothingKernel(1)
    assert k.half_sz == 1
    assert k.n == 3
    assert k.kernel.shape == (3, 3)
    assert k.kernel.max() == 0.0 and k.kernel.min() == 0.0

    
def test_SmoothingKernel_smooth():
    k = smooth.SimpleSmoothingKernel(1)
    
    assert k.kernel[0] == pytest.approx([0.1, 0.1, 0.1])
    assert k.kernel[1] == pytest.approx([0.1, 0.2, 0.1])
    assert k.kernel[2] == pytest.approx([0.1, 0.1, 0.1])
    
    a = numpy.zeros((4, 5), dtype=float)
    a[0, 0] = 1.0
    a[1, 1] = 2.0
    a[2, 2] = 3.0
    a[3, 3] = 4.0
    
    b = k.smooth(a)
    
    assert b[0] == pytest.approx([0.4, 0.3, 0.2, 0.0, 0.0])
    assert b[1] == pytest.approx([0.3, 0.8, 0.5, 0.3, 0.0])
    assert b[2] == pytest.approx([0.2, 0.5, 1.2, 0.7, 0.4])
    assert b[3] == pytest.approx([0.0, 0.3, 0.7, 1.1, 0.4])

    
def test_SmoothingKernel_smooth_with_max_preserved():
    k = smooth.SimpleSmoothingKernel(1)
    
    assert k.kernel[0] == pytest.approx([0.1, 0.1, 0.1])
    assert k.kernel[1] == pytest.approx([0.1, 0.2, 0.1])
    assert k.kernel[2] == pytest.approx([0.1, 0.1, 0.1])
    
    a = numpy.zeros((4, 5), dtype=float)
    a[0, 0] = 1.0
    a[1, 1] = 2.0
    a[2, 2] = 3.0
    a[3, 3] = 4.0
    
    b = k.smooth_with_max_preserved(a)
    
    assert b[0] == pytest.approx([0.4, 0.3, 0.2, 0.0, 0.0])
    assert b[1] == pytest.approx([0.3, 0.8, 0.5, 0.3, 0.0])
    assert b[2] == pytest.approx([0.2, 0.5, 1.2, 0.7, 0.4])
    assert b[3] == pytest.approx([0.0, 0.3, 0.7, 4.0, 0.4])
 
 
def test_SimpleSmoothingKernel___init__():
    k = smooth.SimpleSmoothingKernel(1)
    assert k.half_sz == 1
    assert k.n == 3
    assert k.kernel.shape == (3, 3)
    assert k.kernel[0] == pytest.approx([0.1, 0.1, 0.1])
    assert k.kernel[1] == pytest.approx([0.1, 0.2, 0.1])
    assert k.kernel[2] == pytest.approx([0.1, 0.1, 0.1])

    k = smooth.SimpleSmoothingKernel(2)
    assert k.half_sz == 2
    assert k.n == 5
    assert k.kernel.shape == (5, 5)
    assert k.kernel[0] == pytest.approx([0.0277778, 0.0277778, 0.0277778, 0.0277778, 0.0277778])
    assert k.kernel[1] == pytest.approx([0.0277778, 0.0555556, 0.0555556, 0.0555556, 0.0277778])
    assert k.kernel[2] == pytest.approx([0.0277778, 0.0555556, 0.1111111, 0.0555556, 0.0277778])
    assert k.kernel[3] == pytest.approx([0.0277778, 0.0555556, 0.0555556, 0.0555556, 0.0277778])
    assert k.kernel[4] == pytest.approx([0.0277778, 0.0277778, 0.0277778, 0.0277778, 0.0277778])

